from StringIO import StringIO

import requests
# Zope imports
from AccessControl import ClassSecurityInfo
# Product imports
from activity import activity
from DateTime import DateTime
from Globals import InitializeClass, MessageDialog
from OFS.Folder import Folder
from path import path
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek import constants
from Products.Reportek.interfaces import IProcess
from Products.Reportek.CatalogAware import CatalogAware
from Products.Reportek.RepUtils import getToolByName
from transition import transition
from zope.interface import implements

CycleError = 'CycleError'  # For _topsort()

manage_addProcessForm = PageTemplateFile(
    'zpt/Workflow/process_add.zpt', globals())


def manage_addProcess(self, id, title='', description='', BeginEnd=None,
                      priority=0, begin=None, end=None, REQUEST=None,
                      app_folder=None, restricted=False):
    """ """
    p = process(id, title, description, BeginEnd, priority,
                begin, end, restricted=restricted)
    self._setObject(id, p)
    if app_folder:
        app_folder_path = '/' + constants.APPLICATIONS_FOLDER_ID
        app_folder = self.restrictedTraverse(app_folder_path)
        app_folder.manage_addFolder(id=id, title=title)

    if REQUEST:
        REQUEST.RESPONSE.redirect('manage_main')


class process(CatalogAware, Folder):
    """ A process is a collection of activities and transitions.
    The process map is given by the linking of activities by transitions.
    Each process instance is described by a instance"""

    meta_type = 'Process'
    implements(IProcess)
    security = ClassSecurityInfo()
    icon = 'misc_/Reportek/Process.gif'

    _properties = ({'id': 'title', 'type': 'string', 'mode': 'w'},
                   {'id': 'description', 'type': 'text', 'mode': 'w'},
                   {'id': 'begin', 'type': 'selection', 'mode': 'w',
                       'select_variable': 'listActivities'},
                   {'id': 'end', 'type': 'selection', 'mode': 'w',
                    'select_variable': 'listActivities'},
                   {'id': 'priority', 'type': 'int', 'mode': 'w'},
                   {'id': 'restricted', 'type': 'boolean', 'mode': 'w'}
                   )

    manage_options = (
        {'label': 'Map', 'action': 'index_html'},
        {'label': 'Roles', 'action': 'manage_role_table'},
        {'label': 'Restrictions', 'action': 'manage_process_restrictions'},
        ) + Folder.manage_options[0:1] + Folder.manage_options[2:]

    def __init__(self, id, title, description, BeginEnd, priority, begin, end,
                 restricted=False):
        self.id = id
        self.title = title
        self.description = description
        self.created = DateTime()
        self.priority = priority
        self._restricted = restricted
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

    @property
    def restricted(self):
        return getattr(self, '_restricted', False)

    @restricted.setter
    def restricted(self, value):
        self._restricted = value

    security.declareProtected('Manage OpenFlow', 'manage_addActivityForm')
    manage_addActivityForm = PageTemplateFile(
        'zpt/Workflow/activity_add.zpt', globals())

    security.declareProtected('Manage OpenFlow', 'manage_addTransitionForm')
    manage_addTransitionForm = PageTemplateFile(
        'zpt/Workflow/transition_add.zpt', globals())

    security.declareProtected('Manage OpenFlow', 'index_html')
    index_html = PageTemplateFile('zpt/Workflow/process_map.zpt', globals())

    security.declareProtected('Manage OpenFlow', 'jsIeSupport')

    def jsIeSupport(self):
        return """<!--[if IE]>
    <script>
        var png = $('<img src="%s/workflow_graph">');
        $('.workflow-graph #process_graph').replaceWith(png);
        $('#legend').css({'display': 'inline'});
    </script>
<![endif]-->""" % self.absolute_url()

    security.declareProtected('Manage OpenFlow', 'manage_process_restrictions')
    manage_process_restrictions = PageTemplateFile(
        'zpt/Workflow/process_restrictions.zpt', globals())

    security.declareProtected('Manage OpenFlow', 'manage_role_table')
    manage_role_table = PageTemplateFile(
        'zpt/Workflow/manage_role_table.zpt', globals())

    def manage_role_table_submit(self, REQUEST):
        """ Modify roles for activities in this process """
        for role in self.valid_roles():
            activities = REQUEST.form.get('activities-' + role, [])
            self.aq_parent.editActivitiesPullableOnRole(role, self.getId(),
                                                        activities)
        return self.manage_role_table(manage_tabs_message="Roles updated")

    def get_process_restrictions(self):
        restrictions = self.getRestrictionsOnRole()
        return restrictions.get(self.getId(), {})

    def role_has_permission(self, role, permission):
        p_restrictions = self.get_process_restrictions()
        if role in p_restrictions.get(permission, []):
            return True

    def permissions_acquired(self):
        p_restrictions = self.get_process_restrictions()
        return p_restrictions.get('Acquire', False)

    security.declareProtected('Manage OpenFlow',
                              'manage_restrictions_table_submit')

    def manage_restrictions_table_submit(self):
        """ Modify View permission role assignment for collections with
            mapped dataflow
        """
        roles = ['Manager']
        permission = 'View'
        acquire = 0
        fails = []
        self.restricted = True
        for role in self.valid_roles():
            if 'viewp-{}'.format(role) in self.REQUEST.form:
                roles.append(role)
        if self.REQUEST.form.get('acquire', 'off') == 'on':
            acquire = 1
        brains = self.get_process_colls(self.getId())
        for brain in brains:
            col = brain.getObject()
            try:
                col.set_restricted(permission, roles, acquire=acquire)
            except Exception:
                fails.append(col.absolute_url())

        if fails:
            return MessageDialog(title="Warning!",
                                 message="Unable to set restrictions for: "
                                 + str(','.join(fails)),
                                 action='manage_process_restrictions')
        else:
            self.setRestrictionsOnRole(self.getId(), permission, roles,
                                       acquire=acquire)

        return self.manage_process_restrictions(
            manage_tabs_message="Restrictions updated")

    def listActivities(self):
        return sorted(self.objectIds('Activity'))

    def listUnreferedActivities(self):
        """ Returns a list of activities that have no transitions going to them
        """
        activities = {}  # use dict in order to avoid duplicates
        for t in self.objectValues('Transition'):
            activities[t.From] = ''
            activities[t.To] = ''
        return activities.keys()

    def _topsort(self, pairlist):
        numpreds = {}   # elt -> # of predecessors
        successors = {}  # elt -> list of successors
        for first, second in pairlist:
            # make sure every elt is a key in numpreds
            if first not in numpreds:
                numpreds[first] = 0
            if second not in numpreds:
                numpreds[second] = 0

            # since first < second, second gains a pred ...
            numpreds[second] = numpreds[second] + 1

            # ... and first gains a succ
            if first in successors:
                successors[first].append(second)
            else:
                successors[first] = [second]

        # suck up everything without a predecessor
        answer = filter(lambda x, numpreds=numpreds:
                        numpreds[x] == 0,
                        numpreds.keys())

        # for everything in answer, knock down the pred count on
        # its successors; note that answer grows *in* the loop
        for x in answer:
            del numpreds[x]
            if x in successors:
                for y in successors[x]:
                    numpreds[y] = numpreds[y] - 1
                    if numpreds[y] == 0:
                        answer.append(y)
                # following "del" isn't needed; just makes
                # CycleError details easier to grasp
                del successors[x]

        if numpreds:
            # everything in numpreds has at least one successor ->
            # there's a cycle
            raise CycleError(answer, numpreds, successors)
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
                transpairs.append((self.begin, t.To))
            if t.From != self.end:
                transpairs.append((t.From, self.end))
            if t.To not in froms:
                transpairs.append((t.From, t.To))
            froms.append(t.From)
        return self._topsort(transpairs)

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
                    kind='standard',
                    complete_automatically=1,
                    REQUEST=None):
        """ adds the activity and eventually sets the process begin and
            end activity
        """
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
        if REQUEST:
            REQUEST.RESPONSE.redirect('index_html')

    security.declareProtected('Manage OpenFlow', 'addTransition')

    def addTransition(self, id, From, To, condition=None, description='',
                      REQUEST=None):
        """ adds a transition """
        t = transition(id, From, To, condition, description)
        self._setObject(t.id, t)
        if REQUEST:
            REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    security.declareProtected('Manage OpenFlow', 'manage_delObjects')

    def manage_delObjects(self, ids=[], REQUEST=None):
        """ override default method to handle better the redirection """
        catalog = getToolByName(self, constants.DEFAULT_CATALOG, None)
        for activity_id in [id for id in ids
                            if id in self.objectIds('Activity')]:
            # fallout all the workitems that have this activity id
            for wi in catalog.searchResults(**
                dict(meta_type='Workitem',
                     process_path=self.absolute_url(1),
                     activity_id=activity_id,
                     status=['active', 'inactive'])):
                wi_obj = self.Catalog.getobject(wi.data_record_id_)
                wi_obj.aq_parent.falloutWorkitem(wi.id)
        Folder.manage_delObjects(self, ids)
        if REQUEST:
            REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    security.declarePublic('workflow_graph_help')

    def workflow_graph_help(self, REQUEST, RESPONSE):
        """ Workflow graph description """
        converters_url = self.Converters.get_local_http_converters_url()
        converter_path = 'convert/graphviz'
        dot = path(__file__).parent / 'www' / 'workflow_graph_description.dot'
        resp = requests.post(converters_url + converter_path,
                             files={'file': dot.bytes()})
        if resp.status_code == 200:
            out = resp.content
        else:
            www = path(__file__).parent / 'www'
            out = (www / 'graphviz-error.png').bytes()
        RESPONSE.setHeader('Content-Type', 'image/png')
        return out

    security.declarePublic('workflow_graph_legend')

    def workflow_graph_legend(self):
        """ legend for the workflow graph """
        shorts = process_to_dot(self)['shorts']
        slist = [{'short_name': shorts[s], 'long_name': s} for s in shorts]
        return sorted(slist, key=lambda i: i['short_name'])

    security.declarePublic('workflow_graph')

    def workflow_graph(self, REQUEST, RESPONSE, output='png'):
        """ graphical representation of the workflow state machine """
        converters_url = self.Converters.get_local_http_converters_url()
        graph_data = process_to_dot(self)
        converter_path = 'convert/graphviz'
        if output == 'svg':
            converter_path = 'convert/graphviz_svg'
        resp = requests.post(converters_url + converter_path,
                             files={'file': graph_data['dot']})

        if resp.status_code == 200:
            out = resp.content

        elif output == 'png':
            www = path(__file__).parent / 'www'
            out = (www / 'graphviz-error.png').bytes()

        RESPONSE.setHeader('Content-Type', 'image/png')
        if output == 'svg':
            RESPONSE.setHeader('Content-Type', 'image/svg+xml')
        return out


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
    for t in process.objectValues('Transition'):
        short_tr_from = namify(t.From)
        short_tr_to = namify(t.To)
        condition = t.condition.strip()
        cond_desc = condition
        tooltip = '{0} -> {1}'.format(t.From, t.To)
        if condition.startswith(cond_prefix):
            condition = condition[len(cond_prefix):]
        if condition:
            condition = namify(condition, 'cond')
        line = '{short_tr_from} -> {short_tr_to}'.format(**locals())
        if condition:
            line += ' [ label = "{condition}" fontsize="40.0"] '.format(
                **locals())
            line += ' [ labeltooltip = "{cond_desc}"] '.format(**locals())
            line += ' [ URL = "{0}/manage_workspace" target="_top"] '.format(
                t.absolute_url(1))

        link_lines.append(line)

    dot = StringIO()
    dot.write('digraph "%s workflow"{\n' % process.id)
    dot.write('  rankdir=LR;\n')
    dot.write('  size="10,5"\n')
    dot.write('  node [shape = doublecircle]; %s;\n' % namify(process.begin))
    dot.write('  node [shape = doubleoctagon]; %s;\n' % namify(process.end))
    dot.write('  node [shape = circle];\n')

    for line in link_lines:
        dot.write('  ' + line + ';\n')

    for act in process.objectValues('Activity'):
        app_details = act.mapped_application_details()
        color = 'white'
        if app_details['mapped_by_path']:
            color = 'green'
        elif not app_details['mapped_by_path'] and app_details['path']:
            color = 'orange'
        if app_details['missing']:
            color = 'red'

        label_table = """
            <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="0">
                <TR>
                    <TD BGCOLOR="{1}"
                        HREF="{2}"
                        HEIGHT="30"
                        TOOLTIP="{3}"><FONT POINT-SIZE="20.0">{4}</FONT></TD>
                </TR>
                <TR>
                    <TD HEIGHT="60"
                        BGCOLOR="{5}"
                    ><FONT POINT-SIZE="50.0">{0}</FONT></TD>
                </TR>
            </TABLE>
        """
        mapping_tooltip = "Not mapped to any application"
        if act.mapped_application_details()['path']:
            mapping_tooltip = "{0} mapped to {1} {2}".format(
                ('Automatically'
                 if act.mapped_application_details()['mapped_by_path']
                 else 'Manually'),
                ('missing'
                 if act.mapped_application_details()['missing']
                 else ''),
                act.mapped_application_details()['path'],
            )

        application_url = '/%s/%s/manage_main' % (
            constants.APPLICATIONS_FOLDER_ID,
            process.id
        )
        if act.mapped_application_details()['path']:
            application_url = ('/' + act.mapped_application_details()['path']
                               + '/manage_workspace')

        act_color = 'white'
        if act.id == process.begin:
            act_color = "lightblue"
        if act.id == process.end:
            act_color = "pink"

        dot.write(
            ' {0} [shape=none, margin=0, label = <{1}> ]; '.format(
                namify(act.id),
                label_table.format(
                    namify(act.id),
                    color,
                    application_url,
                    mapping_tooltip,
                    ('AUTO'
                        if act.mapped_application_details()['mapped_by_path']
                        else 'MISS' if
                        act.mapped_application_details()['missing']
                        else 'MAN' if
                        act.mapped_application_details()['path']
                        else ' '
                     ),
                    act_color
                )
            )
        )

        dot.write(
            ' {0} [ tooltip = {1}, labelfontsize="12"] '.format(
                namify(act.id), act.id
            )
        )
        dot.write(
            ' {0} [ URL = "{1}/manage_editForm" target="_top" ] '.format(
                namify(act.id), act.id)
        )

    dot.write('}\n')
    del shorts['-']

    return {
        'dot': dot.getvalue(),
        'shorts': shorts,
    }
