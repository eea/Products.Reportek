# The contents of this file are subject to the Mozilla Public# License
# Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is Reportek version 2.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel and Eau de Web are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Soren Roug, EEA


import logging

# Zope imports
import Zope2
from AccessControl.Permissions import manage_users as ManageUsers
from App.ImageFile import ImageFile
from plone.keyring.interfaces import IKeyManager
from plone.keyring.keymanager import KeyManager
from plone.registry.interfaces import IRegistry
from registry import Registry
from zope.component import getGlobalSiteManager, getUtility
from zope.i18nmessageid import MessageFactory
from ZPublisher.BaseRequest import BaseRequest

from Products.ExtendedPathIndex.ExtendedPathIndex import (
    ExtendedPathIndex,
)
from Products.PluggableAuthService.PluggableAuthService import (
    registerMultiPlugin,
)
from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
from Products.PluginIndexes.KeywordIndex.KeywordIndex import (
    KeywordIndex,
)
from Products.Reportek.config import (
    DEPLOYMENT_BDR,
    REPORTEK_DEPLOYMENT,
)
from Products.Reportek import (
    Collection,
    Converter,
    Converters,
    DataflowMappings,
    OpenFlowEngine,
    QARepository,
    QAScript,
    Referral,
    RemoteApplication,
    RemoteFMEConversionApplication,
    RemoteRabbitMQQAApplication,
    RemoteRESTApplication,
    RemoteRestQaApplication,
    ReportekAPI,
    ReportekEngine,
    ReportekUtilities,
    constants,
    monitoring,
)
from Products.Reportek.caching.config import registry_setup
from Products.Reportek.catalog import ReportekCatalog
from Products.Reportek.interfaces import IReportekCatalog
from Products.Reportek.ReportekUserFactoryPlugin import (
    ReportekUserFactoryPlugin,
    addReportekUserFactoryPlugin,
    manage_addReportekUserFactoryPluginForm,
)
from Products.Reportek.RepUtils import getToolByName
from Products.ZCTextIndex.ZCTextIndex import PLexicon, ZCTextIndex

# workaround for BaseRequest assuming requests not GET, POST, PURGE as webdav
BaseRequest.maybe_webdav_client = False

__doc__ = """Reportek __init__ """
__version__ = "$Rev$"[6:-2]
logger = logging.getLogger("Reportek")


MessageFactory = MessageFactory("Reportek")

maintenance_options = (
    ReportekCatalog.manage_options[:1]
    + ({"label": "Maintenance", "action": "manage_maintenance"},)
    + ReportekCatalog.manage_options[1:]
)

ReportekCatalog.manage_options = maintenance_options


def setup_catalog(app):
    """Set up the catalog for the given app."""
    ctool_id = constants.DEFAULT_CATALOG
    catalog = getToolByName(app, ctool_id, None)
    if not catalog:
        catalog = ReportekCatalog()
        app._setObject(ctool_id, catalog)
        catalog.meta_types = [
            {"name": "FieldIndex", "instance": FieldIndex},
            {"name": "KeywordIndex", "instance": KeywordIndex},
            {"name": "DateIndex", "instance": DateIndex},
            {"name": "ZCTextIndex", "instance": ZCTextIndex},
            {"name": "ExtendedPathIndex", "instance": ExtendedPathIndex},
        ]
        create_reportek_indexes(catalog)
    if catalog not in app.objectValues():
        app._setObject(ctool_id, catalog)
    tool_obj = catalog
    gsm = getGlobalSiteManager()
    if tool_obj is not None and gsm.queryUtility(IReportekCatalog) is None:
        gsm.registerUtility(tool_obj, IReportekCatalog)

    return catalog


def create_reportek_objects(app):
    # Add ReportekEngine instance
    try:
        repo_engine = getattr(app, constants.ENGINE_ID)
    except AttributeError:
        repo_engine = ReportekEngine.ReportekEngine()
        app._setObject(constants.ENGINE_ID, repo_engine)

    # Add converters folder
    try:
        converters = getattr(app, constants.CONVERTERS_ID)
    except AttributeError:
        converters = Converters.Converters()
        app._setObject(constants.CONVERTERS_ID, converters)

    # Add QARepository folder
    try:
        qarepo = getattr(app, constants.QAREPOSITORY_ID)
    except AttributeError:
        qarepo = QARepository.QARepository()
        app._setObject(constants.QAREPOSITORY_ID, qarepo)

    # Add dataflow mapping
    try:
        dataflow_mapping = getattr(app, constants.DATAFLOW_MAPPINGS)
    except AttributeError:
        dataflow_mapping = DataflowMappings.DataflowMappings()
        app._setObject(constants.DATAFLOW_MAPPINGS, dataflow_mapping)

    # Add OpenFlowEngine instance
    try:
        workflow = getattr(app, constants.WORKFLOW_ENGINE_ID)
    except AttributeError:
        workflow = OpenFlowEngine.OpenFlowEngine(constants.WORKFLOW_ENGINE_ID)
        app._setObject(constants.WORKFLOW_ENGINE_ID, workflow)

    # Add Catalog
    setup_catalog(app)

    # Add Reportek Utilities
    try:
        reportek_utilities = getattr(app, constants.REPORTEK_UTILITIES)
    except AttributeError:
        reportek_utilities = ReportekUtilities.ReportekUtilities(
            constants.REPORTEK_UTILITIES, "Reportek Utilities"
        )
        app._setObject(constants.REPORTEK_UTILITIES, reportek_utilities)

    # Add Reportek API
    try:
        reportek_api = getattr(app, constants.REPORTEK_API)
    except AttributeError:
        reportek_api = ReportekAPI.ReportekAPI(
            constants.REPORTEK_API, "Reportek API"
        )
        app._setObject(constants.REPORTEK_API, reportek_api)

    # Add Registry Management
    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
        import RegistryManagement

        try:
            registry_management = getattr(app, constants.REGISTRY_MANAGEMENT)
        except AttributeError:
            registry_management = RegistryManagement.RegistryManagement(
                constants.REGISTRY_MANAGEMENT, "FGases registry"
            )
            app._setObject(constants.REGISTRY_MANAGEMENT, registry_management)

    # Add portal_registry
    try:
        portal_registry = getattr(app, constants.REGISTRY)
    except AttributeError:
        portal_registry = Registry(constants.REGISTRY, "Portal Registry")
        app._setObject(constants.REGISTRY, portal_registry)

    # Register the named utility
    gsm = getGlobalSiteManager()
    # gsm.registerUtility(portal_registry, IRegistry, name=constants.REGISTRY)
    gsm.registerUtility(portal_registry, IRegistry)

    registry = getUtility(IRegistry)
    # setup registry for caching purposes
    registry_setup(registry)

    # register key manager from plone.keyring
    km = getattr(app, "key_manager", None)
    if km is None:
        km = KeyManager()
        app.key_manager = km
        app._p_changed = 1
        if logger is not None:
            logger.info("Adding key manager")
    gsm.registerUtility(km, IKeyManager)


def _strip_protocol_domain(full_url):
    """Take a full url and return a tuple of path part and protocol+domain
    part.
    """
    parts = full_url.split("/")
    # domain.domain.domain.../abs/abs
    i = 1
    if full_url.startswith("http"):
        # http...//domain.domain.domain.../abs/abs
        i = 3
    return "/".join(parts[i:]), "/".join(parts[:i])


def add_index(name, catalog, meta_type, meta=False):
    if name not in catalog.indexes():
        if meta_type == "ZCTextIndex":
            item_extras = Empty()
            item_extras.doc_attr = name
            item_extras.index_type = "Okapi BM25 Rank"
            item_extras.lexicon_id = "lexicon"
            catalog.addIndex(name, meta_type, item_extras)
        else:
            catalog.addIndex(name, meta_type)

    if meta and name not in catalog.schema():
        # Add Catalog metadata
        catalog.addColumn(name)


def add_lexicon(catalog):
    from Products.ZCTextIndex.HTMLSplitter import HTMLWordSplitter
    from Products.ZCTextIndex.Lexicon import (
        CaseNormalizer,
        StopWordAndSingleCharRemover,
    )

    lexicon = PLexicon(
        "lexicon",
        "Lexicon",
        HTMLWordSplitter(),
        CaseNormalizer(),
        StopWordAndSingleCharRemover(),
    )
    catalog._setObject("lexicon", lexicon)


def create_reportek_indexes(catalog):
    if not hasattr(catalog, "lexicon"):
        add_lexicon(catalog)
    add_index("id", catalog, "FieldIndex", meta=True)
    add_index("title", catalog, "ZCTextIndex", meta=True)
    add_index("meta_type", catalog, "FieldIndex", meta=True)
    add_index("bobobase_modification_time", catalog, "DateIndex", meta=True)
    add_index("activity_id", catalog, "FieldIndex", meta=True)
    add_index("actor", catalog, "FieldIndex", meta=True)
    add_index("content_type", catalog, "FieldIndex")
    add_index("country", catalog, "FieldIndex", meta=True)
    add_index("dataflow_uri", catalog, "FieldIndex", meta=True)
    add_index("dataflow_uris", catalog, "KeywordIndex", meta=True)
    add_index("getCountryName", catalog, "FieldIndex", meta=True)
    add_index("instance_id", catalog, "FieldIndex")
    add_index("partofyear", catalog, "FieldIndex", meta=True)
    add_index("path", catalog, "ExtendedPathIndex")
    add_index("process_path", catalog, "FieldIndex")
    add_index("released", catalog, "FieldIndex", meta=True)
    add_index("reportingdate", catalog, "FieldIndex", meta=True)
    # add_index('last_released_date', catalog, 'FieldIndex', meta=True)
    add_index("status", catalog, "FieldIndex")
    add_index("xml_schema_location", catalog, "FieldIndex")
    add_index("years", catalog, "KeywordIndex", meta=True)
    add_index("local_unique_roles", catalog, "KeywordIndex")
    add_index("local_defined_users", catalog, "KeywordIndex", meta=True)
    add_index("Description", catalog, "ZCTextIndex", meta=True)
    add_index("blocker", catalog, "FieldIndex", meta=True)
    add_index("feedback_status", catalog, "FieldIndex", meta=True)
    # restricted is strictly needed for queries made by cr
    add_index("restricted", catalog, "FieldIndex", meta=True)
    add_index("allowedAdminRolesAndUsers", catalog, "KeywordIndex", meta=True)
    add_index("allowedRolesAndUsers", catalog, "KeywordIndex", meta=True)
    add_index("wf_status", catalog, "FieldIndex", meta=True)
    if "activation_log" not in catalog.schema():
        catalog.addColumn("activation_log")
    if "local_defined_roles" not in catalog.schema():
        catalog.addColumn("local_defined_roles")
    add_index("document_id", catalog, "FieldIndex")
    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
        add_index("get_fgas_activities", catalog, "FieldIndex", meta=True)
        add_index("get_fgas_reported_gases", catalog, "FieldIndex", meta=True)
        add_index(
            "get_fgas_i_authorisations", catalog, "FieldIndex", meta=True
        )
        add_index(
            "get_fgas_a_authorisations", catalog, "FieldIndex", meta=True
        )
        add_index("company_id", catalog, "FieldIndex", meta=True)


class Empty:
    pass


def startup(context):
    import transaction

    app = Zope2.app()

    create_reportek_objects(app)

    transaction.commit()


registerMultiPlugin(ReportekUserFactoryPlugin.meta_type)


def initialize(context):
    """Reportek initializer"""

    import blob
    from AccessControl.Permissions import view_management_screens

    context.registerClass(
        QAScript.QAScript,
        permission="Add QAScripts",
        constructors=(
            QAScript.manage_addQAScriptForm,
            QAScript.manage_addQAScript,
        ),
        icon="www/qascript.gif",
    )

    context.registerClass(
        Converter.Converter,
        permission="Add Converters",
        constructors=(
            Converter.manage_addConverterForm,
            Converter.manage_addConverter,
        ),
        icon="www/conv.gif",
    )

    context.registerClass(
        blob.OfsBlobFile,
        permission=view_management_screens,
        constructors=(
            blob.manage_addOfsBlobFile_html,
            blob.manage_addOfsBlobFile,
        ),
        icon="www/blobfile.png",
    )

    context.registerClass(
        ReportekUserFactoryPlugin,
        permission=ManageUsers,
        constructors=(
            manage_addReportekUserFactoryPluginForm,
            addReportekUserFactoryPlugin,
        ),
        visibility=None,
        icon="www/openflowEngine.gif",
    )

    ###########################################
    #   Registration of other classes
    ###########################################
    try:
        context.registerClass(
            Collection.Collection,
            permission="Add Collections",
            constructors=(
                Collection.manage_addCollectionForm,
                Collection.manage_addCollection,
            ),
            icon="www/collection.gif",
        )

        context.registerClass(
            Referral.Referral,
            permission="Add Envelopes",
            constructors=(
                Referral.manage_addReferralForm,
                Referral.manage_addReferral,
            ),
            icon="www/referral.gif",
        )

        context.registerClass(
            RemoteApplication.RemoteApplication,
            permission="Add Remote Application",
            constructors=(
                RemoteApplication.manage_addRemoteApplicationForm,
                RemoteApplication.manage_addRemoteApplication,
            ),
            icon="www/qa_application.gif",
        )

        context.registerClass(
            RemoteRabbitMQQAApplication.RemoteRabbitMQQAApplication,
            permission="Add Remote Application",
            constructors=(
                RemoteRabbitMQQAApplication.manage_addRRMQQAApplicationForm,
                RemoteRabbitMQQAApplication.manage_addRRMQQAApplication,
            ),
            icon="www/qa_application.gif",
        )

        context.registerClass(
            RemoteRestQaApplication.RemoteRestQaApplication,
            permission="Add Remote Application",
            constructors=(
                RemoteRestQaApplication.manage_addRemoteRESTQAApplicationForm,
                RemoteRestQaApplication.manage_addRemoteRESTQAApplication,
            ),
            icon="www/qa_application.gif",
        )

        context.registerClass(
            RemoteRESTApplication.RemoteRESTApplication,
            permission="Add Remote Application",
            constructors=(
                RemoteRESTApplication.manage_addRemoteRESTApplicationForm,
                RemoteRESTApplication.manage_addRemoteRESTApplication,
            ),
            icon="www/qa_application.gif",
        )

        context.registerClass(
            RemoteFMEConversionApplication.RemoteFMEConversionApplication,
            permission="Add Remote Application",
            constructors=(
                RemoteFMEConversionApplication.manage_addRemoteFMEConversionApplicationForm,  # noqa
                RemoteFMEConversionApplication.manage_addRemoteFMEConversionApplication  # noqa
            ),  # noqa
            icon="www/qa_application.gif",
        )

        context.registerHelp()
        context.registerHelpTitle("Zope Help")

        monitoring.initialize()

    except Exception:
        import string
        import sys
        import traceback

        type, val, tb = sys.exc_info()
        sys.stderr.write(
            string.join(traceback.format_exception(type, val, tb), "")
        )
        del type, val, tb


# Define shared web objects that are used by products.
# This is usually (always ?) limited to images used
# when displaying an object in contents lists.
# These objects are accessed as:
#   <dtml-var SCRIPT_NAME>/misc_/Product/name
misc_ = {
    "Converters": ImageFile("www/converter.gif", globals()),
    "QARepository": ImageFile("www/qarepo.gif", globals()),
    "feedback_gif": ImageFile("www/feedback.gif", globals()),
    "hyperlink_gif": ImageFile("www/hyperlink.gif", globals()),
    "document_gif": ImageFile("www/document.gif", globals()),
    "envelope.gif": ImageFile("www/envelope.gif", globals()),
    "openflowEngine_gif": ImageFile("www/openflowEngine.gif", globals()),
    "edit_comment_gif": ImageFile("www/edit_comment.gif", globals()),
    "delete_comment_gif": ImageFile("www/delete_comment.gif", globals()),
    "manage_doc_gif": ImageFile("www/manage_doc.gif", globals()),
    "view_doc_gif": ImageFile("www/view_doc.gif", globals()),
    "link_gif": ImageFile("www/link.gif", globals()),
    "lockicon_gif": ImageFile("www/lockicon.gif", globals()),
    "plus_gif": ImageFile("www/plus.gif", globals()),
    "minus_gif": ImageFile("www/minus.gif", globals()),
    "sort_asc": ImageFile("www/sort_asc.gif", globals()),
    "sort_desc": ImageFile("www/sort_desc.gif", globals()),
    "sortnot": ImageFile("www/sortnot.gif", globals()),
    "accepted": ImageFile("www/accepted.gif", globals()),
    "work_in_process": ImageFile("www/work_in_process.gif", globals()),
    "Transition.gif": ImageFile("www/Transition.gif", globals()),
    "Activity.gif": ImageFile("www/Activity.gif", globals()),
    "Process.gif": ImageFile("www/Process.gif", globals()),
    "Workitem.gif": ImageFile("www/Workitem.gif", globals()),
    "feedback_comment_png": ImageFile("www/comment.png", globals()),
}
