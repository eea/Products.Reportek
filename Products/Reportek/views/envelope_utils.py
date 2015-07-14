from base_admin import BaseAdmin
from DateTime import DateTime


class EnvelopeUtils(BaseAdmin):

    def __call__(self, *args, **kwargs):

        if self.request.get('btn.autocomplete'):
            self.auto_complete_envelopes()
            return self.request.response.redirect('%s/%s?done=1' % (
                        self.context.absolute_url(), self.__name__))

        if self.request.get('btn.search'):
            workitems, tasks = self.get_not_completed_workitems()
            return self.index(workitems=workitems,
                              tasks=tasks)

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
                        'range': 'min'}

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

        return workitems, tasks

    def auto_complete_envelopes(self):
        ids = self.request.get('ids', [])
        task = self.request.get('task', '')

        for path in ids:
            workitem = self.context.unrestrictedTraverse(path, None)
            if task and workitem.getActivityDetails('title') != task:
                continue

            envelope = workitem.getParentNode()
            workitem_id = workitem.getId()

            # activate workitem
            if workitem.status == 'inactive':
                envelope.activateWorkitem(workitem_id)

            # complete envelope
            self.request.set('inspectresult', 'Finish')
            envelope.completeWorkitem(workitem_id, REQUEST=self.request)
