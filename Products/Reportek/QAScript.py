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

import RepUtils
import Globals
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl.Permissions import view_management_screens
from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem
__doc__ = """
      QAScript product module.
      The QAScript define a quality assurance script type.
"""
__version__ = '$Rev$'[6:-2]


manage_addQAScriptForm = PageTemplateFile('zpt/qa/script_add', globals())


def manage_addQAScript(self, id, title='', description='', xml_schema='',
                       workflow=None, content_type_in='', content_type_out='',
                       script_url='', max_size=10, qa_extraparams='',
                       REQUEST=None):
    """ add a new QAScript object """
    ob = QAScript(
        id, title, description, xml_schema, workflow,
        content_type_in, content_type_out, script_url,
        float(max_size),
        RepUtils.utConvertLinesToList(qa_extraparams))
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class QAScript(SimpleItem):
    """ """
    meta_type = "QAScript"

    manage_options = (
        (
            {'label': 'Settings', 'action': 'manage_settings_html'},
        )
        + SimpleItem.manage_options
    )

    def __init__(self, id, title, description, xml_schema, workflow,
                 content_type_in, content_type_out, script_url, max_size,
                 qa_extraparams):
        self.id = id
        self.title = title
        self.description = description
        self.xml_schema = xml_schema
        self.workflow = workflow
        self.content_type_in = content_type_in
        self.content_type_out = content_type_out
        self.script_url = script_url
        self.max_size = max_size
        self.qa_extraparams = qa_extraparams

    # security stuff
    security = ClassSecurityInfo()

    security.declareProtected(view_management_screens, 'manage_settings')

    def manage_settings(self, title='', description='', xml_schema='',
                        workflow=None, content_type_in='',
                        content_type_out='', script_url='', max_size=10,
                        qa_extraparams='', REQUEST=None):
        """ """
        self.title = title
        self.description = description
        self.xml_schema = xml_schema
        self.workflow = workflow
        self.content_type_in = content_type_in
        self.content_type_out = content_type_out
        self.script_url = script_url
        self.max_size = float(max_size)
        self.qa_extraparams = RepUtils.utConvertLinesToList(qa_extraparams)
        self._p_changed = 1
        if REQUEST:
            message = "Content changed."
            return self.manage_settings_html(self, REQUEST,
                                             manage_tabs_message=message)

    security.declareProtected('Use OpenFlow', '__call__')

    def __call__(self, workitem_id, REQUEST=None):
        """ """
        pass

    security.declareProtected(view_management_screens, 'getExtraParameters')

    def getExtraParameters(self):
        """ """
        return RepUtils.utConvertListToLines(self.qa_extraparams)

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = PageTemplateFile('zpt/qa/script_edit', globals())


Globals.InitializeClass(QAScript)
