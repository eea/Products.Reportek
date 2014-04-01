__doc__ = "Container for mappings between dataflows and XML schemas"

from OFS.Folder import Folder
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from constants import DATAFLOW_MAPPINGS, ENGINE_ID


MAPPING_RECORD = 'Reportek Dataflow Mapping Record'
RECORD = 'Dataflow Mappings Record'


class DataflowMappings(Folder):
    """ Container for mappings between dataflows and XML schemas """

    manage_options = (
            Folder.manage_options[0],
            {'label':'View', 'action':'dataflowsMappingsView'}
            ) + Folder.manage_options[2:]


    def all_meta_types( self, interfaces=None ):
        return [
            {
                'name': RECORD,
                'action': '+/add_record',
                'permission': view_management_screens
            }]


    security = ClassSecurityInfo()


    def __init__(self):
        self.id = DATAFLOW_MAPPINGS


    def getEngine(self):
         return getattr(self, ENGINE_ID)


    def getWebformsForDataflows(self, dataflow_uris):
        """ Returns all schemas with webforms for a list of dataflows """
        return [
            schema
            for r in self.objectValues(MAPPING_RECORD)
                if r.dataflow_uri in dataflow_uris and r.webformSchemas
            for schema in r.webformSchemas
        ]


    def getXMLSchemasForDataflow(self, dataflow_uri):
        """ Returns all schemas for a given dataflow """
        # possbile bug, should return also r.allowedSchemas
        return [
            schema
            for r in self.objectValues(MAPPING_RECORD)
                if r.dataflow_uri == dataflow_uri
            for schema in r.webformSchemas
        ]


    def getXMLSchemasForDataflows(self, dataflow_uris):
        """ Returns all schemas for a list of dataflows """
        return [
            schema
            for r in self.objectValues(MAPPING_RECORD)
                if r.dataflow_uri in dataflow_uris
            for schema in r.allowedSchemas + r.webformSchemas
        ]

    def getXMLSchemasForAllDataflows(self):
        """ Returns all schemas for all dataflows """
        return [
            schema
            for r in self.objectValues(MAPPING_RECORD)
            for schema in r.allowedSchemas + r.webformSchemas
        ]


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
        for mapping_record in self.objectValues([MAPPING_RECORD]):
            if mapping_record.dataflow_uri not in dataflow_uris:
                continue
            out.append({
                'title': mapping_record.title_or_id(),
                'uri': mapping_record.schema_url,
                'webform_filename': mapping_record.file_id,
            })
        for mapping_table in self.objectValues([RECORD]):
            if mapping_table.dataflow_uri not in dataflow_uris:
                continue
            for schema in mapping_table.mapping:
                out.append({
                    'title': schema['name'],
                    'uri': schema['url'],
                })
        return out

    security.declareProtected('Manage OpenFlow', 'dataflowsMappingsView')
    dataflowsMappingsView = PageTemplateFile(
            'zpt/dataflow-mappings/mapDataflowsSchemasView',
            globals())

    security.declarePublic('dataflows_select')
    dataflows_select = PageTemplateFile(
            'zpt/dataflow-mappings/dataflows_select',
            globals())

    def truncate(self, text):
        if len(text)<=80:
            return text
        return '%s ...' % text[:77]

InitializeClass(DataflowMappings)
