from base_admin import BaseAdmin
import Zope2

class WrongCountry(BaseAdmin):

    def _top_collections(self):
        app = Zope2.bobo_application()
        return app.objectValues('Report Collection')

    def _wrong_country(self, meta_type):
        wrongs = []
        for top_coll in self._top_collections():
            top_country = top_coll.country
            subItems = self.context.Catalog(
                meta_type=meta_type,
                path=top_coll.absolute_url(True))
            for brain in subItems:
                if brain.country != top_country:
                    wrongs.append({
                        'url': brain.getURL(),
                        'title': brain.title,
                        'country': brain.country,
                        'topCountry': top_country
                    })
        return wrongs

    def collections(self):
        return self._wrong_country('Report Collection')

    def envelopes(self):
        return self._wrong_country('Report Envelope')
