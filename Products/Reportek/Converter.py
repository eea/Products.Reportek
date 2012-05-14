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
# Cornel Nitu, Finsiel Romania

__doc__ = """
      Converter product module.
      The Converter define a conversion type
      .

      $Id$
"""
__version__='$Rev$'[6:-2]

from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
import Globals
import RepUtils

manage_addConverterForm = Globals.DTMLFile('dtml/converterAdd', globals())

def manage_addConverter(self, id, title='', convert_url='', ct_input='', ct_output='', ct_schema='', ct_extraparams='', description='', suffix='', REQUEST=None):
    """ add a new converter object """
    ob = Converter(id, title, convert_url, ct_input, ct_output, ct_schema, RepUtils.utConvertLinesToList(ct_extraparams), description, suffix)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)

class Converter(SimpleItem):
    """ """
    meta_type = "Converter"

    manage_options = (
        (
            {'label' : 'Settings', 'action' : 'manage_settings_html'},
        )
        +
        SimpleItem.manage_options
    )

    def __init__(self, id, title, convert_url, ct_input, ct_output, ct_schema, ct_extraparams, description, suffix):
        """ """
        self.id = id
        self.title = title
        self.convert_url = convert_url
        self.ct_input = ct_input
        self.ct_output = ct_output
        self.ct_schema = ct_schema
        self.ct_extraparams = ct_extraparams
        self.description = description
        self.suffix = suffix[suffix.find('.')+1:] # Drop everything up to period.

    def __setstate__(self, state):
        """ update """
        Converter.inheritedAttribute('__setstate__')(self, state)
        if not hasattr(self, 'ct_schema'):
            self.ct_schema = ''
        if not hasattr(self, 'ct_extraparams'):
            self.ct_extraparams = ''
        if not hasattr(self, 'description'):
            self.description = ''
        if not hasattr(self, 'suffix'):
            self.suffix = ''

    #security stuff
    security = ClassSecurityInfo()

    security.declareProtected(view_management_screens, 'manage_settings')
    def manage_settings(self, title='', ct_input='', ct_output='', ct_schema='', convert_url='', ct_extraparams='', description='', suffix='', REQUEST=None):
        """ """
        self.title = title
        self.convert_url = convert_url
        self.ct_input = ct_input
        self.ct_output = ct_output
        self.ct_schema = ct_schema
        self.ct_extraparams = RepUtils.utConvertLinesToList(ct_extraparams)
        self.description = description
        self.suffix = suffix[suffix.find('.')+1:] # Drop everything up to period.
        self._p_changed = 1
        if REQUEST:
            message="Content changed."
            return self.manage_settings_html(self,REQUEST,manage_tabs_message=message)

    security.declareProtected(view_management_screens, 'getExtraParameters')
    def getExtraParameters(self):
        """ """
        return RepUtils.utConvertListToLines(self.ct_extraparams)

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = Globals.DTMLFile('dtml/converterEdit', globals())

Globals.InitializeClass(Converter)
