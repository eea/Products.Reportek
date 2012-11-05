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
      Mappings between dataflows and types of XML files (XML schemas)
"""

# Zope imports
from OFS.SimpleItem import SimpleItem
from Globals import DTMLFile, InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
import Globals

# product imports

manage_addDataflowMappingRecordForm = Globals.DTMLFile('dtml/mapDataflowSchemaAdd', globals())

def manage_addDataflowMappingRecord(self, id, title='', dataflow_uri='', allowedSchemas=[], webformSchemas=[], file_id='', REQUEST=None):
    """ add a new converter object """
    ob = DataflowMappingRecord(id, title, dataflow_uri, allowedSchemas, webformSchemas, file_id)
    self._setObject(id, ob)
    self[id]._fix_attributes()
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)

class DataflowMappingRecord(SimpleItem):
    """ Mappings between dataflows and types of XML files (XML schemas) """

    meta_type = 'Reportek Dataflow Mapping Record'
    icon = 'misc_/Reportek/datafow_mappings_gif'

    security = ClassSecurityInfo()

    def __init__(self, id, title='', dataflow_uri='', allowedSchemas=[], webformSchemas=[], file_id=''):
        """ constructor """
        self.id = id
        self.title = title
        self.dataflow_uri = dataflow_uri
        self.allowedSchemas = filter(None, allowedSchemas)
        self.webformSchemas = filter(None, webformSchemas)
        if file_id == '': self.file_id = id + '.xml'
        else: self.file_id = file_id

    def __setstate__(self,state):
        DataflowMappingRecord.inheritedAttribute('__setstate__')(self, state)
        self._fix_attributes()

    def _fix_attributes(self):
        if not hasattr(self,'allowedSchemas'):
            if self.has_webForm:
                self.allowedSchemas = []
                self.webformSchemas = [self.schema_url]
            else:
                self.allowedSchemas = [self.schema_url]
                self.webformSchemas = []
        # Quick fix because DTML scripts are getting object properties directly.
        if not hasattr(self,'schema_url'):
            if len(self.allowedSchemas) > 0:
                self.schema_url = self.allowedSchemas[0]
                self.has_webForm = 0
            elif len(self.webformSchemas) > 0:
                self.schema_url = self.webformSchemas[0]
                self.has_webForm = 1
            else:
                self.schema_url = "We have no schema"
                self.has_webForm = 0
        if not hasattr(self,'file_id'):
            self.file_id = self.id + '.xml'

    manage_options = (
        (
            {'label' : 'Settings', 'action' : 'manage_settings_html'},
        )
        +
        SimpleItem.manage_options
    )

    security.declareProtected(view_management_screens, 'manage_settings')
    def manage_settings(self, title='', dataflow_uri='', allowedSchemas=[], webformSchemas=[], file_id='', REQUEST=None):
        """ """
        self.title = title
        self.dataflow_uri = dataflow_uri
        self.allowedSchemas = filter(None, allowedSchemas)
        self.webformSchemas = filter(None, webformSchemas)
        self.file_id = file_id
        if len(self.allowedSchemas) > 0:
            self.schema_url = self.allowedSchemas[0]
            self.has_webForm = 0
        elif len(self.webformSchemas) > 0:
            self.schema_url = self.webformSchemas[0]
            self.has_webForm = 1
        else:
            self.schema_url = "We have no schema"
            self.has_webForm = 0
        self._fix_attributes()
        self._p_changed = 1
        if REQUEST:
            message="Content changed"
            return self.manage_settings_html(self,REQUEST,manage_tabs_message=message)

    def set_schema_type(self, schema_url, has_webform):
        """ If the schema_url is listed in the object and the status has
            changed, then move it to the other list
        """
        for l_schema in self.allowedSchemas:
            if l_schema == schema_url and hasWebform == True:
                self.webformSchemas.append(schema_url)
                self.allowedSchemas.remove(schema_url)
                self._p_changed = 1
        for l_schema in self.webformSchemas:
            if l_schema == schema_url and hasWebform == False:
                self.allowedSchemas.append(schema_url)
                self.webformSchemas.remove(schema_url)
                self._p_changed = 1
        self._fix_attributes()

#   def setWebFormAttr(self, hasWF=1):
#       """ """
#       self.has_webForm = hasWF

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = Globals.DTMLFile('dtml/mapDataflowSchemaEdit', globals())

    security.declarePublic('dataflows_select')
    dataflows_select = DTMLFile('dtml/dataflows_select', globals())

Globals.InitializeClass(DataflowMappingRecord)
