"""
This tool is a wrapper around Products.ZCatalog. On initialization it creates
the required indexes and metadata and offers a few convenience and
maintenance functionalities such as catalog rebuilding and missing objects
reporting.

"""
import logging
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl.SecurityManagement import getSecurityManager
from Products.Reportek.config import REPORTEK_DEPLOYMENT, DEPLOYMENT_BDR
from Products.Five.browser import BrowserView
from OFS.interfaces import IObjectManager
from copy import deepcopy


log = logging.getLogger(__name__)

REPORTEK_META_TYPES = [
        'Report Collection',
        'Report Envelope',
        'Report Document',
        'Report Feedback',
        'Report Feedback Comment',
        'Report Hyperlink',
        'Repository Referral',
        'Remote Application',
        'Process',
        'Activity',
        'Workitem',
        'Converter',
        'QAScript',
        'Reportek Dataflow Mappings',
        'Dataflow Mappings Record',
        'DTML Document',
        'DTML Method',
        'File',
        'File (Blob)',
        'Folder',
        'Image',
        'Page Template',
        'Script (Python)',
        'XMLRPC Method',
        'Workflow Engine']


def catalog_rebuild(root, catalog='Catalog'):
    import transaction

    catalog = root.unrestrictedTraverse('/'.join([catalog]))

    def add_to_catalog(ob):
        try:
            catalog.catalog_object(ob, '/'.join(ob.getPhysicalPath()))
        except Exception as e:
            log.warning("Unable to catalog object: {}".format(ob))

    catalog.manage_catalogClear()
    for i, ob in enumerate(walk_folder(root)):
        if i % 10000 == 0:
            transaction.savepoint()
            root._p_jar.cacheGC()
            log.info('savepoint at %d records', i)
        add_to_catalog(ob)


class MaintenanceView(BrowserView):

    def __call__(self):
        return maintenance.__of__(self.aq_parent)()

maintenance = PageTemplateFile('zpt/manage_maintenance.zpt', globals())


class RebuildView(BrowserView):
    def __call__(self):
        """ maintenance operations for the catalog """

        catalog = self.context
        catalog_rebuild(catalog.unrestrictedTraverse('/'))

        self.request.RESPONSE.redirect(catalog.absolute_url() + '/manage_maintenance')


def walk_folder(folder):
    for idx, ob in folder.ZopeFind(folder, obj_metatypes=REPORTEK_META_TYPES, search_sub=0):
        yield ob

        if IObjectManager.providedBy(ob):
            for sub_ob in walk_folder(ob):
                yield sub_ob


def listAllowedAdminRolesAndUsers(user):
    effective_roles = user.getRoles()
    sm = getSecurityManager()
    if sm.calledByExecutable():
        eo = sm._context.stack[-1]
        proxy_roles = getattr(eo, '_proxy_roles', None)
        if proxy_roles:
            effective_roles = proxy_roles
    result = list(effective_roles)
    result.append('Anonymous')
    result.append('user:%s' % user.getId())
    return result


def searchResults(catalog, query, admin_check=False, security=True):
    """
        Calls catalog.searchResults with extra arguments that
        limit the results to what the user is allowed to see.
    """

    user = getSecurityManager().getUser()
    if admin_check:
        query['allowedAdminRolesAndUsers'] = listAllowedAdminRolesAndUsers(user)
        # BDR specific query, return results
        return catalog.searchResults(**query)
    if security and REPORTEK_DEPLOYMENT != DEPLOYMENT_BDR:
        # This cannot be deployed on BDR yet, as the searchresults will be
        # affected for users with dynamic Owner role.
        # https://taskman.eionet.europa.eu/issues/118846#note-9
        query['allowedRolesAndUsers'] = listAllowedAdminRolesAndUsers(user)

    return catalog.searchResults(**query)


def _mergedLocalRoles(object):
    """Returns a merging of object and its ancestors'
    __ac_local_roles__."""
    # Modified from AccessControl.User.getRolesInContext().
    merged = {}
    object = getattr(object, 'aq_inner', object)
    while 1:
        if hasattr(object, '__ac_local_roles__'):
            dict = object.__ac_local_roles__ or {}
            if callable(dict):
                dict = dict()
            for k, v in dict.items():
                if k in merged:
                    merged[k] = merged[k] + v
                else:
                    merged[k] = v
        if hasattr(object, 'aq_parent'):
            object = object.aq_parent
            object = getattr(object, 'aq_inner', object)
            continue
        if hasattr(object, '__self__'):
            object = object.__self__
            object = getattr(object, 'aq_inner', object)
            continue
        break

    return deepcopy(merged)
