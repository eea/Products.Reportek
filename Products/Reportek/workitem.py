from time import time
import string

import constants
from AccessControl import ClassSecurityInfo
from BTrees.OOBTree import BTree
from ComputedAttribute import ComputedAttribute
from DateTime import DateTime
from Globals import InitializeClass
from OFS.PropertyManager import PropertyManager
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.interfaces import IWorkitem, IWkMetadata
from Products.Reportek.RepUtils import DFlowCatalogAware
from Products.Reportek.CatalogAware import CatalogAware
from zope.event import notify
from zope.interface import implements
from zope.lifecycleevent import ObjectModifiedEvent
from zope.annotation.interfaces import IAnnotations

ANNOTATION_KEY = 'workitem.metadata'


def computed_attribute_decorator(level=0):
    def computed_attribute_wrapper(func):
        return ComputedAttribute(func, level)
    return computed_attribute_wrapper


class workitem(CatalogAware, object, SimpleItem, PropertyManager,
               DFlowCatalogAware):
    """ describes a single workitem of the history graph """

    meta_type = 'Workitem'
    icon = "misc_/Reportek/Workitem.gif"
    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()
    implements(IWorkitem, IWkMetadata)

    def __init__(self, id, instance_id, activity_id, blocked,
                 priority=0, workitems_from=[], workitems_to=[],
                 push_roles=[], pull_roles=[], blocker=False):
        self.id = id
        self.activity_id = activity_id
        self.instance_id = instance_id
        self.workitems_from = workitems_from[:]
        self.workitems_to = workitems_to[:]
        self.status = (blocked and 'blocked') or 'inactive'
        # possible states: blocked,inactive,active,suspended,fallout,complete
        self.event_log = []
        self.actor = ''
        self.graph_level = 0
        self.priority = priority
        self.blocked = blocked
        # blocker means the envelope can not be released due to errors
        # in feedback
        self.blocker = blocker
        self.push_roles = push_roles
        self.pull_roles = pull_roles
        # logging structure
        # each event has the form {'start':xxx, 'end':yyy, 'comment':zzz,
        # 'actor':aaa}
        # 'start' and 'end' are time in msec, 'actor' and 'comment' are string
        self.inactivation_log = []
        self.activation_log = []
        self.completion_log = []
        self.suspension_log = []
        self.fallout_log = []
        # statistic data in msec
        self.inactive_time = 0
        self.active_time = 0
        self.suspended_time = 0
        self.fallout_time = 0
        self.creation_time = DateTime()
        self.__metadata = None
        # log initialization
        if self.status == 'inactive':
            self.inactivation_log.append(
                {'start': time(), 'end': None, 'comment': 'creation',
                 'actor': ''})

    manage_options = (
        ({'label': 'Properties', 'action': 'workitemProperties',
          'help': ('OpenFlowBase', 'workitems.stx')}, ) +
        ({'label': 'View', 'action': 'index_html'}, ) +
        SimpleItem.manage_options
    )

    security.declareProtected('Manage OpenFlow', 'workitemProperties')
    workitemProperties = PageTemplateFile(
        'zpt/Workflow/workitem_edit', globals())

    security.declareProtected('View', 'workitemDetails')
    workitemDetails = PageTemplateFile(
        'zpt/Workflow/workitem_details', globals())

    security.declareProtected('Manage OpenFlow', 'workitem_metadata')
    workitem_metadata = PageTemplateFile(
        'zpt/Workflow/workitem_metadata', globals())

    security.declareProtected('View', 'index_html')
    index_html = PageTemplateFile('zpt/Workflow/workitem_index', globals())

    def title(self):
        return self.activity_id + " by " + self.actor + ", status: " +\
            self.status

    def activity_application(self, activity_id):
        activity = getattr(self.getProcess(), activity_id, None)
        wf_engine = getattr(self, constants.WORKFLOW_ENGINE_ID)
        apps_folder = getattr(self.getPhysicalRoot(),
                              constants.APPLICATIONS_FOLDER_ID)
        path = ''
        if activity:
            if activity.application:
                path = wf_engine._applications.get(
                    activity.application, {}).get('url')
            elif apps_folder.get(self.getProcess().id, {}).get(activity.id):
                path = apps_folder[self.getProcess(
                ).id][activity.id].virtual_url_path()
            elif apps_folder.get('Common', {}).get(activity.id):
                path = apps_folder['Common'][activity.id].virtual_url_path()
            app = self.getPhysicalRoot().restrictedTraverse(path)
            manage_page = 'manage_main'
            if getattr(app, 'manage_settings_html', None):
                manage_page = 'manage_settings_html'
        url = "-"
        if path:
            url = '/%s/%s' % (path, manage_page)
        return {'id': getattr(activity, 'application', None) or activity_id,
                'url': url}

    def activity_link(self, activity_id):
        activity = getattr(self.getProcess(), activity_id, None)
        url = activity.absolute_url()+"/manage_editForm" if activity else "-"
        return {'id': activity_id, 'url': url}

    def lastActivityDate(self):
        """ Returns last activity date and time based on the workitem's
            event log
        """
        if len(self.event_log):
            return self.event_log[-1]['time']
        return self.creation_time

    security.declareProtected('Manage OpenFlow', 'edit')

    def edit(self,
             instance_id=None,
             activity_id=None,
             blocked=None,
             priority=None,
             workitems_from=None,
             workitems_to=None,
             status=None,
             actor=None,
             graph_level=None):
        """ Edit Workitem's properties """
        if instance_id is not None:
            self.instance_id = instance_id
        if activity_id is not None:
            self.activity_id = activity_id
        if priority is not None:
            self.priority = priority
        if workitems_from is not None:
            self.workitems_from = workitems_from
        if workitems_to is not None:
            self.workitems_to = workitems_to
        if status is not None:
            self.setStatus(status)
        if blocked is not None:
            self.blocked = blocked
            if blocked:
                self.status = 'blocked'
        if actor is not None:
            self.actor = actor
        if graph_level is not None:
            self.graph_level = graph_level
        self.reindexObject()

    def addFrom(self, id):
        """ """
        self.workitems_from.append(id)
        self._p_changed = 1
        self.reindexObject()

    def addTo(self, id_list):
        """ """
        self.workitems_to.extend(id_list)
        self._p_changed = 1
        self.reindexObject()

    def setGraphLevel(self, graph_level):
        """ """
        self.graph_level = graph_level
        self.reindexObject()

    def addEvent(self, event, comment=''):
        """ """
        self.event_log.append(
            {'event': event, 'time': DateTime(), 'comment': comment})
        self._p_changed = 1
        notify(ObjectModifiedEvent(self))

    security.declareProtected('View management screens', 'addEventOnTime')

    def addEventOnTime(self, event, p_time, comment=''):
        """ Used only by Managers when updating an workitem log from records
            that already exist
        """
        p_time = DateTime(p_time)
        self.event_log.append(
            {'event': event, 'time': p_time, 'comment': comment})
        self._p_changed = 1

    def isActiveOrInactiveOn(self, process_id, activity_id):
        """ """
        return (self.status in ('active', 'inactive')) \
            and string.split(self.process_path, '/')[-1] == process_id \
            and self.activity_id == activity_id

    def unblock(self, value=1, comment='', actor=''):
        """ """
        self.blocked = max(self.blocked - value, 0)
        if not self.blocked:
            self.setStatus('inactive', comment, actor)

    security.declareProtected('View management screens', 'set_blocker_attr')

    def set_blocker_attr(self, value=1, comment='', actor=''):
        """ sets the 'blocker' flag at the specified value
            used by Managers to fix the envelopes in which the automatic
            QA failed and their acceptability status is wrong
        """
        if value:
            self.blocker = 1
        else:
            self.blocker = 0
        self.actor = actor

        self.addEvent('set blocker flag to %s' % self.blocker, comment)

        self.reindexObject()

    def setStatus(self, status, comment='', actor=''):
        """ """
        old_status = self.status
        new_status = status
        now = time()

        logs = {'inactive': self.inactivation_log,
                'active': self.activation_log,
                'suspended': self.suspension_log,
                'fallout': self.fallout_log,
                'complete': self.completion_log}
        if old_status in logs and logs[old_status]:
            # sets end to old status log
            logs[old_status][-1]['end'] = now
            # adds appropriate time interval to time tracking attribute
            x = now - logs[old_status][-1]['start']
            if old_status == 'inactive':
                self.inactive_time += x
            elif old_status == 'active':
                self.active_time += x
            elif old_status == 'suspended':
                self.suspended_time += x
            elif old_status == 'fallout':
                self.fallout_time += x
        if new_status in logs:
            # creates new element to new status log
            logs[new_status].append(
                {'start': now, 'end': None,
                 'comment': comment, 'actor': actor})

        self.status = status
        self.actor = actor
        self.addEvent(status, comment)
        self.reindexObject()

    def endFallin(self):
        """ """
        if self.status == 'fallout':
            self.setStatus('complete')
        self.reindexObject()

    def setArrivalTime(self, activity_id, comment):
        """ """
        self.addEvent("arrival:" + activity_id)
        self.reindexObject()

    def assignTo(self, actor, by=None, comment=''):
        """ """
        self.actor = actor
        self.addEvent("assigned to " + actor, comment)
        self.reindexObject()

    def getEventLog(self):
        """ """
        return self.event_log

    def getActivityDetails(self, p_attribute):
        """ returns the activity's description """
        l_process = self.unrestrictedTraverse(self.process_path, None)
        try:
            return getattr(getattr(l_process, self.activity_id), p_attribute)
        except Exception:
            return self.activity_id

    def getActivityAttribute(self, attr):
        """Returns activity attr attribute if activity is found.
        Otherwise returns None. Caller must consider both return cases."""
        process = self.unrestrictedTraverse(self.process_path, None)
        try:
            return getattr(getattr(process, self.activity_id), attr)
        except Exception:
            return None

    def _metadata(self, create=True):
        if self.__metadata is not None:
            return self.__metadata

        annotations = IAnnotations(self)
        metadata = annotations.get(ANNOTATION_KEY, None)
        if metadata is None and create:
            metadata = annotations.setdefault(ANNOTATION_KEY, BTree())
        if metadata is not None:
            self.__metadata = metadata
            return self.__metadata

    def get_metadata(self):
        metadata = self._metadata(create=False)
        jobs = metadata.get(self.activity_id, {}).get('getResult', {})
        r = {}
        for key in jobs:
            r[key] = list(jobs[key])
        return r

    @property
    def failure(self):
        return getattr(self, '_failure', False)

    @failure.setter
    def failure(self, value):
        self._failure = bool(value)

    # ComputedAttributes needed in order to retrieve attributes from parent
    @computed_attribute_decorator(level=1)
    def reportingdate(self):
        return getattr(self.getParentNode(), 'reportingdate')

    @computed_attribute_decorator(level=1)
    def dataflow_uris(self):
        return getattr(self.getParentNode(), 'dataflow_uris')


InitializeClass(workitem)
