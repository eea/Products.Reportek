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


"""
Activity class
==============

This class is part of the workflow system

"""

#Zope imports
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass, DTMLFile
from OFS.SimpleItem import SimpleItem
from Products.ZCatalog.CatalogPathAwareness import CatalogAware


class activity(CatalogAware, SimpleItem):
    """ Each activity is responsible for doing something and then forwarding
    the instance """

    meta_type = 'Activity'
    icon = 'misc_/Reportek/Activity.gif'

    manage_options = ({'label' : 'Properties', 'action' : 'manage_editForm'},
                      {'label' : 'View', 'action' : 'index_html'},
                      ) + SimpleItem.manage_options

    security = ClassSecurityInfo()

    def __init__(self,
                 id,
                 split_mode='and',
                 join_mode='and',
                 self_assignable=1,
                 start_mode=0,
                 finish_mode=1,
                 subflow='',
                 push_application='',
                 application='',
                 parameters='{}',
                 title='',
                 description='',
                 kind='standard',
                 complete_automatically=1):
        """ constructor """
        self.id = id
        self.split_mode = split_mode        # 'and', 'xor'
        self.join_mode = join_mode          # 'and', 'xor'
        self.self_assignable = self_assignable
        self.start_mode = start_mode
        self.finish_mode = finish_mode
        self.subflow = subflow
        self.kind = kind
        # kind may be dummy, standard or subflow
        self.application = application
        self.push_application = push_application
        self.title = title
        self.parameters = parameters
        self.description = description
        # used only for activities with an automatic start
        # the workitem will be completed if this parameter is true
        self.complete_automatically = complete_automatically

    def __setstate__(self,state):
        activity.inheritedAttribute('__setstate__')(self, state)
        if not hasattr(self, 'complete_automatically'):
            if self.isAutoStart():
                self.complete_automatically = 1
            else:
                self.complete_automatically = 0

    security.declareProtected('Manage OpenFlow', 'manage_editForm')
    manage_editForm = DTMLFile('dtml/Workflow/activityEdit', globals())

    index_html = DTMLFile('dtml/Workflow/activityIndex', globals())

    security.declareProtected('Manage OpenFlow', 'edit')
    def edit(self,
             split_mode=None,
             join_mode=None,
             self_assignable=None,
             start_mode=None,
             finish_mode=None,
             subflow = None,
             push_application=None,
             application=None,
             title=None,
             description=None,
             kind=None,
             complete_automatically=None,
             REQUEST=None):
        """ changes the activity settings """
        # mode refers to the kind of routing the instance has to undergo
        # and it is either 'and' or 'xor'
        if split_mode:
            self.split_mode = split_mode
        if join_mode:
            self.join_mode = join_mode
        if self_assignable != None:
            self.self_assignable = self_assignable
        if start_mode:
            self.start_mode = 1
        else:
            self.start_mode = 0
        if finish_mode:
            self.finish_mode = 1
        else:
            self.finish_mode = 0
        if subflow != None:
            self.subflow = subflow
        if kind:
            self.kind = kind
        if complete_automatically:
            self.complete_automatically = 1
        else:
            self.complete_automatically = 0
        if application != None:
            self.application = application
        if push_application != None:
            self.push_application = push_application
        if title != None:
            self.title = title
        if description != None:
            self.description = description
        self.reindex_object()
        if REQUEST: return self.manage_editForm(self, REQUEST,manage_tabs_message="Saved changes.")

    security.declareProtected('Manage OpenFlow', 'title_or_id')
    def title_or_id(self):
      """ """
      if self.title:
        return self.title
      else:
        return self.id

    def getIncomingTransitionsNumber(self):
        """ returns all the process transition objects that go to the specified activity """
        return len(filter(lambda x, activity_id=self.id : x.To==activity_id, self.aq_parent.objectValues('Transition')))


    security.declareProtected('Manage OpenFlow', 'isAutoStart')
    def isAutoStart(self):
        """ returns true if the activity start mode is automatic"""
        return self.start_mode and self.kind == 'standard'


    security.declareProtected('Manage OpenFlow', 'isSelfAssignable')
    def isSelfAssignable(self):
        """ returns true if the activity is assignable to self"""
        return self.self_assignable and self.kind=='standard'


    security.declareProtected('Manage OpenFlow', 'isAutoFinish')
    def isAutoFinish(self):
        """ returns true if the activity finish mode is automatic"""
        return self.finish_mode == 1


    security.declareProtected('Manage OpenFlow', 'isStandard')
    def isStandard(self):
        """ returns true if the activity is of 'standard' kind """
        return self.kind == 'standard'


    security.declareProtected('Manage OpenFlow', 'isSubflow')
    def isSubflow(self):
        """ returns true if the activity is a subflow  """
        return self.subflow != ''


    security.declareProtected('Manage OpenFlow', 'isDummy')
    def isDummy(self):
        """ returns true if the activity is a dummy  """
        return self.kind == 'dummy'

    security.declareProtected('Manage OpenFlow', 'isAutoPush')
    def isAutoPush(self):
        """ returns true if the activity push mode is automatic"""
        return self.push_application and self.kind=='standard'

InitializeClass(activity)
