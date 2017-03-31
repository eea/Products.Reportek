import json
from base_admin import BaseAdmin
from DateTime import DateTime
from urllib import unquote
from Products.Reportek.constants import WORKFLOW_ENGINE_ID

class EnvelopeUtils(BaseAdmin):

    def __call__(self, *args, **kwargs):
        super(EnvelopeUtils, self).__call__(*args, **kwargs)
        if self.request.get('btn.autocomplete'):
            self.auto_complete_envelopes()
        if self.request.get('btn.search'):
            self.get_not_completed_workitems()
        return self.index()

    def get_envelope_status(self):
        ignore_list = ['complete', 'fallout', 'running']
        status = self.context.Catalog.uniqueValuesFor('status')
        return [s for s in status if s not in ignore_list]

    def get_env_workflow(self, wk):
        """Return the workflow mapped to the envelope's dataflow_uris."""
        wflow_engine = self.context.restrictedTraverse(WORKFLOW_ENGINE_ID)
        wflow_path = '/'.join(wflow_engine.getPhysicalPath())
        p_mapping = wflow_engine.process_mappings
        country = wk.country
        for wflow, mapping in p_mapping.iteritems():
            c_mapping = mapping.get('countries')
            if not wk.dataflow_uris:
                return None
            elif (wk.dataflow_uris[0] in mapping.get('dataflows') and
                  (country in c_mapping or '*' in c_mapping)):
                return '/'.join([wflow_path, wflow])

        return '/'.join([wflow_path, 'default'])

    def get_next_activities(self, wfpath, wk):
        """Return the next possible activities for the envelope with workitem wk
           and workflow path wf_path.
        """
        wf = self.context.restrictedTraverse(wfpath, None)
        next_transitions = []
        if wf:
            wf_transitions = wf.objectValues('Transition')
            next_transitions = [(getattr(t, 'To'), getattr(t, 'condition')) for t in wf_transitions
                                if getattr(t, 'From') == wk.activity_id]

        return next_transitions

    def get_possible_results(self, condition):
        """Return the possible inspectresult values for the workflow."""
        if 'inspectresult' in condition:
            # This is ugly, the proper thing to do would be to use
            # vocabularies for the form values in the application and
            # transitions
            return condition.split('=')[-1].strip().strip("'")

    def get_not_completed_workitems(self):
        status = self.request.get('status', '')
        age = self.request.get('age', 0)
        obligations = self.request.get('dataflow_uris', [])

        query = {'meta_type': 'Workitem',
                 'status': ['active', 'inactive'],
                 'sort_on': 'reportingdate',
                 'sort_order': 'reverse'}

        if age:
            query['reportingdate'] = {
                        'query': DateTime() - age,
                        'range': 'max'}

        if obligations:
            if not isinstance(obligations, list):
                obligations = [obligations]
            query['dataflow_uris'] = obligations

        brains = self.context.Catalog(**query)

        wks_data = {}
        tasks = {}
        workflows = {}

        for brain in brains:
            workitem = brain.getObject()

            if status and not workitem.status == status:
                continue

            activity = workitem.getActivityDetails('title')

            if activity == 'Draft' and workitem.status == 'inactive':
                continue


            wf = self.get_env_workflow(workitem)
            next_activities = self.get_next_activities(wf, workitem)
            if wf:
                if not tasks.get(activity):
                    tasks[activity] = [wf]
                else:
                    if wf not in tasks[activity]:
                        tasks[activity].append(wf)

            if not workflows.get(wf):
                workflows[wf] = {}

            to = {}
            for act in next_activities:
                to[act[0]] = self.get_possible_results(act[1])
            workflows[wf][activity] = to

            wks_data[workitem.getPath()] = {
                'wf_data': {
                    'workflow': wf},
                'workitem': workitem,
            }

        self.request['wks_data'] = wks_data
        self.request['tasks'] = tasks
        self.request['workflows'] = workflows
        self.request['jsonify'] = json.dumps

    def auto_complete_envelopes(self):
        ids = self.request.get('ids', [])
        task = self.request.get('task', '')
        workflow = self.request.get('workflow')
        results = []
        errors = []
        if task:
            for path in ids:
                path = unquote(path)
                workitem = self.context.unrestrictedTraverse(path, None)
                if workitem:
                    if workitem.getActivityDetails('title') != task:
                        continue
                    if workflow != self.get_env_workflow(workitem):
                        continue

                    envelope = workitem.getParentNode()
                    workitem_id = workitem.getId()

                    # activate workitem
                    if workitem.status == 'inactive':
                        envelope.activateWorkitem(workitem_id)

                    try:
                        envelope.completeWorkitem(workitem_id)
                        results.append({'path': '/'.join(path.split('/')[:-1]),
                                        'task': task})
                    except Exception as e:
                        errors.append({'path': '/'.join(path.split('/')[:-1]),
                                       'error': str(e)})
                else:
                    errors.append({'path': '/'.join(path.split('/')[:-1]),
                                   'error': 'Unable to retrieve workitem'})
        self.request['op_results'] = results
        self.request['op_errors'] = errors
