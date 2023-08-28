from UserList import UserList

from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from constants import DATAFLOW_MAPPINGS, ENGINE_ID, DEFAULT_CATALOG
from Products.Reportek.catalog import searchResults
from Products.Reportek.RepUtils import getToolByName
from DataflowMappingsRecord import DataflowMappingsRecord
from Globals import InitializeClass
from OFS.Folder import Folder
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
__doc__ = """Container for mappings between dataflows and XML schemas"""


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

    def get_dataflow_mapping_records(self, dataflow_uris, web_form_only,
                                     catalog = True):
        """Return the mapping records for the dataflow_uris."""
        if catalog:
            query = {
                'meta_type': DataflowMappingsRecord.meta_type,
                'path': {'query': '/{}'.format(DATAFLOW_MAPPINGS), 'depth': 1}
            }
            if dataflow_uris:
                if isinstance(dataflow_uris, UserList):
                    dataflow_uris = list(dataflow_uris)
                if isinstance(dataflow_uris, list):
                    query['dataflow_uri'] = dataflow_uris
                else:
                    query['dataflow_uri'] = [dataflow_uris]

            return searchResults(
                getToolByName(self, DEFAULT_CATALOG, None), query)

        return (rec for rec in self.objectValues()
                if rec.dataflow_uri in dataflow_uris)

    def getSchemaObjectsForDataflows(self, dataflow_uris, web_form_only,
                                     catalog = True):
        """
        Returns schemas for one or many dataflows
        dataflow_uris - one uri (str) looked after, a list for any uri in it
        or leave None (False) for all dataflows
        web_form_only - if True only Schemas that have webforms will be
        returned
        return - list of found schema objects
        """
        res = []
        mapping = self.get_dataflow_mapping_records(dataflow_uris,
                                                    web_form_only,
                                                    catalog)
        if catalog:
            for brain in mapping:
                for schema in brain.getObject().mapping['schemas']:
                    if not web_form_only or schema['has_webform']:
                        # yield schema # can't yield here if using dtml; it doesn't
                        # know how to iterate
                        res.append(schema)
        else:
            for rec in mapping:
                for schema in rec.mapping['schemas']:
                    if not web_form_only or schema['has_webform']:
                        res.append(schema)

        return res

    def getSchemasForDataflows(self, dataflow_uris=None, web_form_only=False,
                               catalog=True):
        """
        Returns schemas for one or many dataflows
        dataflow_uris - one uri (str) looked after, a list for any uri in it or
        leave None (False) for all dataflows
        web_form_only - if True only Schemas that have webforms will be
        returned
        return - list of found schemas
        """
        schemaObjects = self.getSchemaObjectsForDataflows(
            dataflow_uris, web_form_only, catalog)
        return [schema['url'] for schema in schemaObjects]

    def get_webform_url_for_schema(self, schema, dataflow_uris=None,
                                   web_form_only=False, catalog=True):
        """Return the webform base url for schema"""

        schemaObjects = self.getSchemaObjectsForDataflows(
            dataflow_uris, web_form_only, catalog)
        for schema_obj in schemaObjects:
            if schema_obj.get('url') == schema:
                return schema_obj.get('wf_edit_url')

    security.declarePublic('dataflows_select')
    dataflows_select = PageTemplateFile(
        'zpt/dataflow-mappings/dataflows_select',
        globals())

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
            res.add((record.xls_conversion,
                     getattr(record, 'xls_remove_empty_elems', False)))
        # If all records have the same conversion type, return it
        if len(res) == 1:
            return list(res)[-1]
        # Fallback to default 'split'
        return ('split', False)

    security.declareProtected('View management screens', 'index_html')
    index_html = PageTemplateFile('zpt/dataflow-mappings/index', globals())


InitializeClass(DataflowMappings)
