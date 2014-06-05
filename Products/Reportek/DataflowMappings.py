__doc__ = """Container for mappings between dataflows and XML schemas"""

from OFS.Folder import Folder
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from UserList import UserList

from constants import DATAFLOW_MAPPINGS, ENGINE_ID


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


    def getSchemaObjectsForDataflows(self, dataflow_uris, web_form_only):
        """
        Returns schemas for one or many dataflows
        dataflow_uris - one uri (str) looked after, a list for any uri in it or leave None (False) for all dataflows
        web_form_only - if True only Schemas that have webforms will be returned
        return - list of found schema objects
        """
        query = {
            'meta_type': RECORD,
            'path': '/DataflowMappings'
        }
        if dataflow_uris:
            if isinstance(dataflow_uris, UserList):
                dataflow_uris = list(dataflow_uris)
            if isinstance(dataflow_uris, list):
                query['dataflow_uri'] = dataflow_uris
            else:
                query['dataflow_uri'] = [dataflow_uris]

        res = []
        for brain in self.Catalog(**query):
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
        return - list of found schema objects
        """
        schemaObjects = self.getSchemaObjectsForDataflows(dataflow_uris, web_form_only)
        return [ schema['url'] for schema in schemaObjects ]


    security.declarePublic('dataflows_select')
    dataflows_select = PageTemplateFile(
            'zpt/dataflow-mappings/dataflows_select',
            globals())


InitializeClass(DataflowMappings)
