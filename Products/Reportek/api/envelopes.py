from DateTime import DateTime
from Products.Five import BrowserView
from Products.Reportek.constants import ENGINE_ID
from ZODB.blob import POSKeyError
from Products.Reportek.blob import StorageError
import datetime
import json


class EnvelopesAPI(BrowserView):
    """Envelopes API"""
    MAX_RESULTS = 5000
    AVAILABLE_FILTERS = {
        'url': {
            'catalog_mapping': 'path',
        },
        'title': {
            'catalog_mapping': 'title',
        },
        'description': {
            'catalog_mapping': 'Description',
        },
        'countryCode': {
            'catalog_mapping': 'country',
        },
        'isReleased': {
            'catalog_mapping': 'released',
        },
        'reportingDate': {
            'catalog_mapping': 'reportingdate',
        },
        'reportingDateStart': {
            'catalog_mapping': 'reportingdate',
        },
        'reportingDateEnd': {
            'catalog_mapping': 'reportingdate',
        },
        'modifiedDate': {
            'catalog_mapping': 'bobobase_modification_time',
        },
        'modifiedDateStart': {
            'catalog_mapping': 'bobobase_modification_time',
        },
        'modifiedDateEnd': {
            'catalog_mapping': 'bobobase_modification_time',
        },
        'periodStartYear': {
            'catalog_mapping': '',
        },
        'periodEndYear': {
            'catalog_mapping': '',
        },
        'periodDescription': {
            'catalog_mapping': 'partofyear',
        },
        'obligations': {
            'catalog_mapping': '',
        },
        'isBlockedByQCError': {
            'catalog_mapping': '',
        },
        'status': {
            'catalog_mapping': '',
        },
        'statusDate': {
            'catalog_mapping': '',
        },
        'statusDateStart': {
            'catalog_mapping': '',
        },
        'statusDateEnd': {
            'catalog_mapping': '',
        },
        'creator': {
            'catalog_mapping': '',
        },
        'hasUnknownQC': {
            'catalog_mapping': '',
        }
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

    def get_country_uri(self, country_code):
        """Return country uri from country code."""
        engine = getattr(self.context, ENGINE_ID)
        localities_table = engine.localities_table()
        country_uri = [loc.get('uri') for loc in localities_table
                       if country_code.upper() == loc.get('iso')]
        if country_uri:
            return country_uri[0]

    def get_hostname(self):
        """Extract hostname in virtual-host-safe manner."""

        if "HTTP_X_FORWARDED_HOST" in self.request.environ:
            # Virtual host
            host = self.request.environ["HTTP_X_FORWARDED_HOST"]
        elif "HTTP_HOST" in self.request.environ:
            # Direct client request
            host = self.request.environ["HTTP_HOST"]
        else:
            return None

        return host

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
                        'archived_files': archived_files
                    }

                    documents.append(doc_properties)

        return documents_data

    def build_catalog_query(self, valid_filters, fed_params):
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
            if fed_params.get(param):
                if param != 'obligations':
                    c_idx = catalog_field_map.get(param)
                    value = fed_params.get(param)

                    if param == 'isReleased':
                        value = int(value)

                    if param in ['reportingDate', 'modifiedDate']:
                        startd = datetime.datetime.strptime(value, '%Y-%m-%d')
                        endd = startd + datetime.timedelta(days=1)
                        value = {
                            'query': (DateTime(startd), DateTime(endd)),
                            'range': 'min:max'
                        }
                    if param == 'url':
                        value = value.split(self.get_hostname())[-1]
                    if param == 'countryCode':
                        value = self.get_country_uri(value)
                    if param in ['modifiedDateStart', 'modifiedDateEnd', 'reportingDateStart', 'reportingDateEnd']:
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
                    obligations = fed_params.get(param)
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

        def getbID(b):
            return int(b.id)

        brains = list(self.context.Catalog(**query))

        if children_type == 'Workitem':
            brains.sort(key=getbID)
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

    def is_in_range(self, date_value, date_start, date_end):
        if date_start and not date_end:
            return date_start >= date_value
        elif date_end and not date_start:
            return date_end >= date_value
        else:
            return date_start <= date_value <= date_end

    def is_filtered_out(self, default_props, additional_filters, fed_params):
        """Return True if value is not compliant with user's filters."""
        datev = default_props.get('statusDate')
        if datev:
            datev = datetime.datetime.strptime(str(datev)[:10], '%Y-%m-%d')
        sdatesrange = ('statusDateStart' in additional_filters or
                       'statusDateEnd' in additional_filters)
        if sdatesrange:
            sds = None
            sde = None
            sds = fed_params.get('statusDateStart')
            if sds:
                sds = datetime.datetime.strptime(sds, '%Y-%m-%d')
            sde = fed_params.get('statusDateEnd')
            if sde:
                sde = datetime.datetime.strptime(sde, '%Y-%m-%d')
            elif sds:
                sde = datetime.datetime.now()

            if sds or sde:
                if not self.is_in_range(datev, sds, sde):
                    return True

        for afilter in additional_filters:
            afilter_v = fed_params.get(afilter)
            if afilter_v and afilter not in ['statusDateStart', 'statusDateEnd']:
                if afilter == 'statusDate':
                    startd = datetime.datetime.strptime(afilter_v, '%Y-%m-%d')
                    endd = startd + datetime.timedelta(days=1)
                    if not self.is_in_range(datev, startd, endd):
                        return True
                elif afilter_v.upper() != str(default_props.get(afilter)).upper():
                    return True

    def get_envelope_history(self, path):
        """Return a the envelope's workflow history."""
        result = []
        wk_brains = self.get_env_children(path, 'Workitem')
        for brain in wk_brains:
            blocker = brain.blocker
            if not blocker and blocker is not False:
                blocker = None
            title, status = brain.title.split(', status: ')

            result.append({
                'activity_id': brain.activity_id,
                'blocker': blocker,
                'id': brain.id,
                'title': title,
                'modified': brain.bobobase_modification_time.HTML4(),
                'activity_status': status
            })

        return result

    def has_unknown_qc(self, path):
        """Return true if has a AutomaticQA feedback with UNKNOWN QC."""
        fb_brains = self.get_env_children(path, 'Report Feedback')
        aqc_brains = [brain for brain in fb_brains
                      if brain.title.startswith('AutomaticQA')]
        VALID_FB_STATUSES = [
            'INFO',
            'SKIPPED',
            'OK',
            'WARNING',
            'ERROR',
            'BLOCKER'
        ]

        for aqc in aqc_brains:
            fb_status = aqc.feedback_status
            if fb_status not in VALID_FB_STATUSES:
                return 1

        return 0

    def get_default_props(self, brain):
        """Return default envelope's properties."""
        years = brain.years
        startyear = years[0] if years else ''
        endyear = years[-1] if years and len(years) > 1 else ''
        obls = [obl.split('http://rod.eionet.europa.eu/obligations/')[-1]
                for obl in brain.dataflow_uris]
        return {
            'url': brain.getURL(),
            'title': brain.title,
            'description': brain.Description,
            'countryCode': self.getCountryCode(brain.country),
            'isReleased': brain.released,
            'reportingDate': brain.reportingdate.HTML4(),
            'modifiedDate': brain.bobobase_modification_time.HTML4(),
            'obligations': obls,
            'periodStartYear': startyear,
            'periodEndYear': endyear,
            'periodDescription': brain.partofyear,
        }

    def get_additional_props(self, brain):
        """Return additional envelope properties."""
        last_status_d = None
        wk_brains = self.get_env_children(brain.getPath(), 'Workitem')
        actors = [wk.actor for wk in wk_brains if wk.activity_id == 'Draft']
        creator = None
        if actors:
            creator = actors[-1]

        if brain.activation_log:
            last_status_d = brain.activation_log[-1].get('start')
            if last_status_d:
                last_status_d = datetime.datetime.fromtimestamp(last_status_d)
                last_status_d = DateTime(last_status_d).HTML4()

        return {
            'isBlockedByQCError': self.is_env_blocked(wk_brains),
            'status': wk_brains[-1].activity_id,
            'statusDate': last_status_d,
            'creator': creator or 'Not assigned',
            'hasUnknownQC': self.has_unknown_qc(brain.getPath())
        }

    def get_envelopes(self):
        """Return envelopes."""
        results = []
        errors = []
        data = {
            'envelopes': results,
            'errors': errors,
        }
        fields = self.request.form.get('fields')

        valid_catalog_filters = [
            'url',
            'countryCode',
            'isReleased',
            'reportingDate',
            'reportingDateStart',
            'reportingDateEnd',
            'obligations',
            'periodDescription',
            'modifiedDate',
            'modifiedDateStart',
            'modifiedDateEnd',
        ]

        fed_params = {p: self.request.form.get(p)
                      for p in self.AVAILABLE_FILTERS
                      if self.request.form.get(p)}
        if not fed_params:
            m_date_start = DateTime() - 90
            fed_params['modifiedDateStart'] = m_date_start.strftime('%Y-%m-%d')

        if fields:
            fields = fields.split(',')

        query = self.build_catalog_query(valid_catalog_filters, fed_params)
        brains = self.context.Catalog(**query)
        if len(brains) > self.MAX_RESULTS:
            error = 'There are too many possible results for your query. '\
                    'Please use additional filters.'
            errors.append({'title': 'Too many results',
                           'description': error
                           })
        else:
            additional_filters = [key for key in self.AVAILABLE_FILTERS.keys()
                                  if key not in valid_catalog_filters]
            for brain in brains:
                default_props = self.get_default_props(brain)
                envelope_data = {}
                if not fields:
                    fields = default_props.keys()
                additional_p_fields = [param for param in fields
                                       if param not in default_props]
                additional_p_filters = [param for param in fed_params.keys()
                                        if param not in default_props]
                if additional_p_fields or additional_p_filters:
                    additional_props = self.get_additional_props(brain)
                    default_props.update(additional_props)

                if self.is_filtered_out(default_props, additional_filters, fed_params):
                    continue

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
        self.request.RESPONSE.setHeader("Content-Type", "application/json")
        return json.dumps(data, indent=4)
