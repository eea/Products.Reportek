""" Multiple dataflow mappings for a single obligation """

import json

from OFS.SimpleItem import SimpleItem
from Globals import DTMLFile, InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Products.PageTemplates.PageTemplateFile import PageTemplateFile


manage_addDataflowMappingTable_html = PageTemplateFile(
    'zpt/dataflow_mapping_table_create.zpt', globals())


def manage_addDataflowMappingTable(self, id, title, dataflow_uri,
                                   REQUEST=None):
    """ add a new converter object """
    ob = DataflowMappingTable(id, title, dataflow_uri)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class DataflowMappingTable(SimpleItem):
    """ Mappings between dataflows and types of XML files (XML schemas) """

    meta_type = 'Reportek Dataflow Mapping Table'
    icon = 'misc_/Reportek/datafow_mapping_table_gif'

    security = ClassSecurityInfo()

    manage_options = (
        {'label': 'Schemas', 'action': 'manage_html'},
    ) + SimpleItem.manage_options

    def __init__(self, id, title, dataflow_uri):
        self.id = id
        self.title = title
        self.dataflow_uri = dataflow_uri
        self.mapping = {}

    security.declarePrivate('mapping')
    @property
    def mapping(self):
        return json.loads(self.mapping_json)

    @mapping.setter
    def mapping(self, value):
        self.mapping_json = json.dumps(value)

    security.declareProtected(view_management_screens, 'update')
    def update(self, title, dataflow_uri, REQUEST=None):
        """ """
        self.title = title
        self.dataflow_uri = dataflow_uri
        self.mapping = {}
        if REQUEST:
            return self.manage_settings_html(self, REQUEST,
                                             manage_tabs_message="Saved.")

    security.declareProtected(view_management_screens, 'manage_html')
    manage_html = PageTemplateFile('zpt/dataflow_mapping_table.zpt', globals())

    security.declarePublic('dataflows_select')
    dataflows_select = DTMLFile('dtml/dataflows_select', globals())

InitializeClass(DataflowMappingTable)
