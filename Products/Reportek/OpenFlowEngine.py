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

import json
import md5
import re
from collections import defaultdict

# Zope imports
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from Globals import InitializeClass
from OFS.Folder import Folder
from OFS.ObjectManager import checkValidId
import transaction
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek import constants
import Products
#from webdav.WriteLockInterface import WriteLockInterface

# product imports
from Toolz import Toolz
import RepUtils
import process

# custom exceptions imports
from exceptions import CannotPickProcess, NoProcessAvailable

import logging
logger = logging.getLogger("Reportek")

def manage_addOpenFlowEngine(self, id, title, REQUEST=None):
    """Add a new OpenFlowEngine object
    """
    ob = OpenFlowEngine(id, title)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class OpenFlowEngineImportError(ValueError):
    pass

class OpenFlowEngine(Folder, Toolz):
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
    manage_addApplicationForm = PageTemplateFile('zpt/Workflow/application_add', globals())

    security.declareProtected('Manage OpenFlow', 'manage_editApplicationForm')
    manage_editApplicationForm = PageTemplateFile('zpt/Workflow/application_edit', globals())

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
        if name not in self._applications:
            self._applications[name] = {'url' : link}
            self._p_changed = 1
            if REQUEST:
                REQUEST.RESPONSE.redirect('Applications')
            else:
                return True
        return False

    security.declareProtected('Manage OpenFlow', 'deleteApplication')
    def deleteApplication(self, app_ids=None, REQUEST=None):
        """ removes an application """
        for name in app_ids:
            self._applications.pop(name, None)
        self._p_changed = 1
        if REQUEST: REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    security.declareProtected('Manage OpenFlow', 'editApplication')
    def editApplication(self, name, link, REQUEST=None):
        """ edits an application declaration """
        if name not in self._applications:
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
    def _applicationDetails(self, url):
        typesWithContent = ['Script (Python)', 'DTML Method', 'DTML Document', 'Page Template']
        try:
            url = str(url)
            if not url.startswith('/'):
                url = '/' + url
            app = self.unrestrictedTraverse(url)
            app_type = app.meta_type
            if app_type in typesWithContent:
                content = app.read()
                if type(content) is unicode:
                    content = content.encode('utf-8')
                checksum = md5.md5(content).hexdigest()
            else:
                # other types will be checked based on type only
                checksum = ''
        except:
            app_type = ''
            checksum = ''

        return app_type, checksum


    security.declareProtected(view_management_screens, 'exportToJson')
    def exportToJson(self, proc='', REQUEST=None):
        """ Export Workflow structure to an .json file
            If proc parameter is missing then
            include all the processes available to this object
        """

        workflow = {
            'processes': [],
            'applications': [],
        }
        if proc:
            filename = '%s.json' % proc
            procs = [ getattr(self, proc) ]
        else:
            filename = 'workflows.json'
            procs = self.objectValues('Process')
        if REQUEST:
            REQUEST.RESPONSE.setHeader('content-type', 'application/json; charset=UTF-8')
            REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)

        applications_for_these_processes = set()
        for pr in procs:
            process = {
                'rid': pr.id,
                'title': pr.title,
                'description': pr.description,
                'priority': pr.priority,
                'begin': pr.begin,
                'end': pr.end,
                'activities': [],
                'transitions': [],
            }
            for act in pr.objectValues('Activity'):
                activity = {
                    'rid': act.id,
                    'title': act.title,
                    'description': act.description,
                    'kind': act.kind,
                    'split_mode': act.split_mode,
                    'join_mode': act.join_mode,
                    'self_assignable': act.self_assignable,
                    'start_mode': act.start_mode,
                    'finish_mode': act.finish_mode,
                    'complete_automatically': act.complete_automatically,
                    'subflow': act.subflow,
                    'push_application': act.push_application,
                    'application': act.application,
                    'parameters': act.parameters,
                    'pushable_roles': [ pushR for pushR in self.getPushRoles(pr.id, act.id) ],
                    'pullable_roles': [ pullR for pullR in self.getPullRoles(pr.id, act.id) ],
                }
                process['activities'].append(activity)
                applications_for_these_processes.add(act.application)
            for trans in pr.objectValues('Transition'):
                transition = {
                    'rid': trans.id,
                    'description': trans.description,
                    'from': trans.From,
                    'to': trans.To,
                    'condition': trans.condition,
                }
                process['transitions'].append(transition)
            workflow['processes'].append(process)

        for appName, appValue in self._applications.items():
            if appName in applications_for_these_processes:
                url = appValue['url']
                app_type, checksum = self._applicationDetails(url)
                application = {
                    'rid': appName,
                    'url': url,
                    'type': app_type,
                    'checksum': checksum,
                }
                workflow['applications'].append(application)

        return json.dumps(workflow, indent=4)

    def _importFromJson(self, json_stream):
        """Process json from input stream and aggregates the components of a workflow.
        It returns the applications part of json object with its id and url converted to ascii str.
        The caller may then compare the applications inside the iported object vs the apps already in the system.
        This function is supposed to raise exceptions if invalid data is found in the input json.
        """
        obj = json.load(json_stream)
        validRoles = self.validRoles()
        for pr in obj['processes']:
            try:
                pr_id = str(pr['rid'])
                checkValidId(self, pr_id)
            except Exception as e:
                raise OpenFlowEngineImportError('Invalid rid', pr.get('rid', None), e.args)

            self.manage_addProcess(pr_id, pr['title'], pr['description'], None,
                int(pr['priority']), pr['begin'], pr['end'])

            process = self._getOb(pr_id)
            pushRoles = defaultdict(list)
            pullRoles = defaultdict(list)
            for act in pr.get('activities', []):
                try:
                    act_id = str(act['rid'])
                    checkValidId(process, act_id)
                except:
                    raise OpenFlowEngineImportError('Invalid rid', act.get('rid', None))
                process.addActivity(act_id, act['split_mode'], act['join_mode'],
                    int(act['self_assignable']), int(act['start_mode']), int(act['finish_mode']),
                    str(act['subflow']), str(act['push_application']),
                    str(act['application']), act['title'], str(act['parameters']),
                    act['description'], str(act['kind']), int(act['complete_automatically']))
                for pushR in act['pushable_roles']:
                    if pushR:
                        pushR = str(pushR)
                        pushRoles[pushR].append(act_id)
                for pullR in act['pullable_roles']:
                    if pullR:
                        pullR = str(pullR)
                        pullRoles[pullR].append(act_id)
            for role, activities in pushRoles.items():
                if role in validRoles:
                    self.editActivitiesPushableOnRole(role, pr_id, activities)
            for role, activities in pullRoles.items():
                if role in validRoles:
                    self.editActivitiesPullableOnRole(role, pr_id, activities)
            for trans in pr.get('transitions', []):
                try:
                    trans_id = str(trans['rid'])
                    checkValidId(process, trans_id)
                except:
                    raise OpenFlowEngineImportError('Invalid rid', trans.get('rid', None))
                process.addTransition(trans_id, str(trans['from']), str(trans['to']),
                    str(trans['condition']), trans['description'])

        applications = obj.get('applications', [])
        try:
            for app in applications:
                # we also alter the returning object
                app['rid'] = str(app['rid'])
                app['url'] = str(app['url'])
                # If an app already exists on the target OpenFlowEngine it will not be overwritten
                if not self.addApplication(app['rid'], app['url']):
                    app['targetPath'] = self._applications[app['rid']]['url']
        except:
            raise OpenFlowEngineImportError('Error adding application',
                        app.get('rid', None), app.get('url', None))

        return applications


    security.declareProtected('Manage OpenFlow', 'importFromJson')
    def importFromJson(self, file, REQUEST=None):
        """ Reconstructs the workflow from a .json file """

        message="Imported successfully"
        problem_apps = []
        try:
            imported_applications = self._importFromJson(file)
            for app in imported_applications:
                # We shall compare the source path with the already existing path on target
                targetPath = app.get('targetPath', app['url'])
                existing_type, existing_checksum = self._applicationDetails(targetPath)
                if not existing_type:
                    cmp_result = 'missing'
                elif existing_type == app['type']:
                    if app['checksum'] == existing_checksum:
                        cmp_result = ''
                    else:
                        cmp_result = 'different by content'
                else:
                    cmp_result = 'different by content'

                if cmp_result:
                    app_cmp = {
                        'name': app['rid'],
                        'path': app['url'],
                        'cmp_result': cmp_result,
                    }
                    if targetPath != app['url']:
                        app_cmp['sourceName'] = app['url']
                        app_cmp['path'] = targetPath
                        app_cmp['cmp_result'] += ' and ' + 'different by path'
                    problem_apps.append(app_cmp)
                else:
                    if targetPath != app['url']:
                        app_cmp = {
                            'name': app['rid'],
                            'sourceName': app['url'],
                            'path': targetPath,
                            'cmp_result': 'different by path',
                        }
                        problem_apps.append(app_cmp)
        except OpenFlowEngineImportError as e:
            logger.error("Workflow Import/Export: Failed to import OpenFlowEngine json. Reason: %s" % unicode(e.args))
            if 'Invalid rid' in e.args[0]:
                message = u"Failed to import. Id %s is invalid or already exists." % e.args[1]
            else:
                message=u"Failed to import. Is your json file the result of Export to JSON functionality?"
            transaction.abort()
        except Exception as e:
            logger.error("Workflow Import/Export: Failed to import OpenFlowEngine json. Reason: %s" % unicode(e.args))
            message="Failed to import."
            transaction.abort()

        if problem_apps:
            msg_parts = [message, "Some of the following apps differ:"]
            for app in problem_apps:
                if 'sourceName' in app:
                    additionalPathInfo = " (path on source was: %s)" % app['sourceName']
                else:
                    additionalPathInfo = ""
                msg = "App %s with path: %s is <b>%s</b>%s" % (app['name'],
                            app['path'], app['cmp_result'], additionalPathInfo)
                msg_parts.append(msg)
                logger.warning("Workflow Import/Export: App %s with path: %s is %s%s" % (app['name'],
                            app['path'], app['cmp_result'], additionalPathInfo))
            msg_parts.append("")
            message = "\n".join(msg_parts)

        if REQUEST:
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
                # FIXME - superfluous operations here.
                # Could this hide a bug? Do we need a copy of process_mappings?!?
                # because we currently don't actually have a copy but a reference...
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
        """ dataflow_table is acquired from ReportekEngine"""
        return getattr(self, constants.ENGINE_ID).dataflow_table()

    security.declarePublic('getCountries')
    def getCountries(self):
        """ countries table is aquired from root of ZODB 
        """
        return getattr(self, constants.ENGINE_ID).localities_table()


    security.declareProtected('Manage OpenFlow', 'workflow_map_processes')
    workflow_map_processes = PageTemplateFile('zpt/Workflow/workflowMapProcesses', globals())

    security.declareProtected('Manage OpenFlow', 'workflow_map_process')
    workflow_map_process = PageTemplateFile('zpt/Workflow/workflowMapProcess', globals())

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

    old_path = ''
    new_path = ''

    if obj.oldParent:
        old_path = '/'.join([
                        obj.oldParent.absolute_url_path(),
                        obj.oldName
                   ])

    if obj.newParent:
        try:
            new_path = '/'.join([
                            obj.newParent.absolute_url_path(),
                            obj.newName
                       ])
        except TypeError:
            new_path = ''


    match_old = expr.match(old_path)
    match_new = expr.match(new_path)
    if not (match_old or match_new):
        # return early if no match
        return None

    valid_old_ids = None
    valid_new_ids = None

    root = obj.object.getPhysicalRoot()
    wf = getattr(root, constants.WORKFLOW_ENGINE_ID)
    proc_old = None
    proc_new = None
    messages = []

    if obj.oldParent:
        proc_old = wf.get(obj.oldParent.id)
        if proc_old:
            valid_old_ids = proc_old.listActivities()

    if obj.newParent:
        proc_new = wf.get(obj.newParent.id)
        if proc_new:
            valid_new_ids = proc_new.listActivities()

    if obj.oldName and obj.newName and not obj.oldParent == obj.newParent and match_old:
        messages.append(
            'Application %s moved!' %(
                obj.oldName
            )
        )
    if obj.oldName and not obj.newName:
        messages.append(
            'Application %s deleted!' %(
                obj.oldName
            )
        )
    if valid_old_ids:
        if obj.oldName not in valid_old_ids:
            messages.append(
                'Id %s was not mapped by path to any activity.'%(
                    obj.oldName
                )
            )
        else:
            messages.append(
                'Activity %s has no application mapped by path now.' %(
                    proc_old.get(obj.oldName).absolute_url_path()
                )
            )
    if valid_new_ids:
        if obj.newName in valid_new_ids:
            messages.append(
                'Application %s mapped by path to activity %s.' %(
                    obj.newName,
                    proc_new.get(obj.newName).absolute_url_path())
            )
        else:
            messages.append(
                'Id %s does not match any activity name in process %s.' %(
                    obj.newName,
                    proc_new.absolute_url_path())
            )
            messages.append(
                'Choose a valid name from this list: %s' %(
                    ', '.join(valid_new_ids))
            )
    try:
        root.REQUEST['manage_tabs_message'] =  ' '.join(messages)
    except TypeError:
        # skip, not a real REQUEST
        pass
