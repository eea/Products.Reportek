__doc__ = """Container for mappings between dataflows and XML schemas"""

from OFS.Folder import Folder
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.constants import DATAFLOW_MAPPINGS
from UserList import UserList

from constants import DATAFLOW_MAPPINGS, ENGINE_ID
from DataflowMappingsRecord import DataflowMappingsRecord


class DataflowMappings(Folder):
    """ Container for mappings between dataflows and XML schemas """

    manage_options = (Folder.manage_options[0],
                      {'label': 'View', 'action': 'index_html'}
                     ) + Folder.manage_options[2:]

    meta_type = 'Dataflow Mappings'

    def all_meta_types(self, interfaces=None):
        return [
            {
                'name': DataflowMappingsRecord.meta_type,
                'action': '+/add_record',
                'permission': view_management_screens
            }]

    security = ClassSecurityInfo()

    def __init__(self):
        self.id = DATAFLOW_MAPPINGS

    def getEngine(self):
        return getattr(self, ENGINE_ID)

    def get_dataflow_mapping_records(self, dataflow_uris, web_form_only):
        """Return the mapping records for the dataflow_uris."""
        query = {
            'meta_type': DataflowMappingsRecord.meta_type,
            'path': '/{}'.format(DATAFLOW_MAPPINGS)
        }
        if dataflow_uris:
            if isinstance(dataflow_uris, UserList):
                dataflow_uris = list(dataflow_uris)
            if isinstance(dataflow_uris, list):
                query['dataflow_uri'] = dataflow_uris
            else:
                query['dataflow_uri'] = [dataflow_uris]

        return self.Catalog(**query)

    def getSchemaObjectsForDataflows(self, dataflow_uris, web_form_only):
        """
        Returns schemas for one or many dataflows
        dataflow_uris - one uri (str) looked after, a list for any uri in it or leave None (False) for all dataflows
        web_form_only - if True only Schemas that have webforms will be returned
        return - list of found schema objects
        """
        brains = self.get_dataflow_mapping_records(dataflow_uris,
                                                   web_form_only)
        res = []
        for brain in brains:
            for schema in brain.getObject().mapping['schemas']:
                if not web_form_only or schema['has_webform']:
                    # yield schema # can't yield here if using dtml; it doesn't know how to iterate
                    res.append(schema)
        return res


    def getSchemasForDataflows(self, dataflow_uris=None, web_form_only=False):
        """
        Returns schemas for one or many dataflows
        dataflow_uris - one uri (str) looked after, a list for any uri in it or leave None (False) for all dataflows
        web_form_only - if True only Schemas that have webforms will be returned
        return - list of found schemas
        """
        schemaObjects = self.getSchemaObjectsForDataflows(dataflow_uris, web_form_only)
        return [ schema['url'] for schema in schemaObjects ]

    security.declarePublic('dataflows_select')
    dataflows_select = PageTemplateFile(
            'zpt/dataflow-mappings/dataflows_select',
            globals())

    def get_xls_conversion_type(self, dataflow_uris=None, web_form_only=False):
        """Return the xls conversion type."""
        brains = self.get_dataflow_mapping_records(dataflow_uris,
                                                   web_form_only)
        res = set()
        for brain in brains:
            record = brain.getObject()
            res.add(record.xls_conversion)
        # If all records have the same conversion type, return it
        if len(res) == 1:
            return list(res)[-1]
        # Fallback to default 'split'
        return 'split'

    security.declareProtected('View management screens', 'index_html')
    index_html = PageTemplateFile('zpt/dataflow-mappings/index', globals())

InitializeClass(DataflowMappings)
