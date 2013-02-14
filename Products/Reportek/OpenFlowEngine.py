#   (c) 2001,2003 Icube
#   (c) 2003,2006 European Environment Agency
#   Portions created by Finsiel are Copyright (C) European Environment Agency.
#
#   This file is part of Openflow-refactored.
#
#   Openflow is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   Openflow is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with Openflow; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Contributor(s):
# Miruna Badescu, Finsiel Romania
#

import re
from collections import defaultdict

# Zope imports
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Globals import InitializeClass, DTMLFile
from DateTime import DateTime
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Products.ZCatalog.ZCatalog import ZCatalog
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek import constants
from Products.Reportek import exceptions
import Products
#from webdav.WriteLockInterface import WriteLockInterface

# product imports
from expression import exprNamespace
from expression import Expression
import RepUtils
import process
from openflow2xpdl import OpenFlow2Xpdl
from xpdl2openflow import xpdlparser

# custom exceptions imports
from exceptions import CannotPickProcess, NoProcessAvailable

manage_addOpenFlowEngineForm = DTMLFile('dtml/Workflow/workflowEngineAdd', globals())

def manage_addOpenFlowEngine(self, id, title, REQUEST=None):
    """Add a new OpenFlowEngine object
    """
    ob = OpenFlowEngine(id, title)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class OpenFlowEngine(Folder):
    """ A openflow contains all the processes of the openflow """

    #__implements__ = (WriteLockInterface,)
    icon = 'misc_/Reportek/openflowEngine_gif'
    meta_type='Workflow Engine'

    security = ClassSecurityInfo()

    manage_options = Folder.manage_options[0:1] + \
                 ( {'label': 'Roles', 'action': 'Roles', 'help' : ('Reportek', 'roles.stx')},
                   {'label': 'Import/Export', 'action': 'workflow_impex'},
                  {'label': 'Applications', 'action': 'Applications', 'help' : ('Reportek', 'applications.stx')},
                  {'label':'Map processes', 'action':'workflow_map_processes'}) + \
                 Folder.manage_options[2:]

    def __init__(self, id, title=''):
        """ constructor """
        self.id = id
        self.title = title
        self._applications = {}
        self._activitiesPushableOnRole={}
        self._activitiesPullableOnRole={}
        # process_mappings: dictionary that keeps the way every process 
        # is fit for a subset of dataflows and countries
        self.process_mappings = {}

    def all_meta_types( self, interfaces=None ):
        """
            What can you put inside me? Checks if the legal products are
            actually installed in Zope
        """
        types = ['LDAPUserFolder','User Folder', 'Script (Python)', 'DTML Method', 'DTML Document', 'Page Template']

        y = [  {'name': 'Process', 'action': 'manage_addProcessForm', 'permission': 'Manage OpenFlow'} ]

        for x in Products.meta_types:
            if x['name'] in types:
                y.append(x)
        return y

    security.declareProtected('Manage OpenFlow', 'manage_addProcess')
    manage_addProcess = process.manage_addProcess

    security.declareProtected('Manage OpenFlow', 'manage_addProcessForm')
    manage_addProcessForm = process.manage_addProcessForm

    security.declareProtected('Manage OpenFlow', 'manage_addApplicationForm')
    manage_addApplicationForm = DTMLFile('dtml/Workflow/applicationAdd', globals())

    security.declareProtected('Manage OpenFlow', 'manage_editApplicationForm')
    manage_editApplicationForm = DTMLFile('dtml/Workflow/applicationEdit', globals())

    security.declareProtected('Manage OpenFlow', 'manage_editActivitiesPushableOnRole')
    manage_editActivitiesPushableOnRole = PageTemplateFile('zpt/Workflow/manage_editActivitiesPushableOnRole', globals())

    security.declareProtected('Manage OpenFlow', 'manage_editActivitiesPullableOnRole')
    manage_editActivitiesPullableOnRole = PageTemplateFile('zpt/Workflow/manage_editActivitiesPullableOnRole', globals())

    security.declareProtected('Manage OpenFlow', 'Roles')
    Roles = PageTemplateFile('zpt/Workflow/workflowRoles', globals())

    security.declareProtected('Manage OpenFlow', 'Applications')
    Applications = PageTemplateFile('zpt/Workflow/workflowApplications', globals())

    ##################################################
    # Openflow specific functions                    #
    ##################################################

    security.declareProtected('Manage OpenFlow', 'editActivitiesPushableOnRole')
    def editActivitiesPushableOnRole(self, role, process, activities=None, REQUEST=None):
        """ Edit the link between a role and activities of a process """
        if activities == None: activities = []
        process_path = self.id + '/' + process
        if self._activitiesPushableOnRole.has_key(role) and \
               self._activitiesPushableOnRole[role].has_key(process):
            old_activities = self._activitiesPushableOnRole[role][process]
        else:
            old_activities = []
        removeList = [x for x in old_activities if x not in activities]
        if removeList:
            for i in self.Catalog.searchResults(meta_type='Workitem',process_path=process_path, activity_id=removeList):
                w = i.getObject()
                if w and role in w.push_roles:
                    w.push_roles.remove(role)
                    w._p_changed = 1
                    w.reindex_object()
        addList = [x for x in activities if x not in old_activities]
        if addList:
            for i in self.Catalog.searchResults(meta_type='Workitem', process_path=process_path, activity_id=addList):
                w = i.getObject()
                if w and role not in w.push_roles:
                    w.push_roles.append(role)
                    w._p_changed = 1
                    w.reindex_object()
        if activities:
            if not self._activitiesPushableOnRole.has_key(role):
                self._activitiesPushableOnRole[role] = {}
            self._activitiesPushableOnRole[role][process] = activities
        else:
            self.deleteProcessWithActivitiesPushableOnRole(role, process)
        self._p_changed = 1
        if REQUEST: REQUEST.RESPONSE.redirect('Roles')

    security.declareProtected('Manage OpenFlow', 'getActivitiesPushableOnRole')
    def getActivitiesPushableOnRole(self):
        """ """
        return self._activitiesPushableOnRole

    security.declareProtected('Manage OpenFlow', 'deleteProcessWithActivitiesPushableOnRole')
    def deleteProcessWithActivitiesPushableOnRole(self, role, process):
        """ Delete the link between a role and activities of a process """
        if self._activitiesPushableOnRole.has_key(role):
            if self._activitiesPushableOnRole[role].has_key(process):
                del self._activitiesPushableOnRole[role][process]
                if self._activitiesPushableOnRole[role] == {}:
                    self.deleteRoleWithActivitiesPushable(role)
        self._p_changed = 1

    security.declareProtected('Manage OpenFlow', 'deleteRoleWithActivitiesPushable')
    def deleteRoleWithActivitiesPushable(self, role):
        """ Delete a role """
        if self._activitiesPushableOnRole.has_key(role):
            del self._activitiesPushableOnRole[role]
        self._p_changed = 1

    security.declareProtected('Manage OpenFlow', 'addRoleWithActivitiesPushable')
    def addRoleWithActivitiesPushable(self, role, process):
        """ Add a role """
        self._activitiesPushableOnRole[role] = {}
        self._p_changed = 1

    security.declareProtected('Manage OpenFlow', 'editActivitiesPullableOnRole')
    def editActivitiesPullableOnRole(self, role, process, activities=None, REQUEST=None):
        """ Edit the link between a role and activities of a process """
        process_path = self.id + '/' + process
        if activities == None: activities = []
        if self._activitiesPullableOnRole.has_key(role) and \
               self._activitiesPullableOnRole[role].has_key(process):
            old_activities = self._activitiesPullableOnRole[role][process]
        else:
            old_activities = []
        removeList = [x for x in old_activities if x not in activities]
        if removeList:
            for i in self.Catalog.searchResults(meta_type='Workitem',process_path=process_path, activity_id=removeList):
                w = i.getObject()
                if w and role in w.pull_roles:
                    w.pull_roles.remove(role)
                    w._p_changed = 1
                    w.reindex_object()
        addList = [x for x in activities if x not in old_activities]
        if addList:
            for i in self.Catalog.searchResults(meta_type='Workitem', process_path=process_path, activity_id=addList):
                w = i.getObject()
                if w and role not in w.pull_roles:
                    w.pull_roles.append(role)
                    w._p_changed = 1
                    w.reindex_object()
        if activities:
            if not self._activitiesPullableOnRole.has_key(role):
                self._activitiesPullableOnRole[role] = {}
            self._activitiesPullableOnRole[role][process] = activities
        else:
            self.deleteProcessWithActivitiesPullableOnRole(role, process)
        self._p_changed = 1
        if REQUEST: REQUEST.RESPONSE.redirect('Roles')

    security.declareProtected('Manage OpenFlow', 'getActivitiesPullableOnRole')
    def getActivitiesPullableOnRole(self):
        """ """
        return self._activitiesPullableOnRole

    security.declareProtected('Manage OpenFlow', 'deleteProcessWithActivitiesPullableOnRole')
    def deleteProcessWithActivitiesPullableOnRole(self, role, process):
        """ Delete the link between a role and activities of a process """
        if self._activitiesPullableOnRole.has_key(role):
            if self._activitiesPullableOnRole[role].has_key(process):
                del self._activitiesPullableOnRole[role][process]
                if self._activitiesPullableOnRole[role] == {}:
                    self.deleteRoleWithActivitiesPullable(role)
        self._p_changed = 1

    security.declareProtected('Manage OpenFlow', 'deleteRoleWithActivitiesPullable')
    def deleteRoleWithActivitiesPullable(self, role):
        """ Delete a role """
        if self._activitiesPullableOnRole.has_key(role):
            del self._activitiesPullableOnRole[role]
        self._p_changed = 1

    security.declareProtected('Manage OpenFlow', 'addRoleWithActivitiesPullable')
    def addRoleWithActivitiesPullable(self, role, process):
        """ Add a role """
        self._activitiesPullableOnRole[role] = {}
        self._p_changed = 1

    security.declareProtected('Use OpenFlow', 'usersAssignableTo')
    def usersAssignableTo(self, process_id, activity_id):
        """ List all user name assignable to activity in the process """
        result=[]
        current=self
        apon = self._activitiesPullableOnRole
        pullable_roles = [r for r in apon.keys() \
                          if apon[r].has_key(process_id) and \
                          activity_id in apon[r][process_id]]
        while current is not None:
            if hasattr(current, 'acl_users'):
                for user in getattr(current, 'acl_users').getUsers():
                    name = user.getUserName()
                    roles_ok = [r for r in user.getRoles() if r in pullable_roles]
                    if roles_ok and name not in result:
                        result.append(name)
            try:
                current = current.aq_parent
            except:
                current = None
        return result

    def canPullActivity(self, p_activity_id, p_roles, p_process_id):
        """ """
        l_activitiespullableonrole = self.getActivitiesPullableOnRole()
        for l_role in p_roles:
            if l_activitiespullableonrole.has_key(l_role):
                l_activities_ids = l_activitiespullableonrole[l_role].get(p_process_id, [])
                if p_activity_id in l_activities_ids:
                    return 1
        return 0

    security.declareProtected('Manage OpenFlow', 'deleteProcess')
    def deleteProcess(self, proc_ids=None, REQUEST=None):
        """ removes specified process """
        self.manage_delObjects(proc_ids)
        if REQUEST: REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    def getPushRoles(self, process_id, activity_id):
        """ """
        push_roles = []
        tmpRole = self._activitiesPushableOnRole
        for role in tmpRole.keys():
            if tmpRole[role].has_key(process_id):
                if activity_id in tmpRole[role][process_id]:
                    push_roles.append(role)
        return push_roles

    def getPullRoles(self, process_id, activity_id):
        """ """
        pull_roles = []
        tmpRole = self._activitiesPullableOnRole
        for role in tmpRole.keys():
            if tmpRole[role].has_key(process_id):
                if activity_id in tmpRole[role][process_id]:
                    pull_roles.append(role)
        return pull_roles

    def getWorkitems(self, process_path, statuses_list):
        """ Finds all workitems from a process in certain statuses 
            and sorts them by last modification time
        """
        ret_list = self.Catalog.searchResults(meta_type='Workitem',
                            process_path=process_path,
                            status=statuses_list)
        return RepUtils.utSortByAttr(ret_list, 'bobobase_modification_time')

    ##################################################
    # Applications stuff                             #
    ##################################################

    security.declareProtected('Manage OpenFlow', 'addApplication')
    def addApplication(self, name, link, REQUEST=None):
        """ adds an application declaration """
        if not name in self._applications.keys():
            self._applications[name] = {'url' : link}
            self._p_changed = 1
            if REQUEST:
                REQUEST.RESPONSE.redirect('Applications')

    security.declareProtected('Manage OpenFlow', 'deleteApplication')
    def deleteApplication(self, app_ids=None, REQUEST=None):
        """ removes an application """
        for name in app_ids:
            if name in self._applications.keys():
                del(self._applications[name])
        self._p_changed = 1
        if REQUEST: REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    security.declareProtected('Manage OpenFlow', 'editApplication')
    def editApplication(self, name, link, REQUEST=None):
        """ edits an application declaration """
        if name not in self._applications.keys():
            return
        self._applications[name] = {'url' : link}
        self._p_changed = 1
        if REQUEST:
            REQUEST.RESPONSE.redirect('Applications')

    security.declareProtected('Use OpenFlow', 'listApplications')
    def listApplications(self):
        """ List application declaration;
            returns a list of dictionaries with keys: name, link
        """
        return map(lambda x, self=self: {'name' : x,
                                         'link' : self._applications[x]['url']},
                                         sorted(self._applications.keys()))

    ##################################################
    # IMPORT/EXPORT functions                        #
    ##################################################
    def exportToXPDL(self):
        """ Export Workflow structure to an XPDL file """
        xmldoc = None
        xpdl2of = OpenFlow2Xpdl(self, xmldoc, self)
        xml = xpdl2of.create()
        return xml

    def importFromXPDL(self, file='', REQUEST=None):
        """ Import Workflow structure from an XPDL file """
        content = file.read()
        handler = xpdlparser().parseWorkflow(content)
        if handler:
            root = handler.root

            #add processes
            for process in root.process_definitions:

                pid = RepUtils.asciiEncode(process.id)
                title = RepUtils.asciiEncode(process.name)
                description = RepUtils.asciiEncode(process.process_header.description)
                priority = RepUtils.asciiEncode(process.process_header.priority)
                begin = RepUtils.asciiEncode(process.extendedattributes.get('begin', ''))
                end = RepUtils.asciiEncode(process.extendedattributes.get('end', ''))
                try:
                    priority = int(priority)
                except:
                    priority = 0
                self.manage_addProcess(pid, title, description, None, priority, begin, end)

                #get the process object
                obj = self._getOb(pid)
                process_roles = {}

                #add activities
                for activity in process.activities:
                    aid = RepUtils.asciiEncode(activity.id)
                    title = RepUtils.asciiEncode(activity.name)
                    description = RepUtils.asciiEncode(activity.description)

                    split_mode = RepUtils.asciiEncode(activity.transition_restrictions.split.type)
                    join_mode = RepUtils.asciiEncode(activity.transition_restrictions.join.type)

                    self_assignable = RepUtils.asciiEncode(activity.extendedattributes.get('self_assignable', ''))
                    try:    self_assignable = int(self_assignable)
                    except: self_assignable = 1

                    start_mode = RepUtils.asciiEncode(activity.startmode.mode)
                    try:    start_mode = int(start_mode)
                    except: start_mode = 0

                    finish_mode = RepUtils.asciiEncode(activity.finishmode.mode)
                    try:    finish_mode = int(finish_mode)
                    except: finish_mode = 0

                    complete_automatically = RepUtils.asciiEncode(activity.extendedattributes.get('complete_automatically', ''))
                    try:    complete_automatically = int(complete_automatically)
                    except: complete_automatically = 1

                    if activity.subflow:
                        subflow = RepUtils.asciiEncode(activity.subflow.id)
                    else:
                        subflow = ''

                    parameters = []
                    if activity.tool:
                        tool = RepUtils.asciiEncode(activity.tool.id)
                        for parameter in activity.tool.actual_parameters:
                            parameters.append(parameter.strip('\n'))
                    else:
                        tool = ''

                    pullable_roles = RepUtils.asciiEncode(activity.performer).strip("\n\r\t")
                    pullable_roles = pullable_roles.split(', ')
                    push_application = RepUtils.asciiEncode(activity.extendedattributes.get('push_application',''))
                    activity_kind = RepUtils.asciiEncode(activity.extendedattributes.get('kind',''))

                    obj.addActivity(aid, split_mode.lower(), join_mode.lower(), self_assignable, start_mode, finish_mode,
                        subflow, push_application, tool, title, '', description, activity_kind, complete_automatically)

                    for role in pullable_roles:
                        if role != '':
                            if process_roles.has_key(role):
                                process_roles[role].append(aid)
                            else:
                                process_roles[role] = [aid]

                #add roles
                for process_role in process_roles.keys():
                    self.editActivitiesPullableOnRole(process_role, pid, process_roles[process_role], REQUEST=None)

                #add transitions
                for transition in process.transitions:

                    id = RepUtils.asciiEncode(transition.id)
                    from_ = RepUtils.asciiEncode(transition.from_)
                    to = RepUtils.asciiEncode(transition.to)
                    description = RepUtils.asciiEncode(transition.name)
                    condition = RepUtils.asciiEncode(transition.condition)
                    obj.addTransition(id, from_, to, condition, description)

            #add applications
            for application in root.applications:
                apid = RepUtils.asciiEncode(application.name)
                url = RepUtils.asciiEncode(application.id)
                self.addApplication(apid, url)
            message="Imported successfully"
        else:
            message="Failed to import"
        if REQUEST:
            return self.workflow_impex(self,REQUEST,manage_tabs_message=message)

    ##################################################
    # OLD IMPORT/EXPORT functions  (in XML format)   #
    ##################################################
    __roles_separator = ','

    security.declareProtected('View', 'exportToXml')
    def exportToXml(self, proc='', REQUEST=None):
        """ Export Workflow structure to an XML file
            If the 'proc' parameter is given, it takes 
        """
        export_xml = []
        export_xml_append = export_xml.append
        export_xml = []
        export_xml_append = export_xml.append
        utils_xmlEncode = RepUtils.xmlEncode
        REQUEST.RESPONSE.setHeader('content-type', 'text/xml; charset=utf-8')
        export_xml_append('<?xml version="1.0" encoding="ISO-8859-1"?>')
        export_xml_append('<workflow>\n')
        if proc:
            REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s.xml' % proc)
            proc_list = [getattr(self, proc)]
        else:
            REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=workflow.xml')
            proc_list = self.objectValues('Process')
        for process in proc_list:
            export_xml_append('<process rid="%s" title="%s" description="%s" priority="%s" begin="%s" end="%s">\n' % (utils_xmlEncode(process.id), utils_xmlEncode(process.title), utils_xmlEncode(process.description), utils_xmlEncode(process.priority), utils_xmlEncode(process.begin), utils_xmlEncode(process.end)))
            for activity in process.objectValues('Activity'):
                pushable_roles = []
                pullable_roles = []
                for pushable_role in self.getPushRoles(process.id, activity.id):
                    pushable_roles.append(pushable_role)
                pushable_roles = self.__roles_separator.join(pullable_roles)
                for pullable_role in self.getPullRoles(process.id, activity.id):
                    pullable_roles.append(pullable_role)
                pullable_roles = self.__roles_separator.join(pullable_roles)
                export_xml_append("""<activity rid='%s' title='%s'
                split_mode='%s' join_mode='%s' self_assignable='%s'
                start_mode='%s' finish_mode='%s' complete_automatically='%s'
                subflow='%s' push_application='%s' application='%s'
                parameters='%s' description='%s' kind='%s'
                pushable_roles='%s' pullable_roles='%s'/>\n""" % 
               (utils_xmlEncode(activity.id), utils_xmlEncode(activity.title), utils_xmlEncode(activity.split_mode),
                utils_xmlEncode(activity.join_mode), utils_xmlEncode(activity.self_assignable), utils_xmlEncode(activity.start_mode),
                utils_xmlEncode(activity.finish_mode), utils_xmlEncode(activity.complete_automatically),
                utils_xmlEncode(activity.subflow), utils_xmlEncode(activity.push_application),
                utils_xmlEncode(activity.application), utils_xmlEncode(activity.parameters),
                utils_xmlEncode(activity.description), utils_xmlEncode(activity.kind),
                utils_xmlEncode(pushable_roles), utils_xmlEncode(pullable_roles)))
            for transition in process.objectValues('Transition'):
                export_xml_append('<transition rid="%s" From="%s" To="%s" condition="%s" description="%s"/>\n' % (utils_xmlEncode(transition.id), utils_xmlEncode(transition.From), utils_xmlEncode(transition.To), utils_xmlEncode(transition.condition), utils_xmlEncode(transition.description)))
            export_xml_append('</process>\n')
        for application in self._applications.keys():
            application_url = self._applications[application]['url']
            export_xml_append('<application rid="%s" url="%s"/>\n' % (utils_xmlEncode(application), utils_xmlEncode(application_url)))
        export_xml_append('</workflow>\n')
        return ''.join(export_xml)

    def _importFromXml(self, p_xml_string):
        """ Import Workflow structure from an XML """
        import xpdlparser
        l_workflowhandler = xpdlparser.sxpdlparser().ParseWorkflow(p_xml_string)
        if l_workflowhandler:
            #add process
            for l_process in l_workflowhandler.processes:
                l_process_id = RepUtils.asciiEncode(l_process['rid'])
                l_process_title = RepUtils.asciiEncode(l_process['title'])
                l_process_description = RepUtils.asciiEncode(l_process['description'])
                l_process_priority = RepUtils.asciiEncode(l_process['priority'])
                try:
                    l_process_priority = int(l_process_priority)
                except:
                    l_process_priority = 0
                l_process_begin = RepUtils.asciiEncode(l_process['begin'])
                l_process_end = RepUtils.asciiEncode(l_process['end'])
                self.manage_addProcess(l_process_id, l_process_title, l_process_description, None,
                    l_process_priority, l_process_begin, l_process_end)
                l_process_obj = self._getOb(l_process_id)
                l_process_pushable_roles = {}
                l_process_pullable_roles = {}
                #add activities
                for l_activity in l_process['activities']:
                    l_activity_id = RepUtils.asciiEncode(l_activity['rid'])
                    l_activity_split_mode = RepUtils.asciiEncode(l_activity['split_mode'])
                    l_activity_join_mode = RepUtils.asciiEncode(l_activity['join_mode'])
                    l_activity_self_assignable = RepUtils.asciiEncode(l_activity['self_assignable'])
                    try:
                        l_activity_self_assignable = int(l_activity_self_assignable)
                    except:
                        l_activity_self_assignable = 1
                    l_activity_start_mode = RepUtils.asciiEncode(l_activity['start_mode'])
                    try:
                        l_activity_start_mode = int(l_activity_start_mode)
                    except:
                        l_activity_start_mode = 0
                    l_activity_finish_mode = RepUtils.asciiEncode(l_activity['finish_mode'])
                    try:
                        l_activity_finish_mode = int(l_activity_finish_mode)
                    except:
                        l_activity_finish_mode = 1
                    l_activity_complete_automatically = RepUtils.asciiEncode(l_activity['complete_automatically'])
                    try:
                        l_activity_complete_automatically = int(l_activity_complete_automatically)
                    except:
                        l_activity_complete_automatically = 1
                    l_activity_subflow = RepUtils.asciiEncode(l_activity['subflow'])
                    l_activity_push_application = RepUtils.asciiEncode(l_activity['push_application'])
                    l_activity_application = RepUtils.asciiEncode(l_activity['application'])
                    l_activity_title = RepUtils.asciiEncode(l_activity['title'])
                    l_activity_parameters = RepUtils.asciiEncode(l_activity['parameters'])
                    l_activity_description = RepUtils.asciiEncode(l_activity['description'])
                    l_activity_kind = RepUtils.asciiEncode(l_activity['kind'])
                    l_activity_pushable_roles = RepUtils.asciiEncode(l_activity['pushable_roles']).split(self.__roles_separator)
                    l_activity_pullable_roles = RepUtils.asciiEncode(l_activity['pullable_roles']).split(self.__roles_separator)
                    l_process_obj.addActivity(l_activity_id, l_activity_split_mode, l_activity_join_mode,
                        l_activity_self_assignable, l_activity_start_mode, l_activity_finish_mode,
                        l_activity_subflow, l_activity_push_application, l_activity_application,
                        l_activity_title, l_activity_parameters, l_activity_description, l_activity_kind,
                        l_activity_complete_automatically)
                    for l_activity_pushable_role in l_activity_pushable_roles:
                        if l_activity_pushable_role != '':
                            if l_process_pushable_roles.has_key(l_activity_pushable_role):
                                l_process_pushable_roles[l_activity_pushable_role].append(l_activity_id)
                            else:
                                l_process_pushable_roles[l_activity_pushable_role] = [l_activity_id]
                    for l_activity_pullable_role in l_activity_pullable_roles:
                        if l_activity_pullable_role != '':
                            if l_process_pullable_roles.has_key(l_activity_pullable_role):
                                l_process_pullable_roles[l_activity_pullable_role].append(l_activity_id)
                            else:
                                l_process_pullable_roles[l_activity_pullable_role] = [l_activity_id]
                #add roles
                for l_process_pushable_role in l_process_pushable_roles.keys():
                    self.editActivitiesPushableOnRole(l_process_pushable_role, l_process_id, l_process_pushable_roles[l_process_pushable_role], REQUEST=None)
                for l_process_pullable_role in l_process_pullable_roles.keys():
                    self.editActivitiesPullableOnRole(l_process_pullable_role, l_process_id, l_process_pullable_roles[l_process_pullable_role], REQUEST=None)
                #add transitions
                for l_transition in l_process['transitions']:
                    l_transition_id = RepUtils.asciiEncode(l_transition['rid'])
                    l_transition_From = RepUtils.asciiEncode(l_transition['From'])
                    l_transition_To = RepUtils.asciiEncode(l_transition['To'])
                    l_transition_condition = RepUtils.asciiEncode(l_transition['condition'])
                    l_transition_description = RepUtils.asciiEncode(l_transition['description'])
                    l_process_obj.addTransition(l_transition_id, l_transition_From, l_transition_To,
                        l_transition_condition, l_transition_description)
            #applications
            for l_application in l_workflowhandler.applications:
                l_application_id = RepUtils.asciiEncode(l_application['rid'])
                l_application_url = RepUtils.asciiEncode(l_application['url'])
                self.addApplication(l_application_id, l_application_url)
            return 1
        else:
            return 0

    security.declareProtected('Manage OpenFlow', 'importFromXml')
    def importFromXml(self, file, REQUEST=None):
        """ Imports the contained objects from XML """
        res = self._importFromXml(file.read())
        if REQUEST:
            if res: message="Imported successfully"
            else: message="Failed to import"
            return self.workflow_impex(self,REQUEST,manage_tabs_message=message)

    security.declareProtected('Manage OpenFlow', 'workflow_impex')
    workflow_impex = PageTemplateFile('zpt/Workflow/workflowImpEx', globals())

    ##################################################
    # Processes mappings
    ##################################################

    security.declarePublic('getProcessMappings')
    def getProcessMappings(self):
        """ returns a dictionary with the valid process mappings 
            remembers mappings for erased processes - you never know when it's useful
            A newly added process is not valid for any dataflow or country
        """
        l_all_processes = self.objectIds('Process')
        l_return_dict = self.process_mappings
        for l_process_id in l_all_processes:
            # add new processes
            if l_process_id not in self.process_mappings.keys():
                self.process_mappings[l_process_id] = {'dataflows':[], 'countries':[]}
                l_return_dict[l_process_id] = {'dataflows':[], 'countries':[]}
            else:
                l_return_dict[l_process_id] = self.process_mappings[l_process_id]
        return l_return_dict

    security.declareProtected('Manage OpenFlow', 'setProcessMappings')
    def setProcessMappings(self, p_process, p_dataflows_all, p_countries_all, p_dataflows=None, p_countries=None, REQUEST=None):
        """ sets a process mappings according to the REQUEST """
        l_ret_dict = {'dataflows':[], 'countries':[]}
        if p_dataflows_all == '1':
            l_ret_dict['dataflows'] = ['*']
        else:
            l_ret_dict['dataflows'] = RepUtils.utConvertToList(p_dataflows)
        if p_countries_all == '1':
            l_ret_dict['countries'] = ['*']
        else:
            l_ret_dict['countries'] = RepUtils.utConvertToList(p_countries)
        self.process_mappings[p_process] = l_ret_dict
        self._p_changed = 1
        if REQUEST:
            message="Properties changed"
            return self.workflow_map_processes(self,REQUEST,manage_tabs_message=message)

    security.declarePublic('findProcess')
    def findProcess(self, dataflow_uris, country_code):
        """ Finds the process suited for an envelope and retrieves its absolute_url
            If there's no process or more than one, an error code and the description are returned
            Look by the same dataflow uris and country code
        """
        l_result = {}
        for l_process_id, l_value in self.getProcessMappings().items():
            for l_dataflow in dataflow_uris:
                # both dataflows and countries are chosen explicitly
                if RepUtils.utIsSubsetOf(l_dataflow, l_value['dataflows']) and RepUtils.utIsSubsetOf(country_code, l_value['countries']):
                    l_result[self._getOb(l_process_id).absolute_url(1)] = 2
                # one of dataflows or countries explicitly chosen, the other is generic
                elif (l_value['dataflows'] == ['*'] or RepUtils.utIsSubsetOf(l_dataflow, l_value['dataflows'])) and (l_value['countries'] == ['*'] or RepUtils.utIsSubsetOf(country_code, l_value['countries'])) and not (l_value['dataflows'] == ['*'] and l_value['countries'] == ['*']):
                    l_purl = self._getOb(l_process_id).absolute_url(1)
                    l_result[l_purl] = max(l_result.get(l_purl, 1), 1)
                # generic process both for dataflows and countries
                elif l_value['dataflows'] == ['*'] and l_value['countries'] == ['*']:
                    l_purl = self._getOb(l_process_id).absolute_url(1)
                    l_result[l_purl] = max(l_result.get(l_purl, 0), 0)
        # l_result now has the list of all suitable processes
        l_keys = l_result.keys()
        if len(l_keys) == 1:
            return (0, l_result.keys()[0])
        elif len(l_keys) == 0:
            return (1, (NoProcessAvailable, 'No process associated with this envelope'))
        else:
            # further filter the processes by scores and return the one with the high score
            # or an error if there are more than one with the highest score
            l_highest_score = max(l_result.values())
            l_best_fits = [x[0] for x in l_result.items() if x[1] == l_highest_score]
            if len(l_best_fits) > 1:
                return (1, (CannotPickProcess, 'More than one process associated with this envelope'))
            else:
                return (0, l_best_fits[0])

    security.declarePublic('getDataflows')
    def getDataflows(self):
        """ dataflow_table is acquired from root of ZODB and is
            currently a python script """
        return self.dataflow_table()

    security.declarePublic('getCountries')
    def getCountries(self):
        """ countries table is aquired from root of ZODB 
        """
        return self.localities_table()


    security.declareProtected('Manage OpenFlow', 'workflow_map_processes')
    workflow_map_processes =  DTMLFile('dtml/Workflow/workflowMapProcesses', globals())

    security.declareProtected('Manage OpenFlow', 'workflow_map_process')
    workflow_map_process =  DTMLFile('dtml/Workflow/workflowMapProcess', globals())


    security.declarePublic('getApplicationToActivitiesMapping')
    def getApplicationToActivitiesMapping(self):
        out = defaultdict(list)
        for process in self.objectValues(['Process']):
            for activity in process.objectValues(['Activity']):
                if activity.kind == 'standard':
                    out[activity.application].append(activity)
        return dict(out)

InitializeClass(OpenFlowEngine)

def handle_application_move_events(obj):
    """
    Reportek has a folder to store all the applications for the activities.

    An application path has this pattern:
     ``/<apps_folder>/<proc_id>/<app_id>``

    Let's say we have an application with this path:
     ``/Applications/wise_soe/Draft``

    In order to be able to map activities to applications, when renaming an application, the new name must pass a validation mechanism.

    - First, the process id is identified by looking at the application path ``(wise_soe)``
    - A list with all the ids of activities for that process is pulled from WorkflowEngine
    - In order to be valid, the new name of the application must match one of the ids in the list
    """
    expr = re.compile('^/(%s)/(.*)(?:/(.*))$' %constants.APPLICATIONS_FOLDER_ID)
    try:
        # warning obj.object.absolute_url_path() is the new path
        result = expr.match(obj.object.absolute_url_path())
    except TypeError as exp:
        result = None
    if result:
        (folder, proc_id, app_id) = result.groups()
        root = obj.object.getPhysicalRoot()
        wf = getattr(root, constants.WORKFLOW_ENGINE_ID)
        proc_new = None
        if getattr(obj.newParent, 'id', None) in wf.keys():
            # this is the target process folder when creating, renaming or moving.
            # valid ids are taken from the target folder in these cases
            proc_new = wf.get(obj.newParent.id)
        elif getattr(obj.oldParent, 'id', None) in wf.keys():
            # we don't have a target process folder when deleting
            # se we take valid ids from oldParent to show a warning when
            # deleting an application with a valid id
            proc_new = wf.get(obj.oldParent.id)
        proc_old = wf.get(getattr(obj.oldParent, 'id', None))
        if proc_new:
            valid_ids = proc_new.listActivities()
            if not obj.newName in valid_ids:
                if not obj.newName and app_id in valid_ids:
                    # VALID ID DELETION
                    # getting here means we are deleting a previously mapped
                    # application, leaving an activity unmapped
                    # that's ok, but display a message
                    message = 'Application %s deleted! Activity %s' \
                              ' has no application mapped by path now.' %(
                                      obj.object.absolute_url_path(),
                                      proc_new.get(app_id).absolute_url_path())
                    root.REQUEST['manage_tabs_message'] =  message
                elif not obj.newName:
                    # INVALID ID DELETION
                    # getting here means we are deleting an application that's
                    # not mapped to any activity
                    # that's ok, but display a message
                    message = 'Application %s deleted! '\
                              'It was not mapped by path to any activity' %(
                                obj.object.absolute_url_path())
                    root.REQUEST['manage_tabs_message'] =  message
                else:
                    # getting here means one of the following:

                    # 1) we are creating an application with an invalid id

                    # or

                    # 2) we are moving from one process folder to another process folder
                    # and the app id is not valid in the context of the new
                    # process folder

                    # or

                    # 3) we are renaming an application but the new id does not
                    # match an activity id

                    message = 'Id %s does not match any activity name in process %s. ' \
                              'Choose a valid name from this list: %s' %(app_id, proc_new.absolute_url_path(), ', '.join(valid_ids))
                    root.REQUEST['manage_tabs_message'] =  message

            elif obj.oldParent and obj.newParent and not (obj.oldParent == obj.newParent):
                # getting here means we are moving an application from one
                # folder to a process folder and the app id
                # matches an application id in the new process
                old_path = '/'.join([
                                obj.oldParent.absolute_url_path(),
                                obj.oldName])
                if expr.match(old_path):
                    # comming from another process
                    message = 'Application %s mapped by path to activity %s. '\
                              'Activity %s has no application mapped by path now.'%(
                                    obj.newName,
                                    proc_new.get(obj.newName).absolute_url_path(),
                                    proc_old.get(obj.oldName).absolute_url_path(),
                              )
                    root.REQUEST['manage_tabs_message'] =  message
                else:
                    # comming from somewhere else
                    message = 'Application %s mapped by path to activity %s. '\
                              %(
                                    obj.newName,
                                    proc_new.get(obj.newName).absolute_url_path(),
                              )
                    root.REQUEST['manage_tabs_message'] =  message

            else:
                message = 'Application %s mapped by path to activity %s.'%(
                                app_id, proc_new.get(app_id).absolute_url_path())
                root.REQUEST['manage_tabs_message'] =  message
    elif obj.oldParent:
        expr = re.compile('^/(%s)/(.*)$' %constants.APPLICATIONS_FOLDER_ID)
        result = expr.match(obj.oldParent.absolute_url_path())
        if result:
            (host_folder, proc_id) = result.groups()
            root = obj.object.getPhysicalRoot()
            wf = getattr(root, constants.WORKFLOW_ENGINE_ID)
            proc_new = wf.get(proc_id)
            if proc_new:
                valid_ids = proc_new.listActivities()
                if obj.oldName in valid_ids:
                    message = 'Application %s moved! Activity %s' \
                              ' has no application mapped by path now.' %(
                                      '/'.join([
                                          obj.oldParent.absolute_url_path(),
                                          obj.oldName]),
                                      proc_new.get(obj.oldName).absolute_url_path())
                    root.REQUEST['manage_tabs_message'] =  message
                else:
                    message = 'Application %s moved! It was not mapped by path to any activity.' %(
                                      '/'.join([
                                          obj.oldParent.absolute_url_path(),
                                          obj.oldName]))
                    root.REQUEST['manage_tabs_message'] =  message
