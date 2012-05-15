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


""" EnvelopeInstance class

This class is part of the workflow system

"""

# Zope imports
from AccessControl import getSecurityManager, ClassSecurityInfo
from Globals import InitializeClass, DTMLFile, MessageDialog
from OFS.Folder import Folder
from Products.ZCatalog.CatalogPathAwareness import CatalogAware
from time import time
from DateTime import DateTime
import string

# Product specific imports
from expression import exprNamespace
try:
    # do you have CMF?
    # if so use its Expression class
    from Products.CMFCore.Expression import Expression
except:
    # I guess you have no CMF...
    # here's a what you need:
    from expression import Expression
import RepUtils
from constants import WORKFLOW_ENGINE_ID, WEBQ_XML_REPOSITORY, CONVERTERS_ID
from workitem import workitem


class EnvelopeInstance(CatalogAware, Folder):
    """ The Envelope class subclasses from EnvelopeInstance which implements the workflow operations
        Each envelope follows a certain workflow process established at creation time.
    """

    security = ClassSecurityInfo()

    manage_options=( {'label': 'History', 'action' : 'history_section'},
                    {'label': 'Workflow', 'action' : 'manage_history_html'} )

    def __init__(self, process, priority=0):
        """ constructor """
        self.creation_time = DateTime()
        self.priority = priority
        self.process_path = process.absolute_url(1)
        self.begin_activity_id = process.begin
        self.status = 'initiated'   # initiated,running,active,complete,terminated,suspended
        self.old_status = ''        #Used to remeber the status after a suspension
        #logging structure
        # each event has the form {'start':xxx, 'end':yyy, 'comment':zzz, 'actor':aaa}
        #'start' and 'end' are time in msec, 'actor' and 'comment' are string
        self.initiation_log = [] #1 log
        self.running_log = []
        self.activation_log = []
        self.completion_log = [] #1 log
        #statistic data in msec
        self.initiation_time = 0
        self.running_time = 0
        self.active_time = 0
        #log initialization
        self.initiation_log.append({'start':time(),'end':None,'comment':'creation','actor':''})

    # History of the envelope for administrators
    security.declareProtected('Manage OpenFlow', 'manage_history_html')
    manage_history_html = DTMLFile('dtml/Workflow/envelopeManageHistory', globals())

    # History of the envelope for all users
    security.declareProtected('View', 'history_section')
    history_section = DTMLFile('dtml/Workflow/envelopeHistory', globals())

    security.declareProtected('Manage OpenFlow', 'chooseFallin')
    chooseFallin = DTMLFile('dtml/Workflow/envelopeChooseFallin', globals())

    security.declarePublic('activity_operations')
    activity_operations = DTMLFile('dtml/envelopeActivityOperations', globals())

    def getWorkflowTabs(self, REQUEST):
        """ Returns the tuple:
            (tabs available for the current user with respect to the active workitems, the selected tab)
        """
        l_current_actor = REQUEST.AUTHENTICATED_USER.getUserName()
        l_return = []
        for w in self.objectValues('Workitem'):
            if w.status == 'active' and (w.actor == l_current_actor):
                l_application_url = self.getApplicationUrl(w.id)
                if l_application_url:
                    l_return.append([w.id, l_application_url, self.unrestrictedTraverse(l_application_url).title_or_id()])
        return l_return

    ###########################################
    #   Methods to get the environment objects
    ###########################################

    def getOpenFlowEngine(self):
        """ Returns the Collection object, parent of the process """
        process = self.unrestrictedTraverse(self.process_path)
        return process.aq_parent

    def getActivity(self, workitem_id):
        """ Returns the activity of a workitem """
        workitem = getattr(self, workitem_id)
        activity_id = workitem.activity_id
        process = self.unrestrictedTraverse(self.process_path)
        return getattr(process, activity_id)

    security.declareProtected('Use OpenFlow', 'getApplicationUrl')
    def getApplicationUrl(self, workitem_id):
        """ Return application definition URL relative to instance and workitem """
        activity = self.getActivity(workitem_id)
        application = activity.application
        engine = self.getOpenFlowEngine()
        if application in engine._applications.keys():
            return engine._applications[application]['url']
        else:
            return ""

    def getEnvironment(self, workitem_id):
        """ Returns the engine, the workitem object, the current process and activity """
        workitem = getattr(self, workitem_id)
        activity_id = workitem.activity_id
        wfengine = self.getOpenFlowEngine()
        process = getattr(wfengine, self.process_path.split('/')[-1])
        activity = getattr(process, activity_id)
        return wfengine, workitem, process, activity

    def getInstanceProcessId(self):
        """ Returns the process id from its path """
        return self.process_path.split('/')[-1]

    def getProcess(self):
        """ Returns the process as an object"""
        return self.unrestrictedTraverse(self.process_path)

    ###########################################
    #   Workitems
    ###########################################

    def addWorkitem(self, activity_id, blocked, push_roles=[], pull_roles=[]):
        w_id = str(len(self.objectValues('Workitem')))
        w = workitem(w_id, self.id, activity_id, blocked,
                     push_roles=push_roles, pull_roles=pull_roles)
        self._setObject(str(w.id), w)
        w.addEvent('creation')
        return w

    def getJoiningWorkitem(self, activity_id):
        w_list = filter (lambda x, pi=self.process_path, ai=activity_id : \
                         (x.status=='blocked') and \
                         (x.process_path==pi) and \
                         (x.activity_id==ai),
                         self.objectValues('Workitem'))
        if w_list:
            return w_list[0]
        else:
            return None

    def setStatus(self, status, comment='', actor=''):
        """ """
        old_status = self.status
        new_status = status
        now = time()

        if old_status == 'initiated':
            self.initiation_log[-1]['end'] = now
            self.initiation_time += now - self.initiation_log[-1]['start']
            if new_status == 'running':
                self.running_log.append({'start':now,'end':None,'comment':comment,'actor':actor})

        if old_status == 'running':
            self.running_log[-1]['end'] = now
            self.running_time += now - self.running_log[-1]['start']
            if new_status == 'active':
                self.activation_log.append({'start':now,'end':None,'comment':comment,'actor':actor})
            if new_status == 'complete':
                self.completion_log.append({'start':now,'end':None,'comment':comment,'actor':actor})

        if old_status == 'active':
            self.activation_log[-1]['end'] = now
            self.active_time += now - self.activation_log[-1]['start']
            if new_status == 'running':
                self.running_log.append({'start':now,'end':None,'comment':comment,'actor':actor})

        self.status = status
        self.reindex_object()

    security.declareProtected('View','is_active_for_me')
    def is_active_for_me(self,REQUEST=None):
        """ returns >0 if there is an active workitem for that person"""
        if REQUEST:
            actor=REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor=''
        for item in self.objectValues('Workitem'):
            if item.status == 'active' \
              and (item.actor == actor or item.actor == ''):
                return 1
        return 0

    security.declareProtected('Use OpenFlow', 'getActiveWorkitems')
    def getActiveWorkitems(self):
        """ returns all active workitems """
        return len(filter (lambda x: x.status == 'active', self.objectValues('Workitem')))

    security.declareProtected('View', 'getListOfWorkitems')
    def getListOfWorkitems(self,status=None):
        """ Returns all workitems given a list of statuses
            If the status is not provided, all workitems are returned
        """
        if status is None:
            return self.objectValues('Workitem')
        else:
            if type(status) == type([]):
                return [x for x in self.objectValues('Workitem') if x.status in status]
            else:
                return [x for x in self.objectValues('Workitem') if x.status == status]

    def setPriority(self, value):
        self.priority = value
        self.reindex_object()

    def isActiveOrRunning(self):
        return self.status in ('active', 'running')

    security.declareProtected('Manage OpenFlow', 'suspendInstance')
    def suspendInstance(self, REQUEST=None):
        """ suspend a specified instance """
        if self.isActiveOrRunning() or self.status == 'initiated':
            if REQUEST:
                actor=REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                actor=''
            self.old_status = self.status
            self.setStatus(status='suspended', actor=actor)
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Manage OpenFlow', 'resumeInstance')
    def resumeInstance(self, REQUEST=None):
        """ resume a specified instance """
        if self.status == 'suspended':
            if REQUEST:
                actor=REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                actor=''
            self.setStatus(status=self.old_status, actor=actor)
            self.old_status = ''
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Manage OpenFlow', 'terminateInstance')
    def terminateInstance(self, REQUEST=None):
        """ terminate a specified instance """
        if self.status != 'complete':
            if REQUEST:
                actor=REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                actor=''
            self.setStatus(status='terminated', actor=actor)
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Use OpenFlow', 'startInstance')
    def startInstance(self, REQUEST=None):
        """ Starts the flowing of the process instance inside the process definition """
        if REQUEST:
            actor=REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor=''
        self.setStatus(status='running', actor=actor)
        activity_id = self.begin_activity_id
        engine = self.getOpenFlowEngine()
        push_roles = engine.getPushRoles(self.getInstanceProcessId(), activity_id)
        pull_roles = engine.getPullRoles(self.getInstanceProcessId(), activity_id)
        w = self.addWorkitem(activity_id, 0, push_roles, pull_roles)
        self.manageWorkitemCreation(w.id)
        if REQUEST and REQUEST.has_key('DestinationURL'):
            REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])

    def linkWorkitems(self, workitem_from_id, workitem_to_id_list):
        workitem_from = getattr(self, workitem_from_id)
        workitem_from.addTo(workitem_to_id_list)
        for w_id in workitem_to_id_list:
            w = getattr(self, w_id)
            w.addFrom(workitem_from_id)
            w.setGraphLevel(workitem_from.graph_level + 1)

    security.declareProtected('Use OpenFlow', 'assignWorkitem')
    def assignWorkitem(self, workitem_id, actor, REQUEST=None):
        """ Assign the specified workitem of the specified instance to the specified actor (string)"""
        workitem = getattr(self, workitem_id)
        user_is_ok = (REQUEST==None or
                      [r for r in REQUEST.AUTHENTICATED_USER.getRoles() if r in workitem.push_roles] or \
                      ([r for r in REQUEST.AUTHENTICATED_USER.getRoles() if r in workitem.pull_roles] and activity.isSelfAssignable()))
        workitem_is_ok = self.isActiveOrRunning() and not workitem.status == 'completed' and workitem.actor == ''
        if user_is_ok and workitem_is_ok:
                workitem.assignTo(actor)
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Use OpenFlow', 'unassignWorkitem')
    def unassignWorkitem(self, workitem_id, REQUEST=None):
        """ Unassign the specified workitem """
        workitem = getattr(self, str(workitem_id))
        if self.isActiveOrRunning() and workitem.status != 'completed':
            getattr(self, workitem_id).assignTo('')
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

# FIXME: In Openflow, the actor is not set when you activate the item,
# unless you have given it as an argument. This seems strange given
# that activateWorkitem (at least for Reportek) serves to 'reserve' the
# workitem to a specific worker.
    security.declareProtected('Use OpenFlow', 'activateWorkitem')
    def activateWorkitem(self, workitem_id, actor=None, REQUEST=None):
        """ declares the activation of the specified workitem of the given instance """
        workitem = getattr(self, str(workitem_id))
        if actor:
            action_actor = actor
        else:
            if REQUEST: action_actor=REQUEST.AUTHENTICATED_USER.getUserName()
            else: action_actor=''
        if self.isActiveOrRunning() and workitem.status == 'inactive' and not workitem.blocked:
            if workitem.actor == '':
                if actor is not None:
                    self.assignWorkitem(workitem_id, actor)
                elif action_actor != '':
                    self.assignWorkitem(workitem_id, action_actor)
            workitem.setStatus('active', actor=action_actor)
            self.setStatus(status='active', actor=action_actor)
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Use OpenFlow', 'inactivateWorkitem')
    def inactivateWorkitem(self, workitem_id, REQUEST=None):
        """ declares the inactivation of the specified workitem of the given instance """
        workitem = getattr(self, str(workitem_id))
        actor=''  # We don't need any actor name
        if self.isActiveOrRunning() and workitem.status == 'active' and not workitem.blocked:
            workitem.setStatus('inactive', actor=actor)
            if self.getActiveWorkitems() == 0:
                self.setStatus(status='running', actor=actor)
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Use OpenFlow', 'suspendWorkitem')
    def suspendWorkitem(self, workitem_id, REQUEST=None):
        """ declares the suspension of the specified workitem of the given instance """
        workitem = getattr(self, str(workitem_id))
        if REQUEST:
            actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor = ''
        if self.isActiveOrRunning() and \
               workitem.status == 'inactive' and \
               not workitem.blocked:
            workitem.setStatus('suspended', actor=actor)
            if self.getActiveWorkitems() == 0:
                self.setStatus(status='running', actor=actor)
        if REQUEST:
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Use OpenFlow', 'resumeWorkitem')
    def resumeWorkitem(self, workitem_id, REQUEST=None):
        """ declares the resumption of the specified workitem of the given instance """
        workitem = getattr(self, str(workitem_id))
        if REQUEST:
            actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor = ''
        if self.isActiveOrRunning() and \
               workitem.status == 'suspended' and \
               not workitem.blocked:
            workitem.setStatus('inactive', actor=actor)
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Use OpenFlow', 'completeWorkitem')
    def completeWorkitem(self, workitem_id, actor=None, REQUEST=None):
        """ declares the completion of the specified workitem of the given instance """
        if REQUEST:
            if REQUEST.has_key('actor'):
                actor = REQUEST['actor']
            else:
                actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            l_actor = 'openflow_engine'
        if actor:
            l_actor = actor
        workitem = getattr(self, workitem_id)
        activity = self.getActivity(workitem_id)
        process = self.unrestrictedTraverse(self.process_path)
        if self.isActiveOrRunning():
            workitem_return_id = None
            if workitem.status in ('active', 'fallout'):
                workitem.setStatus('complete', actor=l_actor)
                if self.getActiveWorkitems() == 0:
                    self.setStatus(status='running', actor=l_actor)
                if self.isEnd(workitem.activity_id):
                    subflow_workitem_id = self.getSubflowWorkitem(workitem_id)
                    if subflow_workitem_id != None:
                        self.completeSubflow(subflow_workitem_id)
                    else:
                        self.setStatus(status='complete', actor=l_actor)
            if activity.isAutoFinish() and not process.end == activity.id and not activity.isSubflow():
                self.forwardWorkitem(workitem_id)
            if REQUEST:
                if REQUEST.has_key('DestinationURL'):
                    REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
                else:
                    REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    def isEnd(self, activity_id):
        """  """
        process = self.restrictedTraverse(self.process_path)
        return process.end == activity_id

    security.declareProtected('Use OpenFlow', 'getNextTransitions')
    def getNextTransitions(self, workitem_id):
        """ Returns the list of transition that the given workitem (of the specified instance)
        will be routed on"""
        process = self.unrestrictedTraverse(self.process_path)
        activity = self.getActivity(workitem_id)
        engine = self.getOpenFlowEngine()
        workitem = getattr(self, workitem_id)
        transition_list = []
        split_mode = activity.split_mode
        transition_condition_list = [{'transition_id' : x.id, 'condition' : x.condition} \
                                     for x in process.objectValues('Transition') \
                                     if x.From==activity.id and hasattr(process, x.To)]
        if len(transition_condition_list) == 1:
            transition_list = [transition_condition_list[0]['transition_id']]
        else:
            if split_mode == 'and':
                transition_list = map(lambda x : x['transition_id'], transition_condition_list)
            elif split_mode == 'xor':
                for r in [c for c in transition_condition_list if c['condition']]:
                    expr=Expression(r['condition'])
                    ec=exprNamespace(instance=self,
                                     workitem=workitem,
                                     process=process,
                                     activity=activity,
                                     openflow=engine)
                    if expr(ec):
                        transition_list = [r['transition_id']]
                        break
        return transition_list

    # Test on path type was not in Openflow
    def getDestinations(self, workitem_id, path=None):
        if path:
            transition_list = [path]
        else:
            transition_list = self.getNextTransitions(workitem_id)
        destinations = []
        process = self.unrestrictedTraverse(self.process_path)
        for transition_id in transition_list:
            activity_to_id = getattr(process, transition_id).To
            activity_to = getattr(process, activity_to_id)
            if getattr(process, activity_to_id).join_mode=='and':
                blocked_init = activity_to.getIncomingTransitionsNumber() - 1
            else:
                blocked_init = 0

            destinations.append({'activity_to_id' : activity_to_id,
                                 'blocked_init' : blocked_init,
                                 'process_to_id' : process.id})
        return destinations

    security.declareProtected('Use OpenFlow', 'forwardWorkitem')
    def forwardWorkitem(self, workitem_id, path=None, REQUEST=None):
        """ instructs openflow to forward the specified workitem """
        destinations = self.getDestinations(workitem_id, path)
        if destinations == []:
            self.falloutWorkitem(workitem_id)
        else:
            workitem = getattr(self, workitem_id)
            engine = self.getOpenFlowEngine()
            activity = self.getActivity(workitem_id)
            new_workitems = []
            if self.isActiveOrRunning() and \
                   (workitem.status == 'complete' and \
                   (not workitem.workitems_to or activity.isSubflow())):
                activity_to_id_list = map(lambda x : x['activity_to_id'], destinations)
                workitem.addEvent('forwarded to '+ reduce(lambda x, y : x+', '+y, activity_to_id_list))
                workitem_to_id_list = []
                for d in destinations:
                    w = self.getJoiningWorkitem(d['activity_to_id'])
                    if w:
                        w.unblock()
                        workitem_to_id_list.append(w.id)
                    else:
                        activity_id = d['activity_to_id']
                        push_roles = engine.getPushRoles(self.getInstanceProcessId(), activity_id)
                        pull_roles = engine.getPullRoles(self.getInstanceProcessId(), activity_id)
                        w = self.addWorkitem(activity_id,
                                            d['blocked_init'],
                                            push_roles,
                                            pull_roles)
                        workitem_to_id_list.append(w.id)
                    if w.blocked == 0:
                        new_workitems.append(w.id)
                        w.addEvent('arrival from ' + workitem.activity_id)
                self.linkWorkitems(workitem_id, workitem_to_id_list)
            for w in new_workitems:
                self.manageWorkitemCreation(w)
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('View', 'getPreviousActor')
    def getPreviousActor(self, workitem_id):
        """ Returns the actor that completed the previous workitem """
        if workitem_id: 
            l_w = getattr(self, str(int(workitem_id) - 1))
            return l_w.completion_log[-1]['actor']
        else:
            return ''

    security.declareProtected('Use OpenFlow', 'changeWorkitem')
    def changeWorkitem(self,
                       workitem_id,
                       push_roles = None,
                       pull_roles = None,
                       event_log = None,
                       activity_id = None,
                       blocked = None,
                       priority = None,
                       workitems_from = None,
                       workitems_to = None,
                       status = None,
                       actor = None,
                       graph_level = None,
                       REQUEST = None):
        """ use this API to modify anything of a fallout workitem
            usable only if workitem status is 'fallout' 
        """
        workitem = getattr(self, workitem_id)
        if workitem.status=='fallout':
            if push_roles != None:
                workitem.push_roles = push_roles
            if pull_roles != None:
                workitem.pull_roles = pull_roles
            if event_log != None:
                workitem.event_log = event_log
            # the workitem.edit takes care of reindexing as well
            workitem.edit(activity_id=activity_id,
                          blocked=blocked,
                          priority=priority,
                          workitems_from=workitems_from,
                          workitems_to=workitems_to,
                          status=status,
                          actor=actor,
                          graph_level=graph_level)
            workitem._p_changed = 1
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('Use OpenFlow', 'falloutWorkitem')
    def falloutWorkitem(self, workitem_id, REQUEST=None):
        """ drops the workitem in exceptional handling """
        workitem = getattr(self, workitem_id)
        if REQUEST:
            actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor = ''
        workitem.setStatus('fallout', actor=actor)
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    def sendWorkitemsToException(self, process_id, activity_id):
        for wi in self.Catalog(meta_type='Workitem',
                               process_id=process_id,
                               activity_id=activity_id,
                               status=['active', 'inactive']):
            self.falloutWorkitem(wi.id)

    security.declareProtected('Manage OpenFlow', 'fallinWorkitem')
    def fallinWorkitem(self, workitem_id, activity_id, coming_from=None, REQUEST=None):
        """ the exceptional specified workitem (of the specified instance) will be put back in the activity
        specified by process_path and activity_id; workitem will still be in exceptional state:
        use endFallinWorkitem API to specify the end of the exceptional state"""
        workitem_from = getattr(self, workitem_id)
        engine = self.getOpenFlowEngine()
        push_roles = engine.getPushRoles(self.getInstanceProcessId(), activity_id)
        pull_roles = engine.getPullRoles(self.getInstanceProcessId(), activity_id)
        workitem_to = self.addWorkitem(activity_id, 0, push_roles, pull_roles)
        self.linkWorkitems(workitem_id, [workitem_to.id])
        event = 'fallin to activity ' + activity_id + ' in process ' + self.process_path + \
                ' (workitem ' + str(workitem_to.id) + ')'
        workitem_from.addEvent(event)
        event = 'fallin from activity ' + workitem_from.activity_id + \
                ' in process ' + self.process_path + \
                ' (workitem ' + str(workitem_id) + ')'
        workitem_to.addEvent(event)
        self.manageWorkitemCreation(workitem_to.id)
        if REQUEST:
            if coming_from is not None:
                REQUEST.RESPONSE.redirect(coming_from)
            else:
                REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    security.declareProtected('Manage OpenFlow', 'endFallinWorkitem')
    def endFallinWorkitem(self, workitem_id, REQUEST=None):
        """ Ends the exceptional state of the given workitem """
        workitem = getattr(self, workitem_id)
        workitem.addEvent('handled fallout')
        if not filter(lambda x: x['event'] == 'complete', workitem.getEventLog()):
            workitem.endFallin()
        if REQUEST: 
            if REQUEST.has_key('DestinationURL'):
                REQUEST.RESPONSE.redirect(REQUEST['DestinationURL'])
            else:
                REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declarePublic('getActiveWorkitemsForMe')
    def getWorkitemsActiveForMe(self, REQUEST):
        """ Returns the list of active workitems
            where an user is the current actor of
        """
        l_actor = REQUEST.AUTHENTICATED_USER.getUserName()
        return filter (lambda x: x.status == 'active' and x.actor == l_actor, self.objectValues('Workitem'))

    ###########################################
    #   Activities and applications
    ###########################################

    security.declareProtected('Use OpenFlow', 'manageDummyActivity')
    def manageDummyActivity(self, workitem_id):
        """  """
        self.activateWorkitem(workitem_id, 'openflow_engine')
        self.completeWorkitem(workitem_id)
        if not self.isEnd(self.getInstanceProcessId(), self.getActivity().id):
            self.forwardWorkitem(workitem_id)

    security.declareProtected('Use OpenFlow', 'startAutomaticApplication')
    def startAutomaticApplication(self, workitem_id, REQUEST=None):
        """  """
        application_url = self.getApplicationUrl(workitem_id)
        activity_obj = self.getActivity(workitem_id)
        if application_url:
            if REQUEST:
                args = {'workitem_id':workitem_id, 'REQUEST':REQUEST}
            else:
                args = {'workitem_id':workitem_id, 'REQUEST':self.REQUEST}
            apply(self.restrictedTraverse(application_url), (), args)
        self.activateWorkitem(workitem_id, 'openflow_engine')
        if activity_obj.complete_automatically:
            self.completeWorkitem(workitem_id)

    security.declarePrivate('callAutoPush')
    def callAutoPush(self, workitem_id, REQUEST=None):
        """ """
        engine = self.getOpenFlowEngine()
        application_id = self.getActivity(workitem_id).push_application
        if application_id != "" and engine._applications[application_id]['url']:
            application_url = engine._applications[application_id]['url']
            args = {'workitem_id':workitem_id, 'REQUEST':REQUEST}
            # Why should the application return the actor?
            #actor = apply(self.restrictedTraverse(application_url), (), args) 
            apply(self.restrictedTraverse(application_url), (), args) 
            if REQUEST:
                actor = REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                actor = ''
            self.assignWorkitem(workitem_id, actor)

    def manageWorkitemCreation(self, workitem_id):
        """ """
        activity = self.getActivity(workitem_id)
        if self.status in ('active', 'running'):
            if activity.isDummy():
                self.manageDummyActivity(workitem_id)
            elif activity.isStandard():
                if activity.isAutoPush():
                    self.callAutoPush(workitem_id)
                if activity.isAutoStart():
                    self.startAutomaticApplication(workitem_id)
            elif activity.isSubflow():
                self.startSubflow(workitem_id)

    ###########################################
    #   Subflows - not used, not tested
    ###########################################

    security.declarePrivate('startSubflow')
    def startSubflow(self, workitem_id, REQUEST=None):
        """ """
        self.activateWorkitem(workitem_id)
        self.assignWorkitem(workitem_id, 'openflow_engine')
        subflow_id = self.getActivity(workitem_id).subflow
        engine = self.getOpenFlowEngine()
        begin_activity_id = getattr(self, subflow_id).begin
        push_roles = engine.getPushRoles(subflow_id, begin_activity_id)
        pull_roles = engine.getPullRoles(subflow_id, begin_activity_id)

        w = self.addWorkitem(begin_activity_id, 0, push_roles, pull_roles)
        self.linkWorkitems(workitem_id, [w.id])
        self.manageWorkitemCreation(w.id)

    def getSubflowWorkitem(self, workitem_id):
        """ TODO! """
        same_process_path = self.unrestrictedTraverse(self.process_path).id
        while workitem_id != []:
            engine, workitem, process, activity = self.getEnvironment(workitem_id)
            if activity.isSubflow() and (process.id != same_process_path):
                return workitem_id
            workitem_id = workitem.workitems_from and workitem.workitems_from[0]
        return None

    def completeSubflow(self, workitem_id):
        """ """
        self.completeWorkitem(workitem_id)
        process = self.unrestrictedTraverse(self.process_path)
        if not self.isEnd(process.id, self.getActivity(workitem_id).id):
            self.forwardWorkitem( workitem_id)


InitializeClass(EnvelopeInstance)
