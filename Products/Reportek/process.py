import sys
from StringIO import StringIO
import subprocess
import tempfile
from path import path
import requests

# Zope imports
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass, DTMLFile
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS.Folder import Folder
from DateTime import DateTime
from Products.ZCatalog.CatalogPathAwareness import CatalogAware
from Globals import package_home

# Product imports
from activity import activity
from transition import transition

CycleError = 'CycleError' # For _topsort()

manage_addProcessForm = DTMLFile('dtml/Workflow/processAdd', globals())

def manage_addProcess(self, id, title='', description='', BeginEnd=None, priority=0, begin=None, end=None, REQUEST=None):
    """ """
    p = process(id, title, description, BeginEnd, priority, begin, end)
    self._setObject(id, p)
    if REQUEST: REQUEST.RESPONSE.redirect('manage_main')

class process(CatalogAware, Folder):
    """ A process is a collection of activities and transitions.
    The process map is given by the linking of activities by transitions.
    Each process instance is described by a instance"""

    meta_type = 'Process'
    security = ClassSecurityInfo()
    icon='misc_/Reportek/Process.gif'

    _properties = ({'id':'title', 'type':'string', 'mode':'w'},
            {'id':'description', 'type':'text', 'mode':'w'},
            {'id':'begin', 'type':'selection', 'mode':'w', 'select_variable': 'listActivities'},
            {'id':'end', 'type':'selection', 'mode':'w', 'select_variable': 'listActivities'},
            {'id':'priority', 'type':'int', 'mode':'w'}
    )

    manage_options = (
            {'label' : 'Map', 'action' : 'index_html'},
            {'label' : 'Roles', 'action' : 'manage_role_table'},
        ) + Folder.manage_options[0:1] + Folder.manage_options[2:]

    def __init__(self, id, title, description, BeginEnd, priority, begin, end):
        self.id = id
        self.title = title
        self.description = description
        self.created = DateTime()
        self.priority = priority
        if BeginEnd:
            self.addActivity('Begin')
            self.addActivity('End')
            self.begin = 'Begin'
            self.end = 'End'
        else:
            if begin:
                self.begin = begin
            else:
                self.begin = ''
            if end:
                self.end = end
            else:
                self.end = ''

    security.declareProtected('Manage OpenFlow', 'manage_addActivityForm')
    manage_addActivityForm = DTMLFile('dtml/Workflow/activityAdd', globals())

    security.declareProtected('Manage OpenFlow', 'manage_addTransitionForm')
    manage_addTransitionForm = DTMLFile('dtml/Workflow/transitionAdd', globals())

    security.declareProtected('Manage OpenFlow', 'index_html')
    index_html = DTMLFile('dtml/Workflow/processMap', globals())

#   security.declareProtected('Manage OpenFlow', 'Setting')
#   Setting = DTMLFile('dtml/Workflow/processSetting', globals())

    security.declareProtected('Manage OpenFlow', 'manage_role_table')
    manage_role_table = PageTemplateFile('zpt/Workflow/manage_role_table.zpt', globals())

    def manage_role_table_submit(self, REQUEST):
        """ Modify roles for activities in this process """
        for role in self.valid_roles():
            activities = REQUEST.form.get('activities-' + role, [])
            self.aq_parent.editActivitiesPullableOnRole(role, self.getId(),
                                                        activities)
        return self.manage_role_table(manage_tabs_message="Roles updated")

    def listActivities(self):
        return sorted(self.objectIds('Activity'))

    def listUnreferedActivities(self):
        """ Returns a list of activities that have no transitions going to them"""
        activities = {} #use dict in order to avoid duplicates
        for transition in self.objectValues('Transition'):
            activities[transition.From] = ''
            activities[transition.To] = ''
        return activities.keys()

    def _topsort(self, pairlist):
        numpreds = {}   # elt -> # of predecessors
        successors = {} # elt -> list of successors
        for first, second in pairlist:
            # make sure every elt is a key in numpreds
            if not numpreds.has_key( first ):
                numpreds[first] = 0
            if not numpreds.has_key( second ):
                numpreds[second] = 0

            # since first < second, second gains a pred ...
            numpreds[second] = numpreds[second] + 1

            # ... and first gains a succ
            if successors.has_key( first ):
                successors[first].append( second )
            else:
                successors[first] = [second]

        # suck up everything without a predecessor
        answer = filter( lambda x,numpreds=numpreds:
                             numpreds[x] == 0,
                         numpreds.keys() )

        # for everything in answer, knock down the pred count on
        # its successors; note that answer grows *in* the loop
        for x in answer:
            del numpreds[x]
            if successors.has_key( x ):
                for y in successors[x]:
                    numpreds[y] = numpreds[y] - 1
                    if numpreds[y] == 0:
                        answer.append( y )
                # following "del" isn't needed; just makes
                # CycleError details easier to grasp
                del successors[x]

        if numpreds:
            # everything in numpreds has at least one successor ->
            # there's a cycle
            raise CycleError, (answer, numpreds, successors)
        return answer

    security.declarePublic('listActivitiesSorted')
    def listActivitiesSorted(self):
        """ This is a method to sort the activities topologically
            Only those that have transitions
            Beware of loops
            Just for fun
        """
        transpairs = []
        froms = [self.begin]
        for t in self.objectValues('Transition'):
            if t.To != self.begin:
                transpairs.append((self.begin,t.To))
            if t.From != self.end:
                transpairs.append((t.From,self.end))
            if t.To not in froms:
                transpairs.append((t.From,t.To))
            froms.append(t.From)
        return self._topsort(transpairs)

#   security.declareProtected('Manage OpenFlow', 'edit')
#   def edit(self,
#            begin=None,
#            end=None,
#            title=None,
#            description=None,
#            priority=None,
#            REQUEST=None):
#       """ changes the process settings """
#       if title:
#           self.title = title
#       if description:
#           self.description = description
#       if begin:
#           self.begin = begin
#       if end:
#           self.end = end
#       if priority:
#           self.priority = priority
#       if REQUEST:
#           return self.Setting(self,REQUEST,manage_tabs_message="Changed")

    security.declareProtected('Manage OpenFlow', 'addActivity')
    def addActivity(self,
                    id,
                    split_mode='and',
                    join_mode='and',
                    self_assignable=1,
                    start_mode=0,
                    finish_mode=0,
                    subflow='',
                    push_application='',
                    application='',
                    title='',
                    parameters='',
                    description='',
                    kind = 'standard',
                    complete_automatically=1,
                    REQUEST=None):
        """ adds the activity and eventually sets the process begin and end activity """
        a = activity(id=id,
                     join_mode=join_mode,
                     split_mode=split_mode,
                     self_assignable=self_assignable,
                     start_mode=start_mode,
                     finish_mode=finish_mode,
                     subflow=subflow,
                     push_application=push_application,
                     application=application,
                     title=title,
                     parameters=parameters,
                     description=description,
                     complete_automatically=complete_automatically,
                     kind=kind)
        self._setObject(id, a)
        if REQUEST: REQUEST.RESPONSE.redirect('index_html')

    security.declareProtected('Manage OpenFlow', 'addTransition')
    def addTransition(self, id, From, To, condition=None, description='', REQUEST=None):
        """ adds a transition """
        t = transition(id, From, To, condition, description)
        self._setObject(t.id, t)
        if REQUEST: REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    security.declareProtected('Manage OpenFlow', 'manage_delObjects')
    def manage_delObjects(self, ids=[], REQUEST=None):
        """ override default method to handle better the redirection """
        for activity_id in [id for id in ids if id in self.objectIds('Activity')]:
            # fallout all the workitems that have this activity id
            for wi in self.Catalog(meta_type='Workitem',
                                   process_path=self.absolute_url(1),
                                   activity_id=activity_id,
                                   status=['active', 'inactive']):
                wi_obj = self.Catalog.getobject(wi.data_record_id_)
                wi_obj.aq_parent.falloutWorkitem(wi.id)
        Folder.manage_delObjects(self, ids)
        if REQUEST: REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    security.declarePublic('workflow_graph_legend')
    def workflow_graph_legend(self):
        """ legend for the workflow graph """
        shorts = process_to_dot(self)['shorts']
        slist = [{'short_name': shorts[s], 'long_name': s} for s in shorts]
        return sorted(slist, key=lambda i: i['short_name'])

    security.declarePublic('workflow_graph')
    def workflow_graph(self, REQUEST, RESPONSE):
        """ graphical representation of the workflow state machine """
        converters_url = self.Converters.get_local_http_converters_url()
        graph_data = process_to_dot(self)
        resp = requests.post(converters_url + 'convert/graphviz',
                             files={'file': graph_data['dot']})

        if resp.status_code == 200:
            png = resp.content

        else:
            www = path(__file__).parent / 'www'
            png = (www / 'graphviz-error.png').bytes()

        RESPONSE.setHeader('Content-Type', 'image/png')
        return png


InitializeClass(process)


def process_to_dot(process):
    def make_acronym(name):
        return ''.join(ch for ch in name if ch.isupper())

    shorts = {'-': 'cond'}
    def namify(name, acronym=None):
        if name not in shorts:
            if acronym is None:
                if len(name) < 10:
                    return name
                acronym = make_acronym(name)
            sh0 = sh = acronym
            n = 0
            while sh in shorts.values():
                n += 1
                sh = '%s%d' % (sh0, n)
            shorts[name] = sh
        return shorts[name]

    cond_prefix = 'python:'
    link_lines = []
    for transition in process.objectValues('Transition'):
        short_tr_from = namify(transition.From)
        short_tr_to = namify(transition.To)
        condition = transition.condition.strip()
        if condition.startswith(cond_prefix):
            condition = condition[len(cond_prefix):]
        if condition:
            condition = namify(condition, 'cond')
        line = '{short_tr_from} -> {short_tr_to}'.format(**locals())
        if condition:
            line += ' [ label = "{condition}" ]'.format(**locals())
        link_lines.append(line)

    dot = StringIO()
    dot.write('digraph finite_state_machine {\n')
    dot.write('  rankdir=LR;\n')
    dot.write('  size="8,5"\n')
    dot.write('  node [shape = doublecircle]; %s;\n' % namify(process.begin))
    dot.write('  node [shape = doubleoctagon]; %s;\n' % namify(process.end))
    dot.write('  node [shape = circle];\n')

    for line in link_lines:
        dot.write('  ' + line + ';\n')

    dot.write('}\n')
    del shorts['-']

    return {
        'dot': dot.getvalue(),
        'shorts': shorts,
    }
