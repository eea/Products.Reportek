from base_admin import BaseAdmin

class Statistics(BaseAdmin):
    """ View for statistics page"""

    def totals_per_type(self):
        total = {}
        total['envelopes'] = len(self.context.Catalog(meta_type='Report Envelope'))
        total['envelopes_released'] = len(self.context.Catalog(meta_type='Report Envelope', released=True))
        total['files'] = len(self.context.Catalog(meta_type='Report Document'))
        total['feedbacks'] = len(self.context.Catalog(meta_type='Report Feedback'))
        total['hyperlinks'] = len(self.context.Catalog(meta_type='Report Hyperlink'))
        total['referrals'] = len(self.context.Catalog(meta_type='Repository Referral'))
        return total

    def deliveries_per_country(self):
        all_unique_country_fields = self.context.Catalog.uniqueValuesFor('country')
        country_urls = [ c for c in all_unique_country_fields
                   if c and c.startswith('http://rod.eionet.europa.eu/spatial') ]
        localities = self.context.localities_dict()
        country_deliveries = []
        for country_url in country_urls:
            if country_url in localities:
                # TODO try a named tupple here
                country_deliveries.append(
                    {'country': localities[country_url]['name'],
                     'count': len(self.context.Catalog(meta_type="Report Envelope",
                                                       released=True,
                                                       country=country_url))
                    })
        return country_deliveries
