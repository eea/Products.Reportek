import json
import datetime
from DateTime import DateTime
from Products.Five import BrowserView


class ReportekApi(BrowserView):
    """ """

    def parse_date(self, value):
        if value:
            try:
                return datetime.datetime.strptime(value, '%Y-%m-%d')
            except Exception:
                return None

    def search_envelopes(self, obligation, released=True, rejected=False,
                         start_date=None, end_date=None):
        results = []
        start_date = self.parse_date(start_date)
        end_date = self.parse_date(end_date)
        if start_date and end_date:
            reportingdate = {
                'query': (DateTime(start_date), DateTime(end_date)),
                'range': 'min:max'
            }
        elif start_date:
            reportingdate = {
                'query': DateTime(start_date),
                'range': 'min'
            }
        elif end_date:
            reportingdate = {
                'query': DateTime(end_date),
                'range': 'max'
            }
        else:
            reportingdate = None

        s_query = {
            'meta_type': 'Report Envelope',
            'dataflow_uris': obligation,
            'released': released
        }
        if reportingdate:
            s_query['reportingdate'] = reportingdate

        brains = self.context.Catalog(**s_query)
        for brain in brains:
            env = brain.getObject()
            envelope_properties = {
                'url': env.absolute_url(0),
                'title': env.title,
                'description': env.descr,
                'dataflow_uris': env.dataflow_uris if isinstance(env.dataflow_uris, list) else list(env.dataflow_uris),
                'country': env.country,
                'country_name': env.getCountryName(),
                'country_code': env.getCountryCode(),
                'locality': env.locality,
                'isreleased': env.released,
                'released': env.reportingdate.HTML4(),
                'startyear': env.year,
                'endyear': env.endyear,
                'partofyear': env.partofyear,
                'is_blocked': env.is_blocked
            }
            envelope_properties['id'] = getattr(env, 'company_id', env.id)

            documents = []
            for doc in env.objectValues('Report Document'):
                if doc.get_accept_time() is not None:
                    accepttime = doc.get_accept_time().HTML4()
                else:
                    accepttime = ''

                doc_properties = {
                    'id': doc.id,
                    'title': doc.title,
                    'content_type': doc.content_type,
                    'xml_schema': doc.xml_schema_location,
                    'upload_time': doc.upload_time().HTML4(),
                    'accept_time': accepttime,
                }

                documents.append(doc_properties)

            envelope_properties['files'] = documents

            if (rejected is True and env.is_blocked) or rejected is False:
                results.append(envelope_properties)

        return json.dumps(results, indent=4)

    def get_released_envelopes(self, obligation, start_date=None, end_date=None):
        """
        Get the released envelopes for a given obligation.
        Method used by FDB/ODB.
        """

        return self.search_envelopes(obligation, start_date=start_date,
                                     end_date=end_date)

    def get_unreleased_envelopes(self, obligation, start_date=None, end_date=None):
        """
        Get the un-released envelopes for a given obligation.
        Method used by FDB/ODB.
        """

        return self.search_envelopes(obligation, released=False,
                                     start_date=start_date, end_date=end_date)

    def get_rejected_envelopes(self, obligation, start_date=None, end_date=None):
        """
        Get the rejected envelopes for a given obligation.
        If envelope contains blocker feedback, then it is rejected.
        Method used by FDB/ODB.
        """

        return self.search_envelopes(obligation, rejected=True,
                                     start_date=start_date, end_date=end_date)

    def collections_json(self):
        """ Returns a JSON with some basic Collections information
        """
        BASIC_DATA = [
            'title',
            'company_id',
        ]
        results = []
        query = {
            'meta_type': 'Report Collection'
        }
        brains = self.context.Catalog(**query)
        for brain in brains:
            coll = brain.getObject()
            exp_data = {}
            exp_data['path'] = brain.getPath()
            for data in BASIC_DATA:
                exp_data[data] = getattr(coll, data, None)
            results.append(exp_data)

        self.request.RESPONSE.setHeader("Content-Type", "application/json")
        return json.dumps(results, indent=4)
