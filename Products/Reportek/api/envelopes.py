from DateTime import DateTime
from Products.Five import BrowserView
from Products.Reportek.constants import ENGINE_ID
from ZODB.blob import POSKeyError
from Products.Reportek.blob import StorageError
import datetime
import json


class EnvelopesAPI(BrowserView):
    """Envelopes API"""

    AVAILABLE_FILTERS = {
        'url': {
            'catalog_mapping': '',
            'help_text': 'Return all envelopes with specified url. E.g.: '
                         '/api/envelopes?obligations=696&url=<url>',
        },
        'title': {
            'catalog_mapping': 'title',
            'help_text': 'Return all envelopes with specified title. E.g.: '
                         '/api/envelopes?obligations=696&title=<title>',
        },
        'description': {
            'catalog_mapping': 'description',
            'help_text': 'Return all envelopes with specified description. '
                         'E.g.: /api/envelopes?obligations=696'
                         '&description=<description>',
        },
        'fields': {
            'catalog_mapping': '',
            'help_text': 'Return only the specified fields for envelopes. '
                         'E.g.: /api/envelopes?obligations=696&fields=title,'
                         'description,url,files',
        },
        'hide_help': {
            'catalog_mapping': '',
            'help_text': 'Hide the additional help information from the results',
        },
        'countryCode': {
            'catalog_mapping': '',
            'help_text': 'Return all envelopes related to specified '
                         'countryCode. E.g.: /api/envelopes?obligations='
                         '696&countryCode=RO',
        },
        'isReleased': {
            'catalog_mapping': 'released',
            'help_text': 'Return all released(1) or unreleased(0) envelopes.'
                         'E.g.: /api/envelopes?obligations=696'
                         '&isReleased=1',
        },
        'reportingDate': {
            'catalog_mapping': 'reportingdate',
            'help_text': 'Return all envelopes with the specified '
                         'reportingDate with format YYYY-MM-DD. E.g.: '
                         '/api/envelopes?obligations=696'
                         '&reportingDate=2015-01-15',
        },
        'modifiedDate': {
            'catalog_mapping': 'bobobase_modification_time',
            'help_text': 'Return all envelopes with the specified '
                         'modifiedDate with format YYYY-MM-DD. E.g.: '
                         '/api/envelopes?obligations=696'
                         '&modifiedDate=2015-01-15',
        },
        'modifiedDateStart': {
            'catalog_mapping': 'bobobase_modification_time',
            'help_text': 'Return all envelopes that have a '
                         'modifiedDate starting from the specified '
                         'modifiedDateStart with format YYYY-MM-DD. E.g.: '
                         '/api/envelopes?obligations=696'
                         '&modifiedDateStart=2015-01-15',
        },
        'modifiedDateEnd': {
            'catalog_mapping': 'bobobase_modification_time',
            'help_text': 'Return all envelopes that have a '
                         'modifiedDate before the specified '
                         'modifiedDateEnd with format YYYY-MM-DD. E.g.: '
                         '/api/envelopes?obligations=696'
                         '&modifiedDateEnd=2015-01-15',
        },
        'periodStartYear': {
            'catalog_mapping': '',
            'help_text': 'Return all envelopes with specified start year. E.g.'
                         ': /api/envelopes?obligations=696'
                         '&periodStartYear=2014',
        },
        'periodEndYear': {
            'catalog_mapping': '',
            'help_text': 'Return all envelopes with specified end year. E.g.: '
                         '/api/envelopes?obligations=696'
                         '&periodEndYear=2014',
        },
        'periodDescription': {
            'catalog_mapping': 'partofyear',
            'help_text': 'Return all envelopes with specified period '
                         'description. E.g.: /api/envelopes?obligations='
                         '696&periodDescription=Whole%20Year',
        },
        'obligations': {
            'catalog_mapping': '',
            'help_text': 'Return all envelopes with specified obligation(s). '
                         'E.g.: /api/envelopes?obligations=696,701',
        },
        'isBlockedByQCError': {
            'catalog_mapping': '',
            'help_text': 'Return all envelopes that are blocked by a QC Error.'
                         ' E.g.: /api/envelopes?obligations=696'
                         '&isBlockedByQCError=1',
        },
        'status': {
            'catalog_mapping': '',
            'help_text': 'Return all envelopes with specified status. E.g.: '
                         '/api/envelopes?obligations=696'
                         '&status=Draft',
        },
    }

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
        catalog_field_map = {}
        for c_filter in self.AVAILABLE_FILTERS.keys():
            c_mapping = self.AVAILABLE_FILTERS[c_filter].get('catalog_mapping')
            if c_mapping:
                catalog_field_map[c_filter] = c_mapping
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

                    if param in ['reportingDate', 'modifiedDate']:
                        startd = datetime.datetime.strptime(value, '%Y-%m-%d')
                        endd = startd + datetime.timedelta(days=1)
                        value = {
                            'query': (DateTime(startd), DateTime(endd)),
                            'range': 'min:max'
                        }

                    if param in ['modifiedDateStart', 'modifiedDateEnd']:
                        val = query.get(c_idx)
                        upd_start = None
                        upd_end = None
                        v_date = datetime.datetime.strptime(value, '%Y-%m-%d')
                        if param.endswith('Start'):
                            upd_start = v_date
                            d_query = DateTime(upd_start)
                            d_range = 'min'
                        elif param.endswith('End'):
                            upd_end = v_date
                            d_query = DateTime(upd_end)
                            d_range = 'max'

                        if val:
                            d_range = 'min:max'
                            if upd_start:
                                d_query = (DateTime(upd_start), val['query'])
                            elif upd_end:
                                d_query = (val['query'], DateTime(upd_end))
                        value = {
                            'query': d_query,
                            'range': d_range
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
        a_filters = [{a_f: self.AVAILABLE_FILTERS[a_f].get('help_text')}
                     for a_f in self.AVAILABLE_FILTERS]
        data = {
            'envelopes': results,
            'errors': errors,
        }
        fields = self.request.form.get('fields')

        if 'hide_help' not in self.request.form.keys():
            data['available_filters'] = a_filters
            data['available_fields'] = self.AVAILABLE_FILTERS.keys() + ['files', 'history']

        valid_catalog_filters = [
            'isReleased',
            'reportingDate',
            'obligations',
            'periodDescription',
            'modifiedDate',
            'modifiedDateStart',
            'modifiedDateEnd'
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
                    'modifiedDate': brain.bobobase_modification_time.HTML4(),
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
