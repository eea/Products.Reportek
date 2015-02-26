import json
from Products.Five import BrowserView

class ReportekApi(BrowserView):
    """ """

    def search_envelopes(self, obligation, released=True, rejected=False):
        results = []

        brains = self.context.Catalog(meta_type='Report Envelope',
                            dataflow_uris=obligation,
                            released=released)
        for brain in brains:
            env = brain.getObject()
            envelope_properties = {
                'url': env.absolute_url(0),
                'title': env.title,
                'description': env.descr,
                'dataflow_uris': env.dataflow_uris,
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

            if hasattr(env, 'company_id'):
                envelope_properties['id'] = env.company_id
            else:
                envelope_properties['id'] = env.id

            documents = []
            for doc in env.objectValues('Report Document'):
                if doc.get_accept_time() is not None:
                    accepttime = doc.get_accept_time().HTML4()
                else: accepttime = ''

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


    def get_released_envelopes(self, obligation):
        """
        Get the released envelopes for a given obligation.
        Method used by FDB/ODB.
        """

        return self.search_envelopes(obligation)


    def get_unreleased_envelopes(self, obligation):
        """
        Get the un-released envelopes for a given obligation.
        Method used by FDB/ODB.
        """

        return self.search_envelopes(obligation, released=False)


    def get_rejected_envelopes(self, obligation):
        """
        Get the rejected envelopes for a given obligation.
        If envelope contains blocker feedback, then it is rejected.
        Method used by FDB/ODB.
        """

        return self.search_envelopes(obligation, rejected=True)
