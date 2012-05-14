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

# Zope imports
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
import DataflowMappings
import ReportekEngine
from StaticServe import StaticServeFromZip

from constants import CONVERTERS_ID, ENGINE_ID, WORKFLOW_ENGINE_ID, DATAFLOW_MAPPINGS, DEFAULT_CATALOG, QAREPOSITORY_ID


def initialize(context):
    """ Reportek initializer """
    app = context._ProductContext__app

    ###########################################
    #   The Engine folder in Root         
    ###########################################
    if hasattr(app, ENGINE_ID):
        repo_engine = getattr(app, ENGINE_ID)
    else:
        try:
            repo_engine = ReportekEngine.ReportekEngine()
            app._setObject(ENGINE_ID, repo_engine)
            transaction.note('Added Reportek Engine')
            transaction.commit()
        except:
            pass
        repo_engine = getattr(app, ENGINE_ID)
    assert repo_engine is not None


    ###########################################
    #   The Converters folder in Root         
    ###########################################
    if hasattr(app, CONVERTERS_ID):
        converters = getattr(app, CONVERTERS_ID)
    else:
        try:
            converters = Converters.Converters()
            app._setObject(CONVERTERS_ID, converters)
            transaction.note('Added Reportek Converters')
            transaction.commit()
        except:
            pass
        converters = getattr(app, CONVERTERS_ID)
    assert converters is not None

    context.registerClass(
       Converter.Converter,
       permission='Add Converters',
       constructors = (
            Converter.manage_addConverterForm,
            Converter.manage_addConverter),
       icon = 'www/conv.gif'
       )

    ###########################################
    #   The QARepository folder in Root         
    ###########################################
    if hasattr(app, QAREPOSITORY_ID):
        qarepo = getattr(app, QAREPOSITORY_ID)
    else:
        try:
            qarepo = QARepository.QARepository()
            app._setObject(QAREPOSITORY_ID, qarepo)
            transaction.note('Added Reportek QARepository')
            transaction.commit()
        except:
            pass
        qarepo = getattr(app, QAREPOSITORY_ID)
    assert qarepo is not None

    context.registerClass(
       QAScript.QAScript,
       permission='Add QAScripts',
       constructors = (
            QAScript.manage_addQAScriptForm,
            QAScript.manage_addQAScript),
       icon = 'www/qascript.gif'
       )

    ###########################################
    #   The dataflow mapping in Root
    ###########################################
    if hasattr(app, DATAFLOW_MAPPINGS):
        dataflow_mapping = getattr(app, DATAFLOW_MAPPINGS)
    else:
        try:
            dataflow_mapping = DataflowMappings.DataflowMappings()
            app._setObject(DATAFLOW_MAPPINGS, dataflow_mapping)
            transaction.note('Added dataflow mapping engine')
            transaction.commit()
        except:
            pass
        dataflow_mapping = getattr(app, DATAFLOW_MAPPINGS)
    assert dataflow_mapping is not None


    ###########################################
    #   The OpenFlowEngine in Root       
    ###########################################
    if hasattr(app, WORKFLOW_ENGINE_ID):
        workflow_engine = getattr(app, WORKFLOW_ENGINE_ID)
    else:
        try:
            workflow_engine = OpenFlowEngine.OpenFlowEngine(WORKFLOW_ENGINE_ID)
            app._setObject(WORKFLOW_ENGINE_ID, workflow_engine)
            transaction.note('Added Reportek Workflow engine')
            transaction.commit()
        except:
            pass
        workflow_engine = getattr(app, WORKFLOW_ENGINE_ID)
    assert workflow_engine is not None

    ###########################################
    #   Default Catalog definition            
    ###########################################
    """ Verify if the Root Folder already contains a ZCatalog
        Add one if it does not
        Add a series of indexes in it if these are not there
    """
    if hasattr(app, DEFAULT_CATALOG):
        catalog = getattr(app, DEFAULT_CATALOG)
    else:
        try:
            catalog = ZCatalog(DEFAULT_CATALOG, 'Default Catalog for Reportek')
            app._setObject(DEFAULT_CATALOG, catalog)
            transaction.note('Added default ZCatalog in Root')
            transaction.commit()
        except:
            pass
        catalog = getattr(app, DEFAULT_CATALOG)
    assert catalog is not None

    # zope 2.6.0 won't add these
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

    if not ('title' in available_indexes):
        catalog.addIndex('title', 'TextIndex')
    if not ('title' in available_metadata):
        catalog.addColumn('title')

    if not ('path' in available_indexes):
        catalog.addIndex('path', 'PathIndex')
    if not ('path' in available_metadata):
        catalog.addColumn('path')

    try:
        catalog.Vocabulary(id='Vocabulary', title='')
    except:
        pass

    if not ('status' in available_indexes):
        catalog.addIndex('status', 'FieldIndex')
    if not ('status' in available_metadata):
        catalog.addColumn('status')

    if not ('activity_id' in available_indexes):
        catalog.addIndex('activity_id', 'FieldIndex')
    if not ('activity_id' in available_metadata):
        catalog.addColumn('activity_id')

    if not ('process_path' in available_indexes):
        catalog.addIndex('process_path', 'FieldIndex')
    if not ('process_path' in available_metadata):
        catalog.addColumn('process_path')

    if not ('instance_id' in available_indexes):
        catalog.addIndex('instance_id', 'FieldIndex')
    if not ('instance_id' in available_metadata):
        catalog.addColumn('instance_id')

    if not ('actor' in available_indexes):
        catalog.addIndex('actor', 'FieldIndex')
    if not ('actor' in available_metadata):
        catalog.addColumn('actor')

    if not ('country' in available_indexes):
        catalog.addIndex('country', 'FieldIndex')
    if not ('country' in available_metadata):
        catalog.addColumn('country')

    if not ('dataflow_uris' in available_indexes):
        catalog.addIndex('dataflow_uris', 'KeywordIndex')
    if not ('dataflow_uris' in available_metadata):
        catalog.addColumn('dataflow_uris')

# xxx
#    if not ('description' in available_indexes):
#        catalog.addIndex('description', 'FieldIndex')
#    if not ('description' in available_metadata):
#        catalog.addColumn('description')
#
#    if not ('customer' in available_indexes):
#        catalog.addIndex('customer', 'FieldIndex')
#    if not ('customer' in available_metadata):
#        catalog.addColumn('customer')

#    if not ('creation_time' in available_indexes):
#        catalog.addIndex('creation_time', 'FieldIndex')
#    if not ('creation_time' in available_metadata):
#        catalog.addColumn('creation_time')

#    if not ('priority' in available_indexes):
#        catalog.addIndex('priority', 'FieldIndex')
#    if not ('priority' in available_metadata):
#        catalog.addColumn('priority')

#    if not ('From' in available_indexes):
#        catalog.addIndex('From', 'FieldIndex')
#    if not ('From' in available_metadata):
#        catalog.addColumn('From')
#
#    if not ('To' in available_indexes):
#        catalog.addIndex('To', 'FieldIndex')
#    if not ('To' in available_metadata):
#        catalog.addColumn('To')

#    if not ('workitems_from' in available_indexes):
#        catalog.addIndex('workitems_from', 'KeywordIndex')
#    if not ('workitems_from' in available_metadata):
#        catalog.addColumn('workitems_from')
#
#    if not ('workitems_to' in available_indexes):
#        catalog.addIndex('workitems_to', 'KeywordIndex')
#    if not ('workitems_to' in available_metadata):
#        catalog.addColumn('workitems_to')

#    if not ('push_roles' in available_indexes):
#        catalog.addIndex('push_roles', 'KeywordIndex')
#    if not ('push_roles' in available_metadata):
#        catalog.addColumn('push_roles')
#
#    if not ('pull_roles' in available_indexes):
#        catalog.addIndex('pull_roles', 'KeywordIndex')
#    if not ('pull_roles' in available_metadata):
#        catalog.addColumn('pull_roles')

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
    'tinymce': StaticServeFromZip('', 'www/tinymce_3_2_4_1.zip', globals()), 
    "feedback_comment_png":  ImageFile("www/comment.png", globals()),
}
