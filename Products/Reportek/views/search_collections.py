from base_admin import BaseAdmin


class SearchCollections(BaseAdmin):
    """ SearchCollections view """

    def create_envelopes(self):
        obligations = self.request.get('obligations', [])
        countries = self.request.get('countries', [])
        user = self.request.get('username', '')
        title = self.request.get('title', '')
        year = self.request.get('year', '')

        for brain in self.search_catalog(obligations,
                                         countries,
                                         role='',
                                         users=user):
            collection = brain.getObject()
            print '<li>Creating in: <a href="%s">%s</a></li>' % (
                brain.getPath(), brain.getPath())

            collection.manage_addProduct['Reportek'].manage_addEnvelope(
                title, descr='', year=year,
                endyear='', partofyear='Whole Year', locality='')
