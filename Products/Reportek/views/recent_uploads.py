from base_admin import BaseAdmin
from DateTime import DateTime


class RecentUploads(BaseAdmin):
    """ RecentUploads view """

    def get_recent_uploads(self):
        if self.request.get('btn.search'):
            obligations = self.request.get('dataflow_uris', [])
            countries = self.request.get('countries', [])
            start = self.request.get('startdate', '')
            end = self.request.get('enddate', '')

            query = {
                'meta_type': 'Report Envelope',
                "sort_on": "reportingdate",
                "sort_order": "reverse"
            }
            if obligations:
                if not isinstance(obligations, list):
                    obligations = [obligations]
                query['dataflow_uris'] = obligations
            if countries:
                query['country'] = self.get_country_codes(countries)
            if start or end:
                start_date = DateTime('1980-01-01')
                end_date = DateTime()
                if start:
                    start_date = DateTime(start)
                if end:
                    end_date = DateTime(end)
                query['reportingdate'] = {
                    'range': 'min:max',
                    'query': (start_date, end_date)
                }

            records = []
            for brain in self.context.Catalog(query):
                env = brain.getObject()
                items = sorted(env.objectValues('Workitem'), key=lambda e: e.lastActivityDate)
                feedbacks = env.objectValues('Report Feedback')
                files = env.objectValues(['Report Document', 'Report Hyperlink'])
                records.append({
                    'reportingdate': env.reportingdate.strftime('%Y-%m-%d'),
                    'country': env.getCountryName(),
                    'title': env.title,
                    'link': env.getPath(),
                    'activity': items[-1].activity_id,
                    'status': items[-1].status,
                    'feedbacks': feedbacks,
                    'files': files
                })

            return records
        return []
