from base_admin import BaseAdmin
from AccessControl import getSecurityManager
from Products.Reportek.constants import ENGINE_ID

import json


class SearchDataflow(BaseAdmin):
    """ RecentUploads view """

    def search_dataflow(self):
        """Search the ZCatalog for Report Envelopes,
        show results and keep displaying the form """

        catalog_args = {
            'meta_type': 'Report Envelope',
        }

        status = self.request.get('release_status')
        if status == 'anystatus':
            catalog_args.pop('released', None)
        elif status == 'released':
            catalog_args['released'] = 1
        elif status == 'notreleased':
            catalog_args['released'] = 0
        else:
            return json.dumps([])

        if self.request.get('query_start'):
            catalog_args['start'] = self.request['query_start']
        if self.request.get('obligation'):
            obl = self.request.get('obligation')
            obl = filter(lambda c: c.get('PK_RA_ID') == obl, self.dataflow_rod)[0]
            catalog_args['dataflow_uris'] = [obl['uri']]
        if self.request.get('countries'):
            isos = self.request.get('countries')
            countries = filter(lambda c: c.get('iso') in isos, self.localities_rod)
            catalog_args['country'] = [country['uri'] for country in countries]
        if self.request.get('years'):
            catalog_args['years'] = self.request['years']
        if self.request.get('partofyear'):
            catalog_args['partofyear'] = self.request['partofyear']

        reportingdate_start = self.request.get('reportingdate_start')
        reportingdate_end = self.request.get('reportingdate_end')
        dateRangeQuery = {}
        if reportingdate_start and reportingdate_end:
            dateRangeQuery['range'] = 'min:max'
            dateRangeQuery['query'] = [reportingdate_start, reportingdate_end]
        elif reportingdate_start:
            dateRangeQuery['range'] = 'min'
            dateRangeQuery['query'] = reportingdate_start
        elif reportingdate_end:
            dateRangeQuery['range'] = 'max'
            dateRangeQuery['query'] = reportingdate_end
        if dateRangeQuery:
            catalog_args['reportingdate'] = dateRangeQuery

        reportekEngine = self.context.unrestrictedTraverse('/'+ENGINE_ID)
        envelopes = self.context.Catalog(**catalog_args)
        envelopeObjects = []
        for eBrain in envelopes:
            env = eBrain.getObject()
            if getSecurityManager().checkPermission('View', env):
                files = []
                for fileObj in env.objectValues('Report Document'):
                    files.append({
                        "filename": fileObj.id,
                        "title": str(fileObj.absolute_url_path()),
                        "url": str(fileObj.absolute_url_path()) + "/manage_document"
                    })

                accepted = True
                for fileObj in env.objectValues('Report Feedback'):
                    if fileObj.title in ("Data delivery was not acceptable", "Non-acceptance of F-gas report"):
                        accepted = False

                obligations = []
                for uri in env.dataflow_uris:
                    obligations.append(reportekEngine.dataflow_lookup(uri)['TITLE'])

                envelopeObjects.append({
                    'released': env.released,
                    'path': env.absolute_url_path(),
                    'country': env.getCountryName(),
                    'company': env.aq_parent.title,
                    'userid': env.aq_parent.id,
                    'title': env.title,
                    'years': {"start": env.year, "end": env.endyear},
                    'end_year': env.endyear,
                    'reportingdate': env.reportingdate.strftime('%Y-%m-%d'),
                    'files': files,
                    'obligation': obligations[0],
                    'accepted': accepted
                })

        return json.dumps(envelopeObjects)