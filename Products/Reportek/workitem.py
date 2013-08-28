import constants
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from time import time
from OFS.SimpleItem import SimpleItem 
from OFS.PropertyManager import PropertyManager
from Globals import DTMLFile,InitializeClass
from Products.ZCatalog.CatalogPathAwareness import CatalogAware

class workitem(CatalogAware, SimpleItem, PropertyManager):
    """ describes a single workitem of the history graph """

    meta_type = 'Workitem'
    icon = "misc_/Reportek/Workitem.gif"
    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()

    def __init__(self, id, instance_id, activity_id, blocked,
                 priority=0, workitems_from=[], workitems_to=[],
                 push_roles=[], pull_roles=[], blocker=False) :
        self.id = id
        self.activity_id = activity_id
        self.instance_id = instance_id
        self.workitems_from = workitems_from[:]
        self.workitems_to = workitems_to[:]
        self.status = (blocked and 'blocked') or 'inactive'
        #possible states: blocked,inactive,active,suspended,fallout,complete
        self.event_log = []
        self.actor = ''
        self.graph_level = 0
        self.priority = priority
        self.blocked = blocked
        #blocker means the envelope can not be released due to errors in feedback
        self.blocker = blocker
        self.push_roles = push_roles
        self.pull_roles = pull_roles
        #logging structure
        #each event has the form {'start':xxx, 'end':yyy, 'comment':zzz, 'actor':aaa}
        #'start' and 'end' are time in msec, 'actor' and 'comment' are string
        self.inactivation_log = []
        self.activation_log = []
        self.completion_log = []
        self.suspension_log = []
        self.fallout_log = []
        #statistic data in msec
        self.inactive_time = 0
        self.active_time = 0
        self.suspended_time = 0
        self.fallout_time = 0
        self.creation_time = DateTime()
        #log initialization
        if self.status=='inactive':
            self.inactivation_log.append({'start':time(),'end':None,'comment':'creation','actor':''})

    manage_options=(
        ( {'label':'Properties', 'action':'workitemProperties', 'help' : ('OpenFlowBase', 'workitems.stx') }, ) +
        ( {'label':'View', 'action':'index_html' }, ) +
        SimpleItem.manage_options
        )

    security.declareProtected('Manage OpenFlow', 'workitemProperties')
    workitemProperties = DTMLFile('dtml/Workflow/workitemEdit', globals())

    security.declareProtected('Use OpenFlow', 'workitemDetails')
    workitemDetails = DTMLFile('dtml/Workflow/workitemDetails', globals())

    security.declareProtected('View', 'index_html')
    index_html=DTMLFile('dtml/Workflow/workitemIndex',globals())

    def __setstate__(self,state):
        """ """
        workitem.inheritedAttribute('__setstate__')(self, state)

    def title(self):
        return self.activity_id + " by " + self.actor + ", status: " + self.status

    def activity_application(self, activity_id):
        activity = getattr(self.getProcess(), activity_id)
        wf_engine = getattr(self, constants.WORKFLOW_ENGINE_ID)
        apps_folder = getattr(self.getPhysicalRoot(), constants.APPLICATIONS_FOLDER_ID)
        path = ''
        if activity.application:
            path = wf_engine._applications.get(activity.application, {}).get('url')
        elif apps_folder.get(self.getProcess().id, {}).get(activity.id):
            path = apps_folder[self.getProcess().id][activity.id].virtual_url_path()
        elif apps_folder.get('Common', {}).get(activity.id):
            path = apps_folder['Common'][activity.id].virtual_url_path()
        app = self.getPhysicalRoot().restrictedTraverse(url)
        manage_page = 'manage_main'
        if getattr(app, 'manage_settings_html', None):
            manage_page = 'manage_settings_html'
        if path:
            url = '/%s/%s' %(url, manage_page)
        else:
            url = "-"
        return {'id': activity.application or activity.id, 'url': url}


    def lastActivityDate(self):
        """ Returns last activity date and time based on the workitem's event log """
        if len(self.event_log):
            return self.event_log[-1]['time']
        return creation_time

    security.declareProtected('Manage OpenFlow', 'edit')
    def edit(self,
             instance_id = None,
             activity_id = None,
             blocked = None,
             priority = None,
             workitems_from = None,
             workitems_to = None,
             status = None,
             actor = None,
             graph_level = None):
        """ Edit Workitem's properties """
        if instance_id != None:
            self.instance_id = instance_id
        if activity_id != None:
            self.activity_id = activity_id
        if priority != None:
            self.priority = priority
        if workitems_from != None:
            self.workitems_from = workitems_from
        if workitems_to != None:
            self.workitems_to = workitems_to
        if status != None:
            self.setStatus(status)
        if blocked != None:
            self.blocked = blocked
            if blocked:
                self.status='blocked'
        if actor != None:
            self.actor = actor
        if graph_level != None:
            self.graph_level = graph_level
        self.reindex_object()

    def addFrom(self, id):
        """ """
        self.workitems_from.append(id)
        self._p_changed=1
        self.reindex_object()

    def addTo(self, id_list):
        """ """
        self.workitems_to.extend(id_list)
        self._p_changed=1
        self.reindex_object()

    def setGraphLevel(self, graph_level):
        """ """
        self.graph_level = graph_level
        self.reindex_object()

    def addEvent(self, event, comment=''):
        """ """
        self.event_log.append({'event' : event, 'time' : DateTime(), 'comment': comment})
        self._p_changed=1

    security.declareProtected('View management screens', 'addEventOnTime')
    def addEventOnTime(self, event, p_time, comment=''):
        """ Used only by Managers when updating an workitem log from records that already exist """
        p_time = DateTime(p_time)
        self.event_log.append({'event' : event, 'time' : p_time, 'comment': comment})
        self._p_changed=1

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

    def setStatus(self, status, comment='', actor=''):
        """ """
        old_status = self.status
        new_status = status
        now = time()

        logs = {'inactive':self.inactivation_log,
                'active':self.activation_log,
                'suspended':self.suspension_log,
                'fallout':self.fallout_log,
                'complete':self.completion_log}
        if logs.has_key(old_status) and logs[old_status]:
            # sets end to old status log
            logs[old_status][-1]['end'] = now
            # adds appropriate time interval to time tracking attribute
            x = now - logs[old_status][-1]['start']
            if old_status=='inactive': self.inactive_time += x
            elif old_status=='active': self.active_time += x
            elif old_status=='suspended': self.suspended_time += x
            elif old_status=='fallout': self.fallout_time += x
        if logs.has_key(new_status):
            # creates new element to new status log
            logs[new_status].append({'start':now,'end':None,'comment':comment,'actor':actor})
            
        self.status = status
        self.actor = actor
        self.addEvent(status, comment)
        self.reindex_object()

    def endFallin(self):
        """ """
        if self.status == 'fallout':
            self.setStatus('complete')
        self.reindex_object()

    def setArrivalTime(self, activity_id, comment):
        """ """
        self.addEvent("arrival:" + activity_id)
        self.reindex_object()

    def assignTo(self, actor, by=None, comment=''):
        """ """
        self.actor = actor
        self.addEvent("assigned to " + actor, comment)
        self.reindex_object()

    def getEventLog(self):
        """ """
        return self.event_log

    def getActivityDetails(self, p_attribute):
        """ returns the activity's description """
        l_process = self.unrestrictedTraverse(self.process_path)
        try:
            return getattr(getattr(l_process, self.activity_id), p_attribute)
        except:
            return self.activity_id


InitializeClass(workitem)
