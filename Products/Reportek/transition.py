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
# Soren Roug, EEA
# Miruna Badescu, Finsiel Romania


""" transition class

This class is part of the workflow system

"""

# Zope imports
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS.SimpleItem import SimpleItem
from Products.Reportek.CatalogAware import CatalogAware


class transition(CatalogAware, SimpleItem):
    """ Links two activities """

    manage_options = ({'label': 'Properties',
                       'action': 'manage_editTransitionForm'},
                      {'label': 'View', 'action': 'index_html'},
                      ) + SimpleItem.manage_options

    def __init__(self, id, From, To, condition='', description=''):
        if id == "":
            self.id = '%s_%s' % (From, To)
        else:
            self.id = id
        self.From = From
        self.To = To
        self.condition = condition
        self.description = description

    security = ClassSecurityInfo()

    security.declareProtected('Manage OpenFlow', 'manage_editTransitionForm')
    manage_editTransitionForm = PageTemplateFile(
        'zpt/Workflow/transition_edit.zpt', globals())

#   security.declareProtected('Use OpenFlow', 'index_html')
    index_html = PageTemplateFile(
        'zpt/Workflow/transition_index.zpt', globals())

    meta_type = 'Transition'
    icon = 'misc_/Reportek/Transition.gif'

    security.declareProtected('Manage OpenFlow', 'edit')

    def edit(self, condition, From, To, description, REQUEST=None):
        """  """
        self.condition = condition
        self.From = From
        self.To = To
        self.description = description
        self.reindexObject()
        if REQUEST:
            REQUEST.RESPONSE.redirect(
                'manage_editTransitionForm?manage_tabs_message=Saved changes.')


InitializeClass(transition)
