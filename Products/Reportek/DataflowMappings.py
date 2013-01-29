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
# The Original Code is Reportek version 1.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Miruna Badescu, Finsiel Romania

__doc__ = """
      Container fo mappings between dataflows and types of XML files (XML schemas)
"""

# Zope imports
from OFS.Folder import Folder
from Globals import DTMLFile, InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
import Globals

# product imports
import constants
import RepUtils
import DataflowMappingRecord
import DataflowMappingTable


MAPPING_RECORD_METATYPE = 'Reportek Dataflow Mapping Record'
MAPPING_TABLE_METATYPE = 'Reportek Dataflow Mapping Table'


class DataflowMappings(Folder):
    """ Mappings between dataflows and types of XML files (XML schemas) """

    meta_type = 'Reportek Dataflow Mappings'
    icon = 'misc_/Reportek/datafow_mappings_gif'

    manage_options = ( Folder.manage_options[0], ) + \
        ( {'label':'View', 'action':'dataflowsMappingsView'}, ) + \
        Folder.manage_options[2:] 

    def all_meta_types( self, interfaces=None ):
        """
            What can you put inside me? Checks if the legal products are
            actually installed in Zope
        """
        y = [{'name': MAPPING_RECORD_METATYPE,
              'action': 'manage_addDataflowMappingRecordForm',
              'permission': view_management_screens},
             {'name': MAPPING_TABLE_METATYPE,
              'action': 'manage_addDataflowMappingTable_html',
              'permission': view_management_screens}]

        return y

    security = ClassSecurityInfo()

    def __init__(self, title=''):
        """ constructor """
        self.id = constants.DATAFLOW_MAPPINGS

    def getEngine(self):
        return getattr(self, constants.ENGINE_ID)

    security.declarePublic('get_schemas_for_dataflows')
    def get_schemas_for_dataflows(self, dataflow_uris):
        """
        Get a list of XML schemas that apply to `dataflow_uris`. The list
        includes user-friendly title, the schema URI, and the default
        filename for new webform-generated xml uploads:

        >>> DataflowMappings.get_schemas_for_dataflows(
        ...   ['http://rod.eionet.eu.int/obligations/32'])
        [{'title': 'Nationally designated areas (CDDA-1) 2',
          'uri': 'http://dd.eionet.europa.eu/GetSchema?id=TBL7602',
          'webform_filename': 'cdda-2.xml'},
         {'title': 'Nationally designated areas (CDDA-1) 3',
          'uri': 'http://dd.eionet.europa.eu/GetSchema?id=TBL7599',
          'webform_filename': 'cdda-3.xml'}]

        """
        out = []
        for mapping_record in self.objectValues([MAPPING_RECORD_METATYPE]):
            if mapping_record.dataflow_uri not in dataflow_uris:
                continue
            out.append({
                'title': mapping_record.title_or_id(),
                'uri': mapping_record.schema_url,
                'webform_filename': mapping_record.file_id,
            })
        return out

    def getWebformsForDataflows(self, p_dataflow_uris):
        """ returns all the schemas with webforms for given dataflows """
        tmp_list = []
        for x in self.objectValues('Reportek Dataflow Mapping Record'):
            if x.dataflow_uri in p_dataflow_uris:
                tmp_list += x.webformSchemas
        return tmp_list

    def getXMLSchemasForDataflow(self, p_dataflow_uri):
        """ returns all the valid schemas for a dataflow """
        tmp_list = []
        for x in self.objectValues('Reportek Dataflow Mapping Record'):
            if x.dataflow_uri == p_dataflow_uri:
                tmp_list += x.webformSchemas
        return tmp_list
#       return [x.webformSchemas for x in self.objectValues('Reportek Dataflow Mapping Record') if x.dataflow_uri == p_dataflow_uri]

    def getXMLSchemasForDataflows(self, p_dataflow_uris):
        """ returns all the valid schemas for multiple dataflows,
            but doesn't check for the existance of XForms for those schemas
        """
        tmp_list = []
        for x in self.objectValues('Reportek Dataflow Mapping Record'):
            if x.dataflow_uri in p_dataflow_uris:
                tmp_list += x.allowedSchemas
                tmp_list += x.webformSchemas
        return tmp_list
#       return [x.allowedSchemas + x.webformSchemas for x in self.objectValues('Reportek Dataflow Mapping Record') if x.dataflow_uri in p_dataflow_uris]

    def getXMLSchemasForAllDataflows(self):
        """ returns all the valid schemas for multiple dataflows,
            but doesn't check for the existance of XForms for those schemas
        """
        tmp_list = []
        for x in self.objectValues('Reportek Dataflow Mapping Record'):
            tmp_list += x.allowedSchemas
            tmp_list += x.webformSchemas
        return tmp_list
#       return list([x.allowedSchemas + x.webformSchemas for x in self.objectValues('Reportek Dataflow Mapping Record')])

    security.declareProtected('Manage OpenFlow', 'dataflowsMappingsView')
    dataflowsMappingsView = DTMLFile('dtml/mapDataflowsSchemasView', globals())

    security.declareProtected(view_management_screens, 'manage_addDataflowMappingRecordForm')
    manage_addDataflowMappingRecordForm = DataflowMappingRecord.manage_addDataflowMappingRecordForm

    security.declareProtected(view_management_screens, 'manage_addDataflowMappingRecord')
    manage_addDataflowMappingRecord = DataflowMappingRecord.manage_addDataflowMappingRecord

    security.declareProtected(view_management_screens, 'manage_addDataflowMappingTable_html')
    manage_addDataflowMappingTable_html = DataflowMappingTable.manage_addDataflowMappingTable_html

    security.declareProtected(view_management_screens, 'manage_addDataflowMappingTable')
    manage_addDataflowMappingTable = DataflowMappingTable.manage_addDataflowMappingTable

    security.declarePublic('dataflows_select')
    dataflows_select = DTMLFile('dtml/dataflows_select', globals())


Globals.InitializeClass(DataflowMappings)
