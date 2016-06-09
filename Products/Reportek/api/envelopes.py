from DateTime import DateTime
from Products.Five import BrowserView
from Products.Reportek.constants import ENGINE_ID
import datetime
import json


class EnvelopesAPI(BrowserView):
    """Envelopes API"""

    def __call__(self):
        return self.get_envelopes()

    def getCountryCode(self, country_uri):
        """ Returns country ISO code from the country uri
        """
        dummycounty = {'name': 'Unknown', 'iso': 'xx'}
        engine = getattr(self.context, ENGINE_ID)
        localities_table = engine.localities_table()
        if country_uri:
            try:
                return str([x['iso'] for
                            x in localities_table
                            if str(x['uri']) == country_uri][0])
            except:
                return dummycounty['iso']

    def get_files(self, env_path=None):
        """Return envelope's files."""
        documents = []
        if env_path:
            envelope = self.context.restrictedTraverse(env_path, None)
            if envelope:
                for doc in envelope.objectValues('Report Document'):
                    doc_properties = {
                        'url': doc.absolute_url(0),
                        'title': doc.title,
                        'contentType': doc.content_type,
                        'schemaURL': doc.xml_schema_location,
                        'uploadDate': doc.upload_time().HTML4()
                    }

                    documents.append(doc_properties)

        return documents

    def build_catalog_query(self):
        """Return a catalog query dictionary based on query params."""
        params = self.request.form.keys()
        valid_filters = [
            'isReleased',
            'reportingDate',
            'obligations',
            'periodDescription'
        ]

        catalog_field_map = {
            'title': 'title',
            'isReleased': 'released',
            'reportingDate': 'reportingdate',
            'periodDescription': 'partofyear',
        }

        query = {
            'meta_type': 'Report Envelope'
        }
        for param in params:
            if param in valid_filters:
                if param != 'obligations':
                    c_idx = catalog_field_map.get(param)
                    value = self.request.form.get(param)
                    if param == 'isReleased':
                        value = int(value)
                    if param == 'reportingDate':
                        startd = datetime.datetime.strptime(value, '%Y-%m-%d')
                        endd = startd + datetime.timedelta(days=1)
                        value = {
                            'query': (DateTime(startd), DateTime(endd)),
                            'range': 'min:max'
                        }
                    query[c_idx] = value
                else:
                    obligations = self.request.form.get(param)
                    if obligations:
                        obligations = obligations.split(',')
                        df_tpl = 'http://rod.eionet.europa.eu/obligations/{}'
                        df_uris = [df_tpl.format(o) for o in obligations]

                    query['dataflow_uris'] = df_uris

        return query

    def get_envelope_wk_brains(self, path):
        query = {
            'path': path,
            'meta_type': 'Workitem',
        }
        brains = self.context.Catalog(**query)

        return brains

    def is_env_blocked(self, wk_brains):
        qa_wks = [wk for wk in wk_brains if wk.activity_id == 'AutomaticQA']
        if not qa_wks:
            return 0
        else:
            blocker = qa_wks[-1].blocker
            if not blocker:
                return 0
            return 1

    def get_envelopes(self):
        """Return envelopes."""
        results = []

        fields = self.request.form.get('fields')

        if fields:
            fields = fields.split(',')

        query = self.build_catalog_query()
        brains = self.context.Catalog(**query)
        for brain in brains:
            years = brain.years
            startyear = years[0] if years else ''
            endyear = years[-1] if years and len(years) > 1 else ''
            wk_brains = self.get_envelope_wk_brains(brain.getPath())
            default_props = {
                'url': brain.getURL(),
                'title': getattr(brain, 'title', None),
                'description': brain.Description,
                'countryCode': self.getCountryCode(brain.country),
                'isReleased': brain.released,
                'reportingDate': brain.reportingdate.HTML4(),
                'periodStartYear': startyear,
                'periodEndYear': endyear,
                'periodDescription': brain.partofyear,
                'isBlockedByQCError': self.is_env_blocked(wk_brains),
                'status': wk_brains[-1].activity_id
            }
            envelope_data = {}

            if not fields:
                fields = default_props.keys()

            for field in fields:
                if field == 'files':
                    envelope_data['files'] = self.get_files(brain.getPath())
                elif field in default_props.keys():
                    envelope_data[field] = default_props.get(field)

            if envelope_data:
                results.append(envelope_data)

        return json.dumps(results, indent=4)
