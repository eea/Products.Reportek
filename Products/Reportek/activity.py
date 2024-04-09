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


# Zope imports
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS.SimpleItem import SimpleItem
from Products.Reportek.CatalogAware import CatalogAware
from Products.Reportek import constants
from Products.Reportek.BaseRemoteApplication import BaseRemoteApplication


class activity(CatalogAware, SimpleItem):
    """ Each activity is responsible for doing something and then forwarding
    the instance """

    meta_type = 'Activity'
    icon = 'misc_/Reportek/Activity.gif'

    manage_options = ({'label': 'Properties', 'action': 'manage_editForm'},
                      {'label': 'View', 'action': 'index_html'},
                      ) + SimpleItem.manage_options

    security = ClassSecurityInfo()

    def __init__(self,
                 id,
                 split_mode='and',
                 join_mode='and',
                 self_assignable=1,
                 start_mode=0,
                 bundle_mode=0,
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
        self.bundle_mode = bundle_mode
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

    security.declareProtected('Manage OpenFlow', 'manage_editForm')
    manage_editForm = PageTemplateFile(
        'zpt/Workflow/activity_edit.zpt', globals())

    index_html = PageTemplateFile('zpt/Workflow/activity_index.zpt', globals())

    security.declareProtected('Manage OpenFlow', 'edit')

    def edit(self,
             split_mode=None,
             join_mode=None,
             self_assignable=None,
             start_mode=None,
             bundle_mode=None,
             finish_mode=None,
             subflow=None,
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
        if self_assignable is not None:
            self.self_assignable = self_assignable
        if start_mode:
            self.start_mode = 1
        else:
            self.start_mode = 0
        if bundle_mode:
            self.bundle_mode = 1
        else:
            self.bundle_mode = 0
        if finish_mode:
            self.finish_mode = 1
        else:
            self.finish_mode = 0
        if subflow is not None:
            self.subflow = subflow
        if kind:
            self.kind = kind
        if complete_automatically:
            self.complete_automatically = 1
        else:
            self.complete_automatically = 0
        if application is not None:
            self.application = application
        if push_application is not None:
            self.push_application = push_application
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        self.reindexObject()
        if REQUEST:
            REQUEST.RESPONSE.redirect(
                'manage_editForm?manage_tabs_message=Saved changes.')

    security.declareProtected('Manage OpenFlow', 'title_or_id')

    def title_or_id(self):
        """ """
        if self.title:
            return self.title
        else:
            return self.id

    def get_mapped_application(self):
        app_url = self.mapped_application_details()['path']
        if not app_url.startswith('/'):
            app_url = '/{}'.format(app_url)
        return self.unrestrictedTraverse(app_url, None)

    def mapped_application_details(self):
        root = self.getPhysicalRoot()
        engine = getattr(root, constants.WORKFLOW_ENGINE_ID)
        proc = self.aq_parent

        resp = {'path': "",
                'parent_url': "",
                'missing': None,
                'mapped_by_path': None}

        mapped_by_path = False

        # check in Applications/Common/
        try:
            app_path = '%s/%s/%s' % (constants.APPLICATIONS_FOLDER_ID,
                                     'Common', self.id)
            application = root.unrestrictedTraverse(app_path)
            if application and not mapped_by_path:
                mapped_by_path = True
        except KeyError:
            app_path = None

        # check in Applications/proc_name/
        try:
            app_path = '%s/%s/%s' % (constants.APPLICATIONS_FOLDER_ID,
                                     proc.id, self.id)
            application = root.unrestrictedTraverse(app_path)
            if application:
                mapped_by_path = True
        except KeyError:
            app_path = None

        if mapped_by_path:
            resp.update(
                {'path': application.absolute_url(1),
                 'parent_url': application.aq_parent.absolute_url(),
                 'missing': False,
                 'mapped_by_path': mapped_by_path}
            )
            return resp

        # check in activity.application
        elif self.application:
            if engine._applications.get(self.application):
                app_path = engine._applications[self.application]['url']
            try:
                application = root.unrestrictedTraverse(app_path)
                resp.update(
                    # WARNING:
                    # app_path doesn't have a leading '/' in this case
                    # and if we call the application from the envelope context
                    # it will start the traversing from the envelope and it
                    # will find the application by acquisition.
                    # e.g.:
                    # ../col/env/Applications/CDDA/EnvelopeDecideStartActivity.py
                    # and context.getMySelf() will work in this case
                    {'path': application.absolute_url(1),
                     'parent_url': application.aq_parent.absolute_url(),
                     'missing': False,
                     'mapped_by_path': mapped_by_path}
                )
            except KeyError:
                application = None
                resp.update(
                    {'path': app_path,
                     'parent_url': None,
                     'missing': True,
                     'mapped_by_path': mapped_by_path}
                )
            finally:
                return resp
        else:
            resp['mapped_by_path'] = False
            return resp

    def getIncomingTransitionsNumber(self):
        """ returns all the process transition objects that go to the
            specified activity
        """
        return len([tr for tr in self.aq_parent.objectValues('Transition')
                    if tr.To == self.id])

    security.declareProtected('Manage OpenFlow', 'isAutoStart')

    def isAutoStart(self):
        """ returns true if the activity start mode is automatic"""
        return self.start_mode and self.kind == 'standard'

    security.declareProtected('Manage OpenFlow', 'isBundled')

    def isBundled(self):
        """ returns true if the activity start mode is automatic"""
        return getattr(self, 'bundle_mode', 0) and self.kind == 'standard'

    security.declareProtected('Manage OpenFlow', 'isSelfAssignable')

    def isSelfAssignable(self):
        """ returns true if the activity is assignable to self"""
        return self.self_assignable and self.kind == 'standard'

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
        return self.push_application and self.kind == 'standard'

    def get_wf_status(self):
        mapped_app = self.get_mapped_application()
        if isinstance(mapped_app, BaseRemoteApplication):
            return getattr(mapped_app, '_wf_state_type', 'forward')
        elif isinstance(mapped_app, PageTemplateFile):
            return 'manual'
        return 'forward'


InitializeClass(activity)
