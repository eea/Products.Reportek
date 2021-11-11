from operator import itemgetter
from base_admin import BaseAdmin


class WrongCountry(BaseAdmin):

    def _top_collections(self):
        app = self.context.getPhysicalRoot()
        return app.objectValues('Report Collection')

    def _wrong_country(self, meta_type):
        results = []
        for collection in self._top_collections():

            top_country = collection.country

            for brain in self.context.Catalog(
                    meta_type=meta_type,
                    path=collection.absolute_url(True)):

                if brain.country != top_country:
                    results.append({
                        'url': brain.getURL(),
                        'title': brain.title,
                        'country': brain.country,
                        'topCountry': top_country
                    })

        results.sort(key=itemgetter('title'))
        return results

    def collections(self):
        return self._wrong_country('Report Collection')

    def envelopes(self):
        return self._wrong_country('Report Envelope')
