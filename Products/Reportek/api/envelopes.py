import datetime
from DateTime import DateTime
import json
from Products.Five import BrowserView


class EnvelopesAPI(BrowserView):
    """Envelopes API"""

    def __call__(self):
        return self.get_envelopes()

    def get_files(self, envelope=None):
        """Return envelope's files."""
        documents = []
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
        valid_filters = ['isReleased', 'reportingDate', 'obligations']

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

    def get_envelopes(self):
        """Return envelopes."""
        results = []

        fields = self.request.form.get('fields')

        if fields:
            fields = fields.split(',')

        query = self.build_catalog_query()
        brains = self.context.Catalog(**query)
        for brain in brains:
            env = brain.getObject()
            default_props = {
                'url': env.absolute_url(0),
                'title': env.title,
                'description': env.descr,
                'countryCode': env.getCountryCode(),
                'isReleased': env.released,
                'reportingDate': env.reportingdate.HTML4(),
                'periodStartYear': env.year,
                'periodEndYear': env.endyear,
                'periodDescription': env.partofyear,
                'isBlockedByQCError': env.is_blocked,
                'status': env.objectValues('Workitem')[-1].activity_id
            }
            envelope_data = {}

            if not fields:
                fields = default_props.keys()

            for field in fields:
                if field == 'files':
                    envelope_data['files'] = self.get_files(env)
                elif field in default_props.keys():
                    envelope_data[field] = default_props.get(field)

            if envelope_data:
                results.append(envelope_data)

        return json.dumps(results, indent=4)
