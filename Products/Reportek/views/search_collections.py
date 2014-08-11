from base_admin import BaseAdmin


class SearchCollections(BaseAdmin):
    """ SearchCollections view """

    def __call__(self, *args, **kwargs):
        result = super(SearchCollections, self).__call__(*args, **kwargs)

        if self.request.get('btn.create'):
            self.create_envelopes()

        return result

    def create_envelopes(self):
        title = self.request.get('title', '')
        year = self.request.get('year', '')
        collections = self.request.get('collections', [])

        for collection in collections:
            obj = self.context.unrestrictedTraverse(collection)
            obj.manage_addProduct['Reportek'].manage_addEnvelope(
                title, descr='', year=year,
                endyear='', partofyear='Whole Year', locality='')
