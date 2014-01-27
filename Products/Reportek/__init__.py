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

# Zope imports
import Globals
import Zope2
from App.ImageFile import ImageFile
from Products.ZCatalog.ZCatalog import ZCatalog

# Product imports
import RepUtils

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


def create_reportek_indexes(catalog):
    """ Add a series of indexes in it if these are not there """

    available_indexes = catalog.indexes()
    available_metadata = catalog.schema()
    if not ('id' in available_indexes):
        catalog.addIndex('id', 'FieldIndex')
    if not ('id' in available_metadata):
        catalog.addColumn('id')

    if not ('meta_type' in available_indexes):
        catalog.addIndex('meta_type', 'FieldIndex')
    if not ('meta_type' in available_metadata):
        catalog.addColumn('meta_type')

    if not ('bobobase_modification_time' in available_indexes):
        catalog.addIndex('bobobase_modification_time', 'DateIndex')
    if not ('bobobase_modification_time' in available_metadata):
        catalog.addColumn('bobobase_modification_time')

    if not ('activity_id' in available_indexes):
        catalog.addIndex('activity_id', 'FieldIndex')

    if not ('actor' in available_indexes):
        catalog.addIndex('actor', 'FieldIndex')

    if not ('content_type' in available_indexes):
        catalog.addIndex('content_type', 'FieldIndex')

    if not ('country' in available_indexes):
        catalog.addIndex('country', 'FieldIndex')

    if not ('dataflow_uris' in available_indexes):
        catalog.addIndex('dataflow_uris', 'KeywordIndex')

    if not ('getCountryName' in available_indexes):
        catalog.addIndex('getCountryName', 'FieldIndex')

    if not ('instance_id' in available_indexes):
        catalog.addIndex('instance_id', 'FieldIndex')

    if not ('partofyear' in available_indexes):
        catalog.addIndex('partofyear', 'FieldIndex')

    if not ('path' in available_indexes):
        catalog.addIndex('path', 'PathIndex')

    if not ('process_path' in available_indexes):
        catalog.addIndex('process_path', 'FieldIndex')

    if not ('released' in available_indexes):
        catalog.addIndex('released', 'FieldIndex')

    if not ('reportingdate' in available_indexes):
        catalog.addIndex('reportingdate', 'FieldIndex')

    if not ('status' in available_indexes):
        catalog.addIndex('status', 'FieldIndex')

    if not ('xml_schema_location' in available_indexes):
        catalog.addIndex('xml_schema_location', 'FieldIndex')

    if not ('years' in available_indexes):
        catalog.addIndex('years', 'KeywordIndex')


def startup(context):
    import transaction
    app = Zope2.bobo_application()

    create_reportek_objects(app)
    create_reportek_indexes(app[constants.DEFAULT_CATALOG])

    transaction.commit()


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
    "datafow_mappings_gif": ImageFile("www/datafow_mappings.gif", globals()),
    "datafow_mapping_table_gif": ImageFile("www/datafow_mapping_table.gif", globals()),
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
