from base_admin import BaseAdmin


class EnvelopeUtils(BaseAdmin):
    """ EnvelopeUtils view """

    def __call__(self, *args, **kwargs):
        if self.request.get('btn.search'):
            print self.get_not_completed_workitems()
        return self.index()


    def get_envelope_status(self):
        status = self.context.Catalog.uniqueValuesFor('status')
        return status

    def get_not_completed_workitems(self):
        status = self.request.get('status', '')
        age = self.request.get('age', 0)
        obligation = self.request.get('obligation', '')

        brains = self.context.Catalog(
                    meta_type='Workitem',
                    reportingdate={
                        'query': DateTime - age,
                        'range': 'min'},
                    status=['active','inactive'],
                    sort_on='reportingdate',
                    sort_order='reverse')

        for brain in brains:
            workitem = brain.getObject()
            if status and not workitem.status == status:
                continue
            if obligation and obligation not in workitem.dataflow_uris:
                continue
            # doc_time = doc.reportingdate
            # if doc_time.greaterThan(now):
            #     continue
            # Filter inactive Drafts
            if (workitem.getActivityDetails('title') == 'Draft'
                and workitem.status == 'inactive'):
                continue
            yield workitem
