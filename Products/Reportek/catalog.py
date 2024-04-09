"""
This tool is a wrapper around Products.ZCatalog. On initialization it creates
the required indexes and metadata and offers a few convenience and
maintenance functionalities such as catalog rebuilding and missing objects
reporting.

"""

import logging
import os
import time
import urllib
from time import clock as process_time

from AccessControl.class_init import InitializeClass
from AccessControl.SecurityInfo import ClassSecurityInfo
from AccessControl.SecurityManagement import getSecurityManager
from Acquisition import aq_base
from OFS.interfaces import IObjectManager
from zope.component import queryMultiAdapter
from zope.interface import implementer

from Products.Five.browser import BrowserView
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.config import DEPLOYMENT_BDR, REPORTEK_DEPLOYMENT
from Products.Reportek.constants import DEFAULT_CATALOG
from Products.Reportek.indexer.interfaces import IIndexableObject
from Products.Reportek.indexer.wrapper import IndexableObjectWrapper
from Products.Reportek.interfaces import IReportekCatalog
from Products.Reportek.RepUtils import registerToolInterface
from Products.ZCatalog.ZCatalog import ZCatalog

from .indexing import filterTemporaryItems, getQueue, processQueue

CATALOG_OPTIMIZATION_DISABLED = os.environ.get(
    "CATALOG_OPTIMIZATION_DISABLED",
    "false",
)
CATALOG_OPTIMIZATION_DISABLED = CATALOG_OPTIMIZATION_DISABLED.lower() in (
    "true",
    "t",
    "yes",
    "y",
    "1",
)

log = logging.getLogger(__name__)

REPORTEK_META_TYPES = [
    "Report Collection",
    "Report Envelope",
    "Report Document",
    "Report Feedback",
    "Report Feedback Comment",
    "Report Hyperlink",
    "Repository Referral",
    # 'Remote Application',
    "Process",
    "Activity",
    "Workitem",
    "Converter",
    "QAScript",
    "Reportek Dataflow Mappings",
    "Dataflow Mappings Record",
    "File",
    "File (Blob)",
    # 'XMLRPC Method',
    "Workflow Engine",
]


def catalog_rebuild(root, catalog="Catalog"):
    import transaction

    catalog = root.unrestrictedTraverse("/".join([catalog]))

    def add_to_catalog(ob):
        try:
            catalog.catalog_object(ob, "/".join(ob.getPhysicalPath()))
            # catalog.indexObject(ob)
        except Exception:
            log.warning("Unable to catalog object: {}".format(ob))

    catalog.manage_catalogClear()
    for i, ob in enumerate(walk_folder(root)):
        if i % 10000 == 0:
            transaction.savepoint()
            root._p_jar.cacheGC()
            log.info("savepoint at %d records", i)
        add_to_catalog(ob)


class MaintenanceView(BrowserView):
    def __call__(self):
        return maintenance.__of__(self.aq_parent)()


maintenance = PageTemplateFile("zpt/manage_maintenance.zpt", globals())


class RebuildView(BrowserView):
    def __call__(self):
        """maintenance operations for the catalog"""

        catalog = self.context
        elapse = time.time()
        c_elapse = process_time()

        catalog_rebuild(catalog.unrestrictedTraverse("/"))

        elapse = time.time() - elapse
        c_elapse = process_time() - c_elapse

        msg = "Catalog Rebuilt\n" "Total time: %s\n" "Total CPU time: %s" % (
            repr(elapse),
            repr(c_elapse),
        )
        log.info(msg)

        self.request.RESPONSE.redirect(
            catalog.absolute_url()
            + "/manage_maintenance?manage_tabs_message="
            + urllib.quote(msg)
        )


def walk_folder(folder):
    for idx, ob in folder.ZopeFind(
        folder, obj_metatypes=REPORTEK_META_TYPES, search_sub=0
    ):
        yield ob

        if IObjectManager.providedBy(ob):
            for sub_ob in walk_folder(ob):
                yield sub_ob


def listAllowedAdminRolesAndUsers(user):
    effective_roles = user.getRoles()
    sm = getSecurityManager()
    if sm.calledByExecutable():
        eo = sm._context.stack[-1]
        proxy_roles = getattr(eo, "_proxy_roles", None)
        if proxy_roles:
            effective_roles = proxy_roles
    result = list(effective_roles)
    result.append("Anonymous")
    result.append("user:%s" % user.getId())
    return result


@implementer(IReportekCatalog)
class ReportekCatalog(ZCatalog):
    id = DEFAULT_CATALOG
    meta_type = "Reportek Catalog"
    zmi_icon = "fas fa-search"

    security = ClassSecurityInfo()

    manage_options = ZCatalog.manage_options + (
        {"label": "Overview", "action": "manage_overview"},
    )

    def __init__(self):
        ZCatalog.__init__(self, self.getId())

    def _listAllowedRolesAndUsers(self, user):
        effective_roles = user.getRoles()
        sm = getSecurityManager()
        if sm.calledByExecutable():
            eo = sm._context.stack[-1]
            proxy_roles = getattr(eo, "_proxy_roles", None)
            if proxy_roles:
                effective_roles = proxy_roles
        result = list(effective_roles)
        result.append("Anonymous")
        result.append("user:%s" % user.getId())
        return result

    def _convertQuery(self, kw):
        # Convert query to modern syntax
        for k in "effective", "expires":
            kusage = k + "_usage"
            if kusage not in kw:
                continue
            usage = kw[kusage]
            if not usage.startswith("range:"):
                raise ValueError("Incorrect usage %s" % repr(usage))
            kw[k] = {"query": kw[k], "range": usage[6:]}
            del kw[kusage]

    def searchResults(self, **kw):
        """
        Calls catalog.searchResults with extra arguments that
        limit the results to what the user is allowed to see.
        """
        processQueue()
        user = getSecurityManager().getUser()
        if kw.get("admin_check"):
            kw["allowedAdminRolesAndUsers"] = listAllowedAdminRolesAndUsers(
                user
            )
            kw.pop("admin_check", None)
            # BDR specific query, return results
            return ZCatalog.searchResults(self, **kw)
        if kw.get("security") and REPORTEK_DEPLOYMENT != DEPLOYMENT_BDR:
            # This cannot be deployed on BDR yet, as the searchresults will be
            # affected for users with dynamic Owner role.
            # https://taskman.eionet.europa.eu/issues/118846#note-9
            kw["allowedRolesAndUsers"] = listAllowedAdminRolesAndUsers(user)
            kw.pop("security")
        limit = kw.pop("_limit", None)
        results = ZCatalog.searchResults(self, **kw)
        if limit:
            results = list(results)
            del results[limit:]
        return results

    __call__ = searchResults

    @security.private
    def unrestrictedSearchResults(self, REQUEST=None, **kw):
        """Calls ZCatalog.searchResults directly without restrictions.

        This method returns every also not yet effective and already expired
        objects regardless of the roles the caller has.

        CAUTION: Care must be taken not to open security holes by
        exposing the results of this method to non authorized callers!

        If you're in doubt if you should use this method or
        'searchResults' use the latter.
        """
        processQueue()
        return ZCatalog.searchResults(self, REQUEST, **kw)

    def __url(self, ob):
        return "/".join(ob.getPhysicalPath())

    # manage_catalogFind = DTMLFile('catalogFind', _dtmldir)

    def catalog_object(
        self, obj, uid=None, idxs=None, update_metadata=1, pghandler=None
    ):
        # Wraps the object with workflow and accessibility
        # information just before cataloging.
        if IIndexableObject.providedBy(obj):
            w = obj
        else:
            w = queryMultiAdapter((obj, self), IIndexableObject)
            if w is None:
                # BBB
                w = IndexableObjectWrapper(obj, self)
        ZCatalog.catalog_object(self, w, uid, idxs, update_metadata, pghandler)

    @security.private
    def indexObject(self, object):
        if not CATALOG_OPTIMIZATION_DISABLED:
            obj = filterTemporaryItems(object)
            if obj is not None:
                indexer = getQueue()
                indexer.index(obj)
        else:
            self._indexObject(object)

    @security.private
    def unindexObject(self, object):
        if not CATALOG_OPTIMIZATION_DISABLED:
            obj = filterTemporaryItems(object, checkId=False)
            if obj is not None:
                indexer = getQueue()
                indexer.unindex(obj)
        else:
            self._unindexObject(object)

    @security.private
    def reindexObject(self, object, idxs=[], update_metadata=1, uid=None):
        # `CMFCatalogAware.reindexObject` also updates the modification date
        # of the object for the "reindex all" case.  unfortunately, some other
        # packages like `CMFEditions` check that date to see if the object was
        # modified during the request, which fails when it's only set on commit
        if not CATALOG_OPTIMIZATION_DISABLED:
            if idxs in (None, []) and hasattr(
                aq_base(object), "notifyModified"
            ):
                object.notifyModified()
            obj = filterTemporaryItems(object)
            if obj is not None:
                indexer = getQueue()
                indexer.reindex(obj, idxs, update_metadata=update_metadata)
        else:
            self._reindexObject(
                object,
                idxs=idxs,
                update_metadata=update_metadata,
                uid=uid,
            )

    @security.private
    def _indexObject(self, object):
        """Add to catalog."""
        url = self.__url(object)
        self.catalog_object(object, url)

    @security.private
    def _unindexObject(self, object):
        """Remove from catalog."""
        url = self.__url(object)
        self.uncatalog_object(url)

    @security.private
    def _reindexObject(self, object, idxs=[], update_metadata=1, uid=None):
        """Update catalog after object data has changed.

        The optional idxs argument is a list of specific indexes
        to update (all of them by default).

        The update_metadata flag controls whether the object's
        metadata record is updated as well.

        If a non-None uid is passed, it will be used as the catalog uid
        for the object instead of its physical path.
        """
        if uid is None:
            uid = self.__url(object)
        if idxs != []:
            # Filter out invalid indexes.
            idxs = [i for i in idxs if i in self._catalog.indexes]
        self.catalog_object(object, uid, idxs, update_metadata)


InitializeClass(ReportekCatalog)
# If we register this tool like below, we're going to end up stale catalog
# registerToolInterface(DEFAULT_CATALOG, IReportekCatalog)
