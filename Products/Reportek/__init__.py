# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
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



__doc__ = """Reportek __init__ """
__version__ = '$Rev$'[6:-2]

from config import *
import monitoring
from traceback import format_exception_only
import logging
logger = logging.getLogger("Reportek")

# Zope imports
import Zope2
from App.ImageFile import ImageFile
from Products.ZCatalog.ZCatalog import ZCatalog
from Products.ZCTextIndex.ZCTextIndex import PLexicon

# Product imports

import QARepository
import QAScript
import Converters
import Converter
import Collection
import Referral
import OpenFlowEngine
import RemoteApplication
import RemoteRESTApplication
import DataflowMappings
import ReportekEngine
import ReportekUtilities
import ReportekAPI

from AccessControl.Permissions import manage_users as ManageUsers

import constants

from zope.i18nmessageid import MessageFactory
MessageFactory = MessageFactory('Reportek')

maintenance_options = (
    ZCatalog.manage_options[:1] +
        ({
            'label': "Maintenance",
            'action': 'manage_maintenance'},
        ) +
    ZCatalog.manage_options[1:])

ZCatalog.manage_options = maintenance_options

def create_reportek_objects(app):

    #Add ReportekEngine instance
    try:
        repo_engine = getattr(app, constants.ENGINE_ID)
    except AttributeError:
        repo_engine = ReportekEngine.ReportekEngine()
        app._setObject(constants.ENGINE_ID, repo_engine)

    if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
        import threading
        crPingger = repo_engine.contentRegistryPingger
        if crPingger:
            pingger = threading.Thread(target=ping_remaining_envelopes,
                        name='pingRemainingEnvelopes',
                        args=(app, crPingger))
            pingger.setDaemon(True)
            pingger.start()

    #Add converters folder
    try:
        converters = getattr(app, constants.CONVERTERS_ID)
    except AttributeError:
        converters = Converters.Converters()
        app._setObject(constants.CONVERTERS_ID, converters)

    #Add QARepository folder
    try:
        qarepo = getattr(app, constants.QAREPOSITORY_ID)
    except AttributeError:
        qarepo = QARepository.QARepository()
        app._setObject(constants.QAREPOSITORY_ID, qarepo)

    #Add dataflow mapping
    try:
        dataflow_mapping = getattr(app, constants.DATAFLOW_MAPPINGS)
    except AttributeError:
        dataflow_mapping = DataflowMappings.DataflowMappings()
        app._setObject(constants.DATAFLOW_MAPPINGS, dataflow_mapping)

    #Add OpenFlowEngine instance
    try:
        workflow = getattr(app, constants.WORKFLOW_ENGINE_ID)
    except AttributeError:
        workflow = OpenFlowEngine.OpenFlowEngine(constants.WORKFLOW_ENGINE_ID)
        app._setObject(constants.WORKFLOW_ENGINE_ID, workflow)

    #Add Catalog
    try:
        catalog = getattr(app, constants.DEFAULT_CATALOG)
    except AttributeError:
        catalog = ZCatalog(constants.DEFAULT_CATALOG, 'Reportek Catalog')
        app._setObject(constants.DEFAULT_CATALOG, catalog)

    #Add Reportek Utilities
    try:
        reportek_utilities = getattr(app, constants.REPORTEK_UTILITIES)
    except AttributeError:
        reportek_utilities = ReportekUtilities.ReportekUtilities(
                                    constants.REPORTEK_UTILITIES,
                                    'Reportek Utilities')
        app._setObject(constants.REPORTEK_UTILITIES, reportek_utilities)

    #Add Reportek API
    try:
        reportek_api = getattr(app, constants.REPORTEK_API)
    except AttributeError:
        reportek_api = ReportekAPI.ReportekAPI(
                        constants.REPORTEK_API,
                        'Reportek API')
        app._setObject(constants.REPORTEK_API, reportek_api)

    #Add Registry Management
    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
        import RegistryManagement
        try:
            registry_management = getattr(app, constants.REGISTRY_MANAGEMENT)
        except AttributeError:
            registry_management = RegistryManagement.RegistryManagement(
                                        constants.REGISTRY_MANAGEMENT,
                                        'Fgases Registry')
            app._setObject(constants.REGISTRY_MANAGEMENT, registry_management)

def _strip_protocol_domain(full_url):
    """ Take a full url and return a tuple of path part and protocol+domain part."""
    parts = full_url.split('/')
    # domain.domain.domain.../abs/abs
    i = 1
    if full_url.startswith('http'):
        # http...//domain.domain.domain.../abs/abs
        i = 3
    return '/'.join(parts[i:]), '/'.join(parts[:i])

def ping_remaining_envelopes(app, crPingger):
    import redis
    import pickle
    try:
        rs = redis.Redis(db=REDIS_DATABASE)
        envPathNames = rs.hkeys(constants.PING_ENVELOPES_KEY)
    except Exception as e:
        lines = format_exception_only(e.__class__, e)
        lines.insert(0, "Could not get to redis server")
        logger.warn('. '.join(lines))
        return
    for envPathName in envPathNames:
        # get this fresh on every iteration
        envStatus = rs.hget(constants.PING_ENVELOPES_KEY, envPathName)
        envStatus = pickle.loads(envStatus)
        if not envStatus['op']:
            continue
        envPathOnly, proto_domain = _strip_protocol_domain(envPathName)
        env = app.unrestrictedTraverse(envPathOnly)
        uris = [ envPathName + '/rdf' ]
        innerObjsByMetatype = env._getObjectsForContentRegistry()
        # as we are not called from browser there is no domain part in the absolute_url
        uris.extend( proto_domain +  '/' + o.absolute_url(1)
                    for objs in innerObjsByMetatype.values()
                        for o in objs )
        crPingger.content_registry_ping(uris, ping_argument=envStatus['op'], envPathName=envPathName)

def add_index(name, catalog, meta_type, meta=False):
    if name not in catalog.indexes():
        if meta_type == 'ZCTextIndex':
            item_extras = Empty()
            item_extras.doc_attr = name
            item_extras.index_type = 'Okapi BM25 Rank'
            item_extras.lexicon_id = 'lexicon'
            catalog.addIndex(name, meta_type, item_extras)
        else:
            catalog.addIndex(name, meta_type)

    if meta and name not in catalog.schema():
        #Add Catalog metadata
        catalog.addColumn(name)


def add_lexicon(catalog):
    from Products.ZCTextIndex.HTMLSplitter import HTMLWordSplitter
    from Products.ZCTextIndex.Lexicon import CaseNormalizer
    from Products.ZCTextIndex.Lexicon import StopWordAndSingleCharRemover

    lexicon = PLexicon(
                'lexicon',
                'Lexicon',
                HTMLWordSplitter(),
                CaseNormalizer(),
                StopWordAndSingleCharRemover()
            )
    catalog._setObject('lexicon', lexicon)


def create_reportek_indexes(catalog):
    if not hasattr(catalog, 'lexicon'):
        add_lexicon(catalog)
    add_index('id', catalog, 'FieldIndex', meta=True)
    add_index('title', catalog, 'ZCTextIndex', meta=True)
    add_index('meta_type', catalog, 'FieldIndex', meta=True)
    add_index('bobobase_modification_time', catalog, 'DateIndex', meta=True)
    add_index('activity_id', catalog, 'FieldIndex')
    add_index('actor', catalog, 'FieldIndex')
    add_index('content_type', catalog, 'FieldIndex')
    add_index('country', catalog, 'FieldIndex', meta=True)
    add_index('dataflow_uri', catalog, 'FieldIndex', meta=True)
    add_index('dataflow_uris', catalog, 'KeywordIndex', meta=True)
    add_index('getCountryName', catalog, 'FieldIndex', meta=True)
    add_index('instance_id', catalog, 'FieldIndex')
    add_index('partofyear', catalog, 'FieldIndex')
    add_index('path', catalog, 'PathIndex')
    add_index('process_path', catalog, 'FieldIndex')
    add_index('released', catalog, 'FieldIndex')
    add_index('reportingdate', catalog, 'FieldIndex')
    add_index('status', catalog, 'FieldIndex')
    add_index('xml_schema_location', catalog, 'FieldIndex')
    add_index('years', catalog, 'KeywordIndex')
    add_index('local_unique_roles', catalog, 'KeywordIndex')
    add_index('local_defined_users', catalog, 'KeywordIndex', meta=True)
    add_index('local_defined_roles', catalog, 'FieldIndex', meta=True)
    add_index('document_id', catalog, 'FieldIndex')


class Empty:
    pass


def startup(context):
    import transaction
    app = Zope2.bobo_application()

    create_reportek_objects(app)
    create_reportek_indexes(app[constants.DEFAULT_CATALOG])

    transaction.commit()



if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
    import BdrAuthorizationMiddleware
    from Products.PluggableAuthService.PluggableAuthService import registerMultiPlugin
    registerMultiPlugin(BdrAuthorizationMiddleware.BdrUserFactoryPlugin.meta_type)


def initialize(context):
    """ Reportek initializer """

    from AccessControl.Permissions import view_management_screens
    import blob

    context.registerClass(
       QAScript.QAScript,
       permission='Add QAScripts',
       constructors = (
            QAScript.manage_addQAScriptForm,
            QAScript.manage_addQAScript),
       icon = 'www/qascript.gif'
       )

    context.registerClass(
       Converter.Converter,
       permission='Add Converters',
       constructors = (
            Converter.manage_addConverterForm,
            Converter.manage_addConverter),
       icon = 'www/conv.gif'
       )

    context.registerClass(
       blob.OfsBlobFile,
       permission=view_management_screens,
       constructors = (
            blob.manage_addOfsBlobFile_html,
            blob.manage_addOfsBlobFile),
       icon = 'www/blobfile.png'
       )


    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
        context.registerClass(
            BdrAuthorizationMiddleware.BdrUserFactoryPlugin,
            permission=ManageUsers,
            constructors=(
                BdrAuthorizationMiddleware.manage_addBdrUserFactoryPluginForm,
                BdrAuthorizationMiddleware.addBdrUserFactoryPlugin),
            visibility=None,
            icon='www/openflowEngine.gif'
        )

    ###########################################
    #   Registration of other classes
    ###########################################
    try:
        context.registerClass(
           Collection.Collection,
           permission='Add Collections',
           constructors = (
                Collection.manage_addCollectionForm,
                Collection.manage_addCollection),
           icon = 'www/collection.gif'
           )

        context.registerClass(
           Referral.Referral,
           permission='Add Collections',
           constructors = (
                Referral.manage_addReferralForm,
                Referral.manage_addReferral),
           icon = 'www/referral.gif'
           )

        context.registerClass(
           RemoteApplication.RemoteApplication,
           permission='Add Remote Application',
           constructors = (
                RemoteApplication.manage_addRemoteApplicationForm,
                RemoteApplication.manage_addRemoteApplication),
           icon = 'www/qa_application.gif'
           )

        context.registerClass(
           RemoteRESTApplication.RemoteRESTApplication,
           permission='Add Remote Application',
           constructors = (
                RemoteRESTApplication.manage_addRemoteRESTApplicationForm,
                RemoteRESTApplication.manage_addRemoteRESTApplication),
           icon = 'www/qa_application.gif'
           )

        context.registerHelp()
        context.registerHelpTitle('Zope Help')

        monitoring.initialize()

    except:
        import sys, traceback, string
        type, val, tb = sys.exc_info()
        sys.stderr.write(string.join(traceback.format_exception(type, val, tb), ''))
        del type, val, tb

# Define shared web objects that are used by products.
# This is usually (always ?) limited to images used
# when displaying an object in contents lists.
# These objects are accessed as:
#   <dtml-var SCRIPT_NAME>/misc_/Product/name
misc_ = {
    "Converters": ImageFile("www/converter.gif", globals()),
    "QARepository": ImageFile("www/qarepo.gif", globals()),
    "feedback_gif":  ImageFile("www/feedback.gif", globals()),
    "hyperlink_gif":  ImageFile("www/hyperlink.gif", globals()),
    "document_gif":  ImageFile("www/document.gif", globals()),
    "envelope.gif":  ImageFile("www/envelope.gif", globals()),
    "openflowEngine_gif": ImageFile("www/openflowEngine.gif", globals()),
    "edit_comment_gif":  ImageFile("www/edit_comment.gif", globals()),
    "delete_comment_gif":  ImageFile("www/delete_comment.gif", globals()),
    "manage_doc_gif":  ImageFile("www/manage_doc.gif", globals()),
    "view_doc_gif":  ImageFile("www/view_doc.gif", globals()),
    "link_gif":  ImageFile("www/link.gif", globals()),
    "lockicon_gif":  ImageFile("www/lockicon.gif", globals()),
    "plus_gif":  ImageFile("www/plus.gif", globals()),
    "minus_gif":  ImageFile("www/minus.gif", globals()),
    "sort_asc":  ImageFile("www/sort_asc.gif", globals()),
    "sort_desc":  ImageFile("www/sort_desc.gif", globals()),
    "sortnot":  ImageFile("www/sortnot.gif", globals()),
    "accepted":  ImageFile("www/accepted.gif", globals()),
    "work_in_process":  ImageFile("www/work_in_process.gif", globals()),

    "Transition.gif":  ImageFile("www/Transition.gif", globals()),
    "Activity.gif":  ImageFile("www/Activity.gif", globals()),
    "Process.gif":  ImageFile("www/Process.gif", globals()),
    "Workitem.gif":  ImageFile("www/Workitem.gif", globals()),
    "feedback_comment_png":  ImageFile("www/comment.png", globals()),
}
