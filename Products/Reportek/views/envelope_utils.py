from base_admin import BaseAdmin
from DateTime import DateTime
from urllib import unquote


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

    def get_not_completed_workitems(self):
        status = self.request.get('status', '')
        age = self.request.get('age', 0)
        obligations = self.request.get('obligations', [])

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
            df_uris = [self.get_obligations()[obl] for obl in obligations]
            query['dataflow_uris'] = df_uris

        brains = self.context.Catalog(**query)

        workitems = []
        tasks = set()

        for brain in brains:
            workitem = brain.getObject()

            if status and not workitem.status == status:
                continue

            activity = workitem.getActivityDetails('title')

            if activity == 'Draft' and workitem.status == 'inactive':
                continue

            tasks.add(activity)
            workitems.append(workitem)

        # return workitems, tasks
        self.request['workitems'] = workitems
        self.request['tasks'] = tasks

    def auto_complete_envelopes(self):
        ids = self.request.get('ids', [])
        task = self.request.get('task', '')
        results = []
        errors = []
        if task:
            for path in ids:
                path = unquote(path)
                workitem = self.context.unrestrictedTraverse(path, None)
                if workitem:
                    if task and workitem.getActivityDetails('title') != task:
                        continue

                    envelope = workitem.getParentNode()
                    workitem_id = workitem.getId()

                    # activate workitem
                    if workitem.status == 'inactive':
                        envelope.activateWorkitem(workitem_id)

                    # complete envelope
                    self.request.set('inspectresult', 'Finish')
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
