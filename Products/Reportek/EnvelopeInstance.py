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


"""EnvelopeInstance class

This class is part of the workflow system

"""

import json
import logging
from time import time

import plone.protect.interfaces

# Zope imports
from AccessControl import ClassSecurityInfo, getSecurityManager
from constants import ENGINE_ID
from DateTime import DateTime

# Product specific imports
from expression import exprNamespace
from Globals import InitializeClass
from OFS.Folder import Folder
from workitem import workitem
from zope.interface import alsoProvides

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.CatalogAware import CatalogAware
from Products.Reportek.constants import DEFAULT_CATALOG
from Products.Reportek.exceptions import ApplicationException
from Products.Reportek.rabbitmq import queue_msg
from Products.Reportek.RemoteRabbitMQQAApplication import (
    RemoteRabbitMQQAApplication,
)
from Products.Reportek.RepUtils import getToolByName

try:
    # do you have CMF?
    # if so use its Expression class
    from Products.CMFCore.Expression import Expression
except ImportError:
    # I guess you have no CMF...
    # here's a what you need:
    from expression import Expression
logger = logging.getLogger("Reportek")


class EnvelopeInstance(CatalogAware, Folder, object):
    """The Envelope class subclasses from EnvelopeInstance which implements
    the workflow operations
    Each envelope follows a certain workflow process established at
    creation time.
    """

    security = ClassSecurityInfo()

    manage_options = (
        {"label": "History", "action": "history_section"},
        {"label": "Workflow", "action": "manage_history_html"},
    )

    def __init__(self, process, priority=0):
        """constructor"""
        self.creation_time = DateTime()
        self.priority = priority
        self.process_path = process.absolute_url(1)
        self.begin_activity_id = process.begin
        self.status = "initiated"  # initiated,running,active,complete,...
        self.old_status = ""  # Used to remeber the status after a suspension
        # logging structure
        # each event has the form {'start':xxx, 'end':yyy,
        #                           'comment':zzz, 'actor':aaa}
        # 'start' and 'end' are time in msec, 'actor' and 'comment' are string
        self.initiation_log = []  # 1 log
        self.running_log = []
        self.activation_log = []
        self.completion_log = []  # 1 log
        # statistic data in msec
        self.initiation_time = 0
        self.running_time = 0
        self.active_time = 0
        # log initialization
        self.initiation_log.append(
            {"start": time(), "end": None, "comment": "creation", "actor": ""}
        )

    # History of the envelope for administrators
    security.declareProtected("Manage OpenFlow", "manage_history_html")
    manage_history_html = PageTemplateFile(
        "zpt/envelope/manage_history", globals()
    )

    security.declareProtected("Manage OpenFlow", "chooseFallin")
    chooseFallin = PageTemplateFile("zpt/envelope/choose_fallin", globals())

    security.declarePublic("activity_operations")
    activity_operations = PageTemplateFile(
        "zpt/envelope/operations", globals()
    )

    def getWorkflowTabs(self, REQUEST):
        """Returns the tuple:
        (tabs available for the current user with respect to the active
         workitems, the selected tab)
        """
        l_return = []
        for w in self.getWorkitemsActiveForMe(REQUEST):
            l_application_url = self.getApplicationUrl(w.id)
            if l_application_url:
                l_return.append(
                    [
                        w.id,
                        l_application_url,
                        self.unrestrictedTraverse(
                            l_application_url
                        ).title_or_id(),
                    ]
                )
        return l_return

    ###########################################
    #   Methods to get the environment objects
    ###########################################

    def getOpenFlowEngine(self):
        """Returns the Collection object, parent of the process"""
        process = self.unrestrictedTraverse(self.process_path, None)
        if process:
            return process.aq_parent

    def getActivity(self, workitem_id):
        """Returns the activity of a workitem"""
        workitem = getattr(self, workitem_id)
        activity_id = workitem.activity_id
        process = self.unrestrictedTraverse(self.process_path, None)
        return getattr(process, activity_id, None)

    security.declareProtected("Use OpenFlow", "getApplicationUrl")

    def getApplicationUrl(self, workitem_id):
        """Return application definition URL relative to instance and
        workitem
        """
        activity = self.getActivity(workitem_id)
        if activity:
            return activity.mapped_application_details()["path"]

    def getEnvironment(self, workitem_id):
        """Returns the engine, the workitem object, the current process and
        activity
        """
        workitem = getattr(self, workitem_id)
        activity_id = workitem.activity_id
        wfengine = self.getOpenFlowEngine()
        process = getattr(wfengine, self.process_path.split("/")[-1], None)
        activity = getattr(process, activity_id, None)
        return wfengine, workitem, process, activity

    def getInstanceProcessId(self):
        """Returns the process id from its path"""
        return self.process_path.split("/")[-1]

    def getProcess(self):
        """Returns the process as an object"""
        return self.unrestrictedTraverse(self.process_path, None)

    security.declareProtected("View management screens", "setProcess")

    def setProcess(self, process_path):
        """Returns the process as an object
        It's something only Managers can do, and only after verifying
        the compatibility between the two processes
        """
        self.process_path = process_path
        self._p_changed = 1

    ###########################################
    #   Workitems
    ###########################################

    def addWorkitem(self, activity_id, blocked, push_roles=[], pull_roles=[]):
        w_id = str(len(self.objectValues("Workitem")))
        w = workitem(
            w_id,
            self.id,
            activity_id,
            blocked,
            push_roles=push_roles,
            pull_roles=pull_roles,
        )
        self._setObject(str(w.id), w)
        w.addEvent("creation")
        return w

    def getJoiningWorkitem(self, activity_id):
        w_list = (
            wk
            for wk in self.getListOfWorkitems(status="blocked")
            if wk.process_path == self.process_path
            and wk.activity_id == activity_id
        )
        # Return the first element from the generator or None
        return next(w_list, None)

    def setStatus(self, status, comment="", actor=""):
        """ """
        old_status = self.status
        new_status = status
        now = time()

        if old_status == "initiated":
            self.initiation_log[-1]["end"] = now
            self.initiation_time += now - self.initiation_log[-1]["start"]
            if new_status == "running":
                self.running_log.append(
                    {
                        "start": now,
                        "end": None,
                        "comment": comment,
                        "actor": actor,
                    }
                )

        if old_status == "running":
            self.running_log[-1]["end"] = now
            self.running_time += now - self.running_log[-1]["start"]
            if new_status == "active":
                self.activation_log.append(
                    {
                        "start": now,
                        "end": None,
                        "comment": comment,
                        "actor": actor,
                    }
                )
            if new_status == "complete":
                self.completion_log.append(
                    {
                        "start": now,
                        "end": None,
                        "comment": comment,
                        "actor": actor,
                    }
                )

        if old_status == "active":
            self.activation_log[-1]["end"] = now
            self.active_time += now - self.activation_log[-1]["start"]
            if new_status == "running":
                self.running_log.append(
                    {
                        "start": now,
                        "end": None,
                        "comment": comment,
                        "actor": actor,
                    }
                )

        self.status = status
        self.reindexObject()

    security.declareProtected("View", "is_active_for_me")

    def is_active_for_me(self, REQUEST=None):
        """returns >0 if there is an active workitem for that person"""
        actor = REQUEST.AUTHENTICATED_USER.getUserName() if REQUEST else ""
        for item in self.getActiveWorkitems():
            if item.actor in (actor, ""):
                return True
        return False

    security.declareProtected("Use OpenFlow", "getActiveWorkitems")

    def getActiveWorkitems(self):
        """returns all active workitems"""
        return self.getListOfWorkitems(status="active")

    security.declareProtected("View", "getListOfWorkitems")

    def getListOfWorkitems(self, status=None):
        """Returns all workitems given a list of statuses
        If the status is not provided, all workitems are returned
        """
        workitems = self.objectValues("Workitem")
        if status is None:
            return workitems

        statuses = set(status) if isinstance(status, list) else set([status])
        return [x for x in workitems if x.status in statuses]

    def setPriority(self, value):
        self.priority = value
        self.reindexObject()

    def isActiveOrRunning(self):
        return self.status in ("active", "running")

    security.declareProtected("Manage OpenFlow", "suspendInstance")

    def suspendInstance(self, REQUEST=None):
        """suspend a specified instance"""
        if self.isActiveOrRunning() or self.status == "initiated":
            if REQUEST:
                actor = REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                actor = ""
            self.old_status = self.status
            self.setStatus(status="suspended", actor=actor)
        if REQUEST:
            if "DestinationURL" in REQUEST:
                REQUEST.RESPONSE.redirect(REQUEST["DestinationURL"])
            else:
                REQUEST.RESPONSE.redirect(REQUEST["HTTP_REFERER"])

    security.declareProtected("Manage OpenFlow", "resumeInstance")

    def resumeInstance(self, REQUEST=None):
        """resume a specified instance"""
        if self.status == "suspended":
            if REQUEST:
                actor = REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                actor = ""
            self.setStatus(status=self.old_status, actor=actor)
            self.old_status = ""
        if REQUEST:
            if "DestinationURL" in REQUEST:
                REQUEST.RESPONSE.redirect(REQUEST["DestinationURL"])
            else:
                REQUEST.RESPONSE.redirect(REQUEST["HTTP_REFERER"])

    security.declareProtected("Manage OpenFlow", "handle_wk_response")

    def handle_wk_response(self, workitem):
        # Handle responses for wk actions
        data = {
            "workitem": {
                "id": workitem.getId(),
                "activityId": workitem.activity_id,
                "activeTime": workitem.active_time,
                "url": workitem.absolute_url(),
                "actor": workitem.actor,
                "status": workitem.status,
            }
        }
        if getattr(self, "REQUEST"):
            if self.REQUEST.environ.get("HTTP_ACCEPT") == "application/json":
                self.REQUEST.RESPONSE.setHeader(
                    "Content-Type", "application/json"
                )
                return json.dumps(data, indent=4)
            if "DestinationURL" in self.REQUEST:
                self.REQUEST.RESPONSE.redirect(self.REQUEST["DestinationURL"])
            else:
                self.REQUEST.RESPONSE.redirect(self.REQUEST["HTTP_REFERER"])
        return json.dumps(data, indent=4)

    security.declareProtected("Manage OpenFlow", "terminateInstance")

    def terminateInstance(self, REQUEST=None):
        """terminate a specified instance"""
        if self.status != "complete":
            if REQUEST:
                actor = REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                actor = ""
            self.setStatus(status="terminated", actor=actor)
        if REQUEST:
            if "DestinationURL" in REQUEST:
                REQUEST.RESPONSE.redirect(REQUEST["DestinationURL"])
            else:
                REQUEST.RESPONSE.redirect(REQUEST["HTTP_REFERER"])

    security.declareProtected("Use OpenFlow", "startInstance")

    def startInstance(self, REQUEST=None):
        """Starts the flowing of the process instance inside the process
        definition
        """
        if REQUEST:
            actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor = ""
        self.setStatus(status="running", actor=actor)
        activity_id = self.begin_activity_id
        engine = self.getOpenFlowEngine()
        push_roles = engine.getPushRoles(
            self.getInstanceProcessId(), activity_id
        )
        pull_roles = engine.getPullRoles(
            self.getInstanceProcessId(), activity_id
        )
        w = self.addWorkitem(activity_id, 0, push_roles, pull_roles)
        self.manageWorkitemCreation(w.id)
        if REQUEST and "DestinationURL" in REQUEST:
            REQUEST.RESPONSE.redirect(REQUEST["DestinationURL"])

    def linkWorkitems(self, workitem_from_id, workitem_to_id_list):
        workitem_from = getattr(self, workitem_from_id)
        workitem_from.addTo(workitem_to_id_list)
        for w_id in workitem_to_id_list:
            w = getattr(self, w_id)
            w.addFrom(workitem_from_id)
            w.setGraphLevel(workitem_from.graph_level + 1)

    security.declareProtected("Use OpenFlow", "assignWorkitem")

    def assignWorkitem(self, workitem_id, actor, REQUEST=None):
        """Assign the specified workitem of the specified instance to the
        specified actor (string)
        """
        workitem = getattr(self, workitem_id)
        activity = self.getActivity(workitem_id)
        user_is_ok = (
            REQUEST is None
            or [
                r
                for r in REQUEST.AUTHENTICATED_USER.getRoles()
                if r in workitem.push_roles
            ]
            or (
                [
                    r
                    for r in REQUEST.AUTHENTICATED_USER.getRoles()
                    if r in workitem.pull_roles
                ]
                and activity.isSelfAssignable()
            )
        )
        workitem_is_ok = (
            self.isActiveOrRunning()
            and not workitem.status == "completed"
            and workitem.actor == ""
        )
        if user_is_ok and workitem_is_ok:
            workitem.assignTo(actor)
        return self.handle_wk_response(workitem)

    security.declareProtected("Use OpenFlow", "unassignWorkitem")

    def unassignWorkitem(self, workitem_id, REQUEST=None):
        """Unassign the specified workitem"""
        workitem = getattr(self, str(workitem_id))
        if self.isActiveOrRunning() and workitem.status != "completed":
            getattr(self, workitem_id).assignTo("")
        return self.handle_wk_response(workitem)

    # FIXME: In Openflow, the actor is not set when you activate the item,
    # unless you have given it as an argument. This seems strange given
    # that activateWorkitem (at least for Reportek) serves to 'reserve' the
    # workitem to a specific worker.
    security.declareProtected("Use OpenFlow", "activateWorkitem")

    def activateWorkitem(self, workitem_id, actor=None, REQUEST=None):
        """declares the activation of the specified workitem of the given
        instance
        """
        if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
            if REQUEST:
                alsoProvides(
                    REQUEST, plone.protect.interfaces.IDisableCSRFProtection
                )
        workitem = getattr(self, str(workitem_id))
        if actor:
            action_actor = actor
        else:
            if REQUEST:
                action_actor = REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                action_actor = ""
        if (
            self.isActiveOrRunning()
            and workitem.status == "inactive"
            and not workitem.blocked
        ):
            if workitem.actor == "":
                if actor is not None:
                    self.assignWorkitem(workitem_id, actor)
                elif action_actor != "":
                    self.assignWorkitem(workitem_id, action_actor)
            workitem.setStatus("active", actor=action_actor)
            self.setStatus(status="active", actor=action_actor)
        return self.handle_wk_response(workitem)

    security.declareProtected("Use OpenFlow", "inactivateWorkitem")

    def inactivateWorkitem(self, workitem_id, REQUEST=None):
        """declares the inactivation of the specified workitem of the given
        instance
        """
        if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
            if REQUEST:
                alsoProvides(
                    REQUEST, plone.protect.interfaces.IDisableCSRFProtection
                )
        workitem = getattr(self, str(workitem_id))
        actor = ""  # We don't need any actor name
        if (
            self.isActiveOrRunning()
            and workitem.status == "active"
            and not workitem.blocked
        ):
            workitem.setStatus("inactive", actor=actor)
            if len(self.getActiveWorkitems()) == 0:
                self.setStatus(status="running", actor=actor)
        return self.handle_wk_response(workitem)

    security.declareProtected("Use OpenFlow", "suspendWorkitem")

    def suspendWorkitem(self, workitem_id, REQUEST=None):
        """declares the suspension of the specified workitem of the given
        instance
        """
        workitem = getattr(self, str(workitem_id))
        if REQUEST:
            actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor = ""
        if (
            self.isActiveOrRunning()
            and workitem.status == "inactive"
            and not workitem.blocked
        ):
            workitem.setStatus("suspended", actor=actor)
            if len(self.getActiveWorkitems()) == 0:
                self.setStatus(status="running", actor=actor)
        return self.handle_wk_response(workitem)

    security.declareProtected("Use OpenFlow", "resumeWorkitem")

    def resumeWorkitem(self, workitem_id, REQUEST=None):
        """declares the resumption of the specified workitem of the given
        instance
        """
        workitem = getattr(self, str(workitem_id))
        if REQUEST:
            actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor = ""
        if (
            self.isActiveOrRunning()
            and workitem.status == "suspended"
            and not workitem.blocked
        ):
            workitem.setStatus("inactive", actor=actor)
        return self.handle_wk_response(workitem)

    security.declareProtected("Use OpenFlow", "completeWorkitem")

    def completeWorkitem(self, workitem_id, actor=None, REQUEST=None):
        """declares the completion of the specified workitem of the given
        instance
        """

        if REQUEST:
            if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
                alsoProvides(
                    REQUEST, plone.protect.interfaces.IDisableCSRFProtection
                )
            if "actor" in REQUEST:
                actor = REQUEST["actor"]
            else:
                actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            l_actor = "openflow_engine"
        if actor:
            l_actor = actor
        workitem = getattr(self, workitem_id)
        activity = self.getActivity(workitem_id)
        process = self.unrestrictedTraverse(self.process_path)
        if self.isActiveOrRunning():
            if workitem.status in ("active", "fallout"):
                workitem.setStatus("complete", actor=l_actor)
                if len(self.getActiveWorkitems()) == 0:
                    self.setStatus(status="running", actor=l_actor)
                if self.isEnd(workitem.activity_id):
                    subflow_workitem_id = self.getSubflowWorkitem(workitem_id)
                    if subflow_workitem_id is not None:
                        self.completeSubflow(subflow_workitem_id)
                    else:
                        self.setStatus(status="complete", actor=l_actor)
                        self.wf_status = "complete"
                        self.reindexObject()
            if (
                activity.isAutoFinish()
                and not process.end == activity.id
                and not activity.isSubflow()
            ):
                # If the current activity is auto start and not bundled with
                # previous, let it be handled by the forwarder
                if activity.isAutoStart() and not activity.isBundled():
                    self.wf_status = activity.get_wf_status()
                    self.reindexObject()
                # If it's manually started or bundled with previous, forward it
                # manually as we might have template forms that have form
                # values
                else:
                    self.forwardWorkitem(workitem_id)
            return self.handle_wk_response(workitem)

    security.declareProtected("Use OpenFlow", "forwardState")

    def forwardState(self, REQUEST=None):
        """.."""
        # Disable CSRF protection
        if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
            alsoProvides(
                self.REQUEST, plone.protect.interfaces.IDisableCSRFProtection
            )
        result = {}
        engine = getattr(self, ENGINE_ID)
        rmq = getattr(engine, "env_fwd_rmq", False)
        if getattr(self, "wf_status", None) in ["forward", "hybrid"]:
            wks = self.getListOfWorkitems()
            wk = wks[-1]
            forwardable = [
                w
                for w in wks
                if w.status == "complete"
                and not (w.activity_id == "End" or w.workitems_to)
            ]
            if forwardable:
                wk = forwardable[0]
            if wk.status in ["complete", "inactive"]:
                self.handleWorkitem(wk.id)
                result["forwarded"] = wk.activity_id
                wks = self.getListOfWorkitems()
                latest_wk = wks[-1]
                if wk != latest_wk:
                    result["triggerable"] = latest_wk.activity_id
            else:
                if self.wf_status == "forward":
                    wk.triggerApplication(wk.id, REQUEST)
                    if rmq:
                        activity = self.getActivity(wk.id)
                        queue_msg(
                            "{}|{}".format(
                                self.absolute_url(), self.get_freq(wk.id)
                            ),
                            queue=self.get_rmq_queue(activity.getId()),
                        )
                    result["triggered"] = wk.activity_id
                elif self.wf_status == "hybrid":
                    wk.triggerApplication(wk.id, REQUEST)

        return engine.jsonify(result)

    def isEnd(self, activity_id):
        """ """
        process = self.restrictedTraverse(self.process_path)
        return process.end == activity_id

    security.declareProtected("Use OpenFlow", "getNextTransitions")

    def getNextTransitions(self, workitem_id):
        """Returns the list of transition that the given workitem (of the
        specified instance) will be routed on"""
        process = self.unrestrictedTraverse(self.process_path)
        activity = self.getActivity(workitem_id)
        engine = self.getOpenFlowEngine()
        workitem = getattr(self, workitem_id)
        transition_list = []
        split_mode = activity.split_mode
        transition_condition_list = [
            {"transition_id": x.id, "condition": x.condition}
            for x in process.objectValues("Transition")
            if x.From == activity.id and hasattr(process, x.To)
        ]
        if len(transition_condition_list) == 1:
            transition_list = [transition_condition_list[0]["transition_id"]]
        else:
            if split_mode == "and":
                transition_list = map(
                    lambda x: x["transition_id"], transition_condition_list
                )
            elif split_mode == "xor":
                for r in [
                    c for c in transition_condition_list if c["condition"]
                ]:
                    expr = Expression(r["condition"])
                    ec = exprNamespace(
                        instance=self,
                        workitem=workitem,
                        process=process,
                        activity=activity,
                        openflow=engine,
                    )
                    if expr(ec):
                        transition_list = [r["transition_id"]]
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
            if getattr(process, activity_to_id).join_mode == "and":
                blocked_init = activity_to.getIncomingTransitionsNumber() - 1
            else:
                blocked_init = 0

            destinations.append(
                {
                    "activity_to_id": activity_to_id,
                    "blocked_init": blocked_init,
                    "process_to_id": process.id,
                }
            )
        return destinations

    def get_rmq_queue(self, act_id=None):
        engine = self.unrestrictedTraverse(ENGINE_ID, None)
        queue = getattr(engine, "env_fwd_rmq_queue", "fwd_envelopes")
        # Uncomment to allow for separate queues based on Activity
        # if act_id and act_id in ['AutomaticQA', 'FMEConversionApplication']:
        #     queue = 'poll_envelopes'
        return queue

    def get_freq(self, workitem_id):
        """Return the frequency at which the application should be exec"""
        freq = 5
        application_url = self.getApplicationUrl(workitem_id)
        application = self.unrestrictedTraverse(application_url, None)
        if application:
            freq = int(getattr(application, "retryFrequency", freq))
        return freq

    def handleWorkitem(self, workitem_id, REQUEST=None):
        # If it's a previously failed application, retry it, otherwise forward
        # it
        workitem = getattr(self, workitem_id)
        activity = self.getActivity(workitem_id)
        engine = self.unrestrictedTraverse(ENGINE_ID, None)
        rmq = getattr(engine, "env_fwd_rmq", False)
        if (
            self.isActiveOrRunning()
            and workitem.status == "inactive"
            and getattr(self, "wf_status", None) == "forward"
        ):
            if activity.isDummy():
                self.manageDummyActivity(workitem_id)
            elif activity.isStandard():
                if activity.isAutoPush():
                    self.callAutoPush(workitem_id)
                if activity.isAutoStart():
                    self.wf_status = activity.get_wf_status()
                    self.reindexObject()
                    self.startAutomaticApplication(workitem_id)
                    if rmq:
                        queue_msg(
                            "{}|{}".format(
                                self.absolute_url(), self.get_freq(workitem_id)
                            ),
                            queue=self.get_rmq_queue(activity.getId()),
                        )
                else:
                    self.wf_status = "manual"
                    self.reindexObject()
            elif activity.isSubflow():
                self.startSubflow(workitem_id)
        else:
            self.forwardWorkitem(workitem_id)

    security.declareProtected("Use OpenFlow", "forwardWorkitem")

    def forwardWorkitem(self, workitem_id, path=None, REQUEST=None):
        """instructs openflow to forward the specified workitem"""
        if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
            if REQUEST:
                alsoProvides(
                    REQUEST, plone.protect.interfaces.IDisableCSRFProtection
                )
        destinations = self.getDestinations(workitem_id, path)
        if destinations == []:
            self.falloutWorkitem(workitem_id)
        else:
            workitem = getattr(self, workitem_id)
            engine = self.getOpenFlowEngine()
            activity = self.getActivity(workitem_id)
            new_workitems = []
            if self.isActiveOrRunning() and (
                workitem.status == "complete"
                and (not workitem.workitems_to or activity.isSubflow())
            ):
                activity_to_id_list = map(
                    lambda x: x["activity_to_id"], destinations
                )
                workitem.addEvent(
                    "forwarded to "
                    + reduce(lambda x, y: x + ", " + y, activity_to_id_list)
                )
                workitem_to_id_list = []
                for d in destinations:
                    w = self.getJoiningWorkitem(d["activity_to_id"])
                    if w:
                        w.unblock()
                        workitem_to_id_list.append(w.id)
                    else:
                        activity_id = d["activity_to_id"]
                        push_roles = engine.getPushRoles(
                            self.getInstanceProcessId(), activity_id
                        )
                        pull_roles = engine.getPullRoles(
                            self.getInstanceProcessId(), activity_id
                        )
                        w = self.addWorkitem(
                            activity_id,
                            d["blocked_init"],
                            push_roles,
                            pull_roles,
                        )
                        workitem_to_id_list.append(w.id)
                    if w.blocked == 0:
                        new_workitems.append(w.id)
                        w.addEvent("arrival from " + workitem.activity_id)
                self.linkWorkitems(workitem_id, workitem_to_id_list)
            for w in new_workitems:
                self.manageWorkitemCreation(w)
        if REQUEST:
            if "DestinationURL" in REQUEST:
                REQUEST.RESPONSE.redirect(REQUEST["DestinationURL"])
            else:
                REQUEST.RESPONSE.redirect(REQUEST["HTTP_REFERER"])

    security.declareProtected("View", "getPreviousActor")

    def getPreviousActor(self, workitem_id):
        """Returns the actor that completed the previous workitem"""
        if workitem_id:
            l_w = getattr(self, str(int(workitem_id) - 1))
            return l_w.completion_log[-1]["actor"]
        else:
            return ""

    security.declareProtected("Use OpenFlow", "changeWorkitem")

    def changeWorkitem(
        self,
        workitem_id,
        push_roles=None,
        pull_roles=None,
        event_log=None,
        activity_id=None,
        blocked=None,
        priority=None,
        workitems_from=None,
        workitems_to=None,
        status=None,
        actor=None,
        graph_level=None,
        REQUEST=None,
    ):
        """use this API to modify anything of a fallout workitem
        usable only if workitem status is 'fallout'
        """
        workitem = getattr(self, workitem_id)
        if workitem.status == "fallout":
            if push_roles is not None:
                workitem.push_roles = push_roles
            if pull_roles is not None:
                workitem.pull_roles = pull_roles
            if event_log is not None:
                workitem.event_log = event_log
            # the workitem.edit takes care of reindexing as well
            workitem.edit(
                activity_id=activity_id,
                blocked=blocked,
                priority=priority,
                workitems_from=workitems_from,
                workitems_to=workitems_to,
                status=status,
                actor=actor,
                graph_level=graph_level,
            )
            workitem._p_changed = 1
        return self.handle_wk_response(workitem)

    security.declareProtected("Use OpenFlow", "falloutWorkitem")

    def falloutWorkitem(self, workitem_id, REQUEST=None):
        """drops the workitem in exceptional handling"""
        workitem = getattr(self, workitem_id)
        if REQUEST:
            actor = REQUEST.AUTHENTICATED_USER.getUserName()
        else:
            actor = ""
        workitem.setStatus("fallout", actor=actor)
        return self.handle_wk_response(workitem)

    def sendWorkitemsToException(self, process_id, activity_id):
        catalog = getToolByName(self, DEFAULT_CATALOG, None)
        for wi in catalog.searchResults(
            meta_type="Workitem",
            process_id=process_id,
            activity_id=activity_id,
            status=["active", "inactive"],
        ):
            self.falloutWorkitem(wi.id)

    security.declareProtected("Manage OpenFlow", "fallinWorkitem")

    def fallinWorkitem(
        self, workitem_id, activity_id, coming_from=None, REQUEST=None
    ):
        """the exceptional specified workitem (of the specified instance)
        will be put back in the activity specified by process_path and
        activity_id; workitem will still be in exceptional state:
        use endFallinWorkitem API to specify the end of the exceptional state
        """
        if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
            if REQUEST:
                alsoProvides(
                    REQUEST, plone.protect.interfaces.IDisableCSRFProtection
                )
        try:
            username = REQUEST["AUTHENTICATED_USER"].getUserName()
        except Exception:
            username = "N/A"
        self.delete_app_jobs(workitem_id)
        workitem_from = getattr(self, workitem_id)
        engine = self.getOpenFlowEngine()
        push_roles = engine.getPushRoles(
            self.getInstanceProcessId(), activity_id
        )
        pull_roles = engine.getPullRoles(
            self.getInstanceProcessId(), activity_id
        )
        workitem_to = self.addWorkitem(activity_id, 0, push_roles, pull_roles)
        self.linkWorkitems(workitem_id, [workitem_to.id])
        event = (
            "fallin to activity {} in process {} (workitem {}) - {}".format(
                activity_id, self.process_path, str(workitem_to.id), username
            )
        )
        workitem_from.addEvent(event)
        event = (
            "fallin from activity {} in process {} (workitem {}) - {}".format(
                workitem_from.activity_id,
                self.process_path,
                str(workitem_id),
                username,
            )
        )
        workitem_to.addEvent(event)
        self.manageWorkitemCreation(workitem_to.id)
        if REQUEST:
            if coming_from is not None:
                REQUEST.RESPONSE.redirect(coming_from)
            else:
                REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    security.declareProtected("Manage OpenFlow", "endFallinWorkitem")

    def endFallinWorkitem(self, workitem_id, REQUEST=None):
        """Ends the exceptional state of the given workitem"""
        if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
            if REQUEST:
                alsoProvides(
                    REQUEST, plone.protect.interfaces.IDisableCSRFProtection
                )
        workitem = getattr(self, workitem_id)
        workitem.addEvent("handled fallout")
        if not [x for x in workitem.getEventLog() if x["event"] == "complete"]:
            workitem.endFallin()
        if REQUEST:
            if "DestinationURL" in REQUEST:
                REQUEST.RESPONSE.redirect(REQUEST["DestinationURL"])
            else:
                REQUEST.RESPONSE.redirect(REQUEST["HTTP_REFERER"])

    security.declarePublic("getActiveWorkitemsForMe")

    def getWorkitemsActiveForMe(self, REQUEST):
        """Returns the list of active workitems
        where an user is the current actor of
        """
        l_actor = REQUEST.AUTHENTICATED_USER.getUserName()
        return [wk for wk in self.getActiveWorkitems() if wk.actor == l_actor]

    ###########################################
    #   Activities and applications
    ###########################################

    security.declareProtected("Use OpenFlow", "manageDummyActivity")

    def manageDummyActivity(self, workitem_id):
        """ """
        self.activateWorkitem(workitem_id, "openflow_engine")
        self.completeWorkitem(workitem_id)
        if not self.isEnd(self.getInstanceProcessId(), self.getActivity().id):
            self.forwardWorkitem(workitem_id)

    security.declareProtected("Use OpenFlow", "startAutomaticApplication")

    def startAutomaticApplication(self, workitem_id, REQUEST=None):
        """ """
        application_url = self.getApplicationUrl(workitem_id)
        activity_obj = self.getActivity(workitem_id)
        self.activateWorkitem(workitem_id, "openflow_engine")

        if application_url:
            args = {"workitem_id": workitem_id}
            if REQUEST:
                args["REQUEST"] = REQUEST
            else:
                args["REQUEST"] = self.REQUEST
            application = self.restrictedTraverse(application_url)
            try:
                application(**args)
            except Exception as e:
                msg = (
                    "ApplicationException while executing: {} "
                    "for envelope: {}, with workitem_id: {} - "
                    "Error: {}".format(
                        application_url, self.absolute_url(), workitem_id, e
                    )
                )
                logger.exception(msg)
                raise ApplicationException(msg)

        if activity_obj.complete_automatically:
            self.completeWorkitem(workitem_id)

    security.declarePrivate("callAutoPush")

    def callAutoPush(self, workitem_id, REQUEST=None):
        """ """
        engine = self.getOpenFlowEngine()
        application_id = self.getActivity(workitem_id).push_application
        if (
            application_id != ""
            and engine._applications[application_id]["url"]
        ):
            application_url = engine._applications[application_id]["url"]
            args = {"workitem_id": workitem_id, "REQUEST": REQUEST}
            # Why should the application return the actor?
            # actor = apply(self.restrictedTraverse(application_url), (), args)
            application = self.restrictedTraverse(application_url)
            try:
                application(**args)
            except Exception as e:
                msg = (
                    "ApplicationException while executing: {} "
                    "for envelope: {}, with workitem_id: {} - "
                    "Error: {}".format(
                        application_url, self.absolute_url(), workitem_id, e
                    )
                )
                logger.exception(msg)
                raise ApplicationException(msg)

            if REQUEST:
                actor = REQUEST.AUTHENTICATED_USER.getUserName()
            else:
                actor = ""
            self.assignWorkitem(workitem_id, actor)

    def manageWorkitemCreation(self, workitem_id):
        """ """
        activity = self.getActivity(workitem_id)
        engine = self.unrestrictedTraverse(ENGINE_ID, None)
        rmq = getattr(engine, "env_fwd_rmq", False)
        if self.status in ("active", "running") and activity:
            if activity.isDummy():
                self.manageDummyActivity(workitem_id)
            elif activity.isStandard():
                if activity.isAutoPush():
                    self.callAutoPush(workitem_id)
                if activity.isAutoStart():
                    self.wf_status = activity.get_wf_status()
                    self.reindexObject()
                    self.startAutomaticApplication(workitem_id)
                    application_url = self.getApplicationUrl(workitem_id)
                    application = self.restrictedTraverse(application_url)
                    if rmq and not isinstance(
                        application, RemoteRabbitMQQAApplication
                    ):
                        queue_msg(
                            "{}|{}".format(
                                self.absolute_url(), self.get_freq(workitem_id)
                            ),
                            queue=self.get_rmq_queue(activity.getId()),
                        )
                else:
                    self.wf_status = "manual"
                    self.reindexObject()
            elif activity.isSubflow():
                self.startSubflow(workitem_id)

    ###########################################
    #   Subflows - not used, not tested
    ###########################################

    security.declarePrivate("startSubflow")

    def startSubflow(self, workitem_id, REQUEST=None):
        """ """
        self.activateWorkitem(workitem_id)
        self.assignWorkitem(workitem_id, "openflow_engine")
        subflow_id = self.getActivity(workitem_id).subflow
        engine = self.getOpenFlowEngine()
        begin_activity_id = getattr(self, subflow_id).begin
        push_roles = engine.getPushRoles(subflow_id, begin_activity_id)
        pull_roles = engine.getPullRoles(subflow_id, begin_activity_id)

        w = self.addWorkitem(begin_activity_id, 0, push_roles, pull_roles)
        self.linkWorkitems(workitem_id, [w.id])
        self.manageWorkitemCreation(w.id)

    def getSubflowWorkitem(self, workitem_id):
        """TODO!"""
        same_process_path = self.unrestrictedTraverse(self.process_path).id
        while workitem_id != []:
            engine, workitem, process, activity = self.getEnvironment(
                workitem_id
            )
            if (
                activity
                and activity.isSubflow()
                and (process.id != same_process_path)
            ):
                return workitem_id
            workitem_id = (
                workitem.workitems_from and workitem.workitems_from[0]
            )
        return None

    def completeSubflow(self, workitem_id):
        """ """
        self.completeWorkitem(workitem_id)
        process = self.unrestrictedTraverse(self.process_path)
        if not self.isEnd(process.id, self.getActivity(workitem_id).id):
            self.forwardWorkitem(workitem_id)

    def traceActivity(self, steps=0, activity_type=None):
        """Return required activity by crawling up it's history."""

        wk_ids = [int(wk_id) for wk_id in self.objectIds("Workitem")]
        last_workitem_id = max(wk_ids)

        if not steps and not activity_type:
            return getattr(self, str(last_workitem_id))

        count = 1
        last_workitem = getattr(self, str(last_workitem_id))

        while str(last_workitem_id) != "0":
            workitem_from = getattr(last_workitem, "workitems_from")
            if len(workitem_from) > 0:
                workitem_from = workitem_from[-1]
            prev_wk = getattr(self, workitem_from)
            prev_wk_id = prev_wk.activity_id

            steps_cond = not activity_type and count == steps
            act_cond = not steps and activity_type == prev_wk_id

            if steps_cond or act_cond:
                return prev_wk
            else:
                last_workitem = getattr(self, prev_wk.getId())
                last_workitem_id = prev_wk.getId()
                count += 1

    def getPreviousActivityOfType(self, activity_type):
        """Return previous activity of type activity_type."""

        return self.traceActivity(activity_type=activity_type)

    def getPreviousActivity(self, steps=1):
        """Return previous step activity."""

        activity = self.traceActivity(steps=steps)
        if activity:
            return activity.activity_id

    def get_viable_cancel_fallin(self):
        """Looks over the envelope's history and determines the manual activity
        to which it can fall into
        """
        wks = self.getListOfWorkitems()[:-1]
        for wk in reversed(wks):
            activity = self.getActivity(wk.getId())
            if not activity.isAutoStart():
                return wk.activity_id
        return "Draft"

    def is_globally_restricted(self):
        """Return True if is globally restricted"""
        engine = self.unrestrictedTraverse(ENGINE_ID, None)
        if getattr(engine, "globally_restricted_site", False):
            return True

    def is_workflow_restricted(self):
        """Return True if is workflow restricted"""
        process = self.getProcess()
        if getattr(process, "restricted", False):
            return True

    def delete_app_jobs(self, workitem_id):
        """Delete jobs associated with the mapped activity"""
        wk = getattr(self, workitem_id)
        if wk.status != "complete":
            if wk.activity_id.startswith("Automatic"):
                annotations = wk._metadata()
                qa_prop = annotations.get(
                    wk.activity_id, getattr(wk, wk.activity_id, None)
                )
                if qa_prop:
                    jobs = qa_prop.get("getResult", {})
                    app_url = self.getApplicationUrl(wk.id)
                    app = self.unrestrictedTraverse(app_url)
                    for job in jobs.keys():
                        app.delete_job(job, workitem_id)
            elif wk.activity_id.startswith("FMEConversion"):
                fme_prop = getattr(wk, "FMEConversion")
                if fme_prop:
                    jobs = fme_prop.get("results", {})
                    app_url = self.getApplicationUrl(wk.id)
                    app = self.unrestrictedTraverse(app_url)
                    for job in jobs:
                        app.delete_job(job, workitem_id)

    security.declareProtected("Reportek Cancel Activity", "cancel_activity")

    def cancel_activity(self, workitem_id, actor=None, REQUEST=None):
        """Cancel the current activity"""
        wk = getattr(self, workitem_id)

        if wk.status != "complete" and len(self.getActiveWorkitems()) > 0:
            r_app = wk.activity_id.startswith(
                "Automatic"
            ) or wk.activity_id.startswith("FMEConversion")
            if not r_app:
                if REQUEST:
                    REQUEST.SESSION.set("note_content_type", "text/html")
                    REQUEST.SESSION.set("note_title", "Error")
                    REQUEST.SESSION.set(
                        "note_text",
                        """Unable to cancel this activity. """
                        """Activity id is: {}""".format(wk.activity_id),
                    )
                    REQUEST.RESPONSE.redirect("note")
            if wk.wf_status in ["forward", "hybrid"]:
                fallinto = self.get_viable_cancel_fallin()
                self.fallinWorkitem(
                    workitem_id=workitem_id,
                    activity_id=fallinto,
                    REQUEST=REQUEST,
                )
                if wk.status != "complete":
                    self.falloutWorkitem(workitem_id, REQUEST=REQUEST)
                    self.endFallinWorkitem(
                        workitem_id=workitem_id, REQUEST=REQUEST
                    )
            if REQUEST:
                if "DestinationURL" in REQUEST:
                    REQUEST.RESPONSE.redirect(REQUEST["DestinationURL"])
                else:
                    REQUEST.RESPONSE.redirect(REQUEST["HTTP_REFERER"])
        else:
            if REQUEST:
                REQUEST.SESSION.set("note_content_type", "text/html")
                REQUEST.SESSION.set("note_title", "Error")
                REQUEST.SESSION.set(
                    "note_text",
                    """Unable to cancel activity. """
                    """Activity status is: {}""".format(wk.status),
                )
                REQUEST.RESPONSE.redirect("note")

    def is_cancellable(self, workitem_id):
        """Return True if activity is cancellable"""
        wk = getattr(self, workitem_id, None)
        if wk and getSecurityManager().checkPermission(
            "Reportek Cancel Activity", self
        ):
            is_lr = wk.activity_id.startswith(
                "Automatic"
            ) or wk.activity_id.startswith("FMEConversion")
            unfinished = (
                wk.status != "complete" and len(self.getActiveWorkitems()) > 0
            )
            if is_lr and unfinished:
                return True

    security.declareProtected("Use OpenFlow", "get_wk_metadata")

    def get_wk_metadata(self, workitem_id, REQUEST=None):
        """Used to get the last history entry"""
        self.REQUEST.RESPONSE.setHeader("Content-Type", "application/json")
        wk = getattr(self, workitem_id, None)

        result = {}
        if wk:
            act_type = {0: "manual", 1: "automatic"}.get(
                wk.getActivity(wk.id).start_mode
            )
            result["activity_type"] = act_type
            result["blocker"] = getattr(wk, "blocker", False)
            result["failure"] = getattr(wk, "failure", False)
            result["activity_id"] = getattr(wk, "activity_id", "")
            result["history"] = [
                {"event": evt.get("event"), "time": evt.get("time").HTML4()}
                for evt in wk.event_log
            ]
        return json.dumps(result)


InitializeClass(EnvelopeInstance)
