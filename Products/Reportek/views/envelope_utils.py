import json
from urllib import unquote

from base_admin import BaseAdmin
from DateTime import DateTime
from Products.Reportek.catalog import searchResults
from Products.Reportek.constants import ENGINE_ID, WORKFLOW_ENGINE_ID
from Products.Reportek.rabbitmq import send_message


class EnvelopeUtils(BaseAdmin):

    def __call__(self, *args, **kwargs):
        super(EnvelopeUtils, self).__call__(*args, **kwargs)
        if self.request.get('btn.autocomplete'):
            self.auto_complete_envelopes()
        if self.request.get('btn.search'):
            self.get_not_completed_workitems()
        if self.request.get('btn.publish'):
            self.forwardable_envelopes()
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

    def stuck_envelopes(self):
        catalog = self.context.Catalog
        brains = catalog(meta_type='Activity')
        activities = [brain.getObject() for brain in brains]
        # Get all automated activities
        auto_activities = {act.getId() for act in activities
                           if act.complete_automatically == 1 and
                           act.start_mode == 1 and act.finish_mode == 1}
        # Get all inactive workitems
        query = {
            'meta_type': 'Workitem',
            'status': 'inactive'}
        inactive_brains = searchResults(catalog, query,
                                        admin_check=self.should_check_permission())
        envelopes = []
        for b in inactive_brains:
            obj = b.getObject()
            if obj.activity_id in auto_activities:
                env = obj.aq_parent
                wk_ids = [int(wk_id) for wk_id in env.objectIds('Workitem')]
                last_workitem_id = str(max(wk_ids))
                # Check if it's the last workitem_id and cannot be pulled
                if obj.getId() == last_workitem_id and not obj.pull_roles:
                    activity = env.getActivity(obj.getId())
                    process = env.getProcess()
                    activity_url = process_url = ''
                    activity_title = process_title = 'Not available'
                    if activity:
                        activity_url = activity.absolute_url()
                        activity_title = activity.title_or_id()
                    if process:
                        process_url = process.absolute_url()
                        process_title = process.title_or_id()
                    envelopes.append({
                        'env': {
                            'url': env.absolute_url(),
                            'path': env.getPath()
                        },
                        'process': {
                            'url': process_url,
                            'title': process_title
                        },
                        'activity': {
                            'url': activity_url,
                            'title': activity_title
                        },
                        's_date': DateTime(obj.event_log[-1].get('time')).strftime('%d/%m/%Y %H:%M:%S')
                    })

        return json.dumps(envelopes)

    def env_long_running_aqa(self):
        """Return a list of envelopes with long running Automatic QA"""

        catalog = self.context.Catalog
        query = {
            'meta_type': 'Workitem',
            'activity_id': 'AutomaticQA',
            'status': 'active'
        }
        # Get all active workitems
        aqa_brains = searchResults(catalog, query,
                                   admin_check=self.should_check_permission())
        try:
            age = int(self.request.get('age', 30))
        except Exception:
            age = 30
        envelopes = []
        for brain in aqa_brains:
            if brain.activation_log:
                act_start = brain.activation_log[-1].get('start')
                if DateTime() - DateTime(act_start) >= age:
                    wk = brain.getObject()
                    env = wk.aq_parent
                    activity = env.getActivity(wk.getId())
                    process = env.getProcess()
                    envelopes.append({
                        'env': {
                            'url': env.absolute_url(),
                            'path': env.getPath()
                        },
                        'process': {
                            'url': process.absolute_url(),
                            'title': process.title_or_id()
                        },
                        'activity': {
                            'url': activity.absolute_url(),
                            'title': activity.title_or_id()
                        },
                        's_date': DateTime(obj.event_log[-1].get('time')).strftime('%d/%m/%Y %H:%M:%S')
                    })

        return json.dumps(envelopes)

    def forwardable_envelopes(self):
        pub_envs = self.request.get('envelopes', [])
        if self.request.get('btn.publish') and not pub_envs:
            self.request['op_results'] = []
        if pub_envs:
            results = []
            if self.rmq_fwd:
                for env in pub_envs:
                    try:
                        send_message(env, queue='fwd_envelopes')
                        results.append({
                            'envelope': env,
                            'published': True,
                            'error': None
                        })
                    except Exception as e:
                        results.append({
                            'envelope': env,
                            'published': False,
                            'error': Exception("Unable to send message to RabbitMQ! Details: {}".format(str(e)))
                        })
            self.request['op_results'] = results

        catalog = self.context.Catalog
        query = {
            'meta_type': 'Report Envelope',
            'wf_status': 'forward'
        }
        brains = searchResults(catalog, query,
                               admin_check=self.should_check_permission())
        envelopes = []
        for b in brains:
            env = b.getObject()
            wks = env.getListOfWorkitems()
            last_wk = wks[-1]
            activity = env.getActivity(last_wk.getId())
            process = env.getProcess()
            activity_url = process_url = ''
            activity_title = process_title = 'Not available'
            if activity:
                activity_url = activity.absolute_url()
                activity_title = activity.title_or_id()
            if process:
                process_url = process.absolute_url()
                process_title = process.title_or_id()
            envelopes.append({
                'env': {
                    'url': env.absolute_url(),
                    'path': env.getPath()
                },
                'process': {
                    'url': process_url,
                    'title': process_title
                },
                'activity': {
                    'url': activity_url,
                    'title': activity_title
                },
                's_date': DateTime(last_wk.event_log[-1].get('time')).strftime('%d/%m/%Y %H:%M:%S')
            })

        return json.dumps(envelopes)
