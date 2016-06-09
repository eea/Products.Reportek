from DateTime import DateTime
from Products.Five import BrowserView
from Products.Reportek.constants import ENGINE_ID
from ZODB.blob import POSKeyError
from Products.Reportek.blob import StorageError
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
        errors = []
        documents_data = {
            'documents': documents,
            'errors': errors
        }
        if env_path:
            envelope = self.context.restrictedTraverse(env_path, None)
            if envelope:
                for doc in envelope.objectValues('Report Document'):
                    archived_files = []
                    try:
                        zipfiles = envelope.getZipInfo(doc)
                        for zfile in zipfiles:
                            archived_files.append(zfile)
                    except (POSKeyError, StorageError) as e:
                        errors.append({
                            'title': 'An error occured trying to access file: {}'.format(doc.absolute_url(0)),
                            'description': str(e)
                        })
                    doc_properties = {
                        'url': doc.absolute_url(0),
                        'title': doc.title,
                        'contentType': doc.content_type,
                        'schemaURL': doc.xml_schema_location,
                        'uploadDate': doc.upload_time().HTML4(),
                        'archived_files': archived_files or None
                    }

                    documents.append(doc_properties)

        return documents_data

    def build_catalog_query(self, valid_filters):
        """Return a catalog query dictionary based on query params."""
        catalog_field_map = {
            'title': 'title',
            'isReleased': 'released',
            'reportingDate': 'reportingdate',
            'periodDescription': 'partofyear',
        }

        query = {
            'meta_type': 'Report Envelope'
        }

        for param in valid_filters:
            if self.request.form.get(param):
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

    def get_env_children(self, path, children_type):
        """Return envelope's children of type children_type as brains."""
        query = {
            'path': path,
            'meta_type': children_type,
        }
        brains = self.context.Catalog(**query)

        return brains

    def is_env_blocked(self, wk_brains):
        """Return 1 if envelope is blocked, otherwise 1."""
        qa_wks = [wk for wk in wk_brains if wk.activity_id == 'AutomaticQA']
        if not qa_wks:
            return 0
        else:
            blocker = qa_wks[-1].blocker
            if not blocker:
                return 0
            return 1

    def is_invalid(self, default_props, additional_filters):
        """Return True if filter value is different from env value."""
        for afilter in additional_filters:
            afilter_v = self.request.form.get(afilter)
            if afilter_v and afilter_v != str(default_props.get(afilter)):
                return True

    def get_envelope_history(self, path):
        """Return a the envelope's workflow history."""
        result = []
        wk_brains = self.get_env_children(path, 'Workitem')
        for brain in wk_brains:
            blocker = brain.blocker
            if not blocker and blocker is not False:
                blocker = None
            result.append({
                'activity_id': brain.activity_id,
                'blocker': blocker,
                'id': brain.id,
                'title': brain.title,
                'modified': brain.bobobase_modification_time.HTML4()
            })

        return result

    def get_envelopes(self):
        """Return envelopes."""
        results = []
        errors = []
        data = {
            'envelopes': results,
            'errors': errors
        }
        fields = self.request.form.get('fields')
        valid_catalog_filters = [
            'isReleased',
            'reportingDate',
            'obligations',
            'periodDescription'
        ]

        if not self.request.form.get('obligations'):
            errors.append({
                'title': 'No obligation specified',
                'detail': 'You need to specify the obligations filter. E.g. api/envelopes?obligations=696'
            })
        else:
            if fields:
                fields = fields.split(',')

            query = self.build_catalog_query(valid_catalog_filters)
            brains = self.context.Catalog(**query)
            for brain in brains:
                years = brain.years
                startyear = years[0] if years else ''
                endyear = years[-1] if years and len(years) > 1 else ''
                wk_brains = self.get_env_children(brain.getPath(), 'Workitem')
                default_props = {
                    'url': brain.getURL(),
                    'title': brain.title,
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
                additional_filters = [key for key in default_props.keys()
                                      if key not in valid_catalog_filters]

                if self.is_invalid(default_props, additional_filters):
                    continue

                if not fields:
                    fields = default_props.keys()

                for field in fields:
                    if field == 'files':
                        files_data = self.get_files(brain.getPath())
                        envelope_data['files'] = files_data.get('documents')
                        if files_data.get('errors'):
                            errors += files_data.get('errors', [])
                    elif field == 'history':
                        envelope_data['history'] = self.get_envelope_history(brain.getPath())
                    elif field in default_props.keys():
                        envelope_data[field] = default_props.get(field)

                if envelope_data:
                    results.append(envelope_data)
        return json.dumps(data, indent=4)
