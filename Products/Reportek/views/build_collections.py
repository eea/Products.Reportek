from base_admin import BaseAdmin
from operator import itemgetter
from collections import defaultdict
from Products.Reportek.constants import ENGINE_ID


class BuildCollections(BaseAdmin):
    """ View for build collections page"""
    def __init__(self, *args, **kwargs):
        super(BuildCollections, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        messages = {'success': [], 'fail': []}

        if self.request.method == 'GET':
            return self.index(messages=messages)

        # get form params
        pattern = self.request.form.pop('pattern', '')
        countries = self.request.form.pop('countries', None)
        title = self.request.form.pop('ctitle', '')
        obl = self.request.form.pop('obligations', [])

        collection_id = self.request.form.pop('cid', '')
        allow_collections = int(self.request.form.pop('allow_collections', 0))
        allow_envelopes = int(self.request.form.pop('allow_envelopes', 1))

        obligations = []
        # adjust obligation to expected format
        for ob in obl:
            ob = filter(lambda c: c.get('PK_RA_ID') == ob, self.dataflow_rod)[0]
            obligations.append(ob.get('uri'))

        # get ReportekEngine object
        engine = self.context.unrestrictedTraverse('/'+ENGINE_ID)

        for iso in countries:
            # get country uri
            country = filter(lambda c: c.get('iso') == iso, self.localities_rod)[0]
            if country:
                target_path = country['iso'].lower()
                try:
                    if pattern:
                        pattern = engine.clean_pattern(pattern)
                        target_path = '/'.join([country['iso'].lower(), pattern])

                    target = engine.getPhysicalRoot().restrictedTraverse(target_path)
                    target.manage_addCollection(
                        title, '', '', '', '', country['uri'], '', obligations,
                        allow_collections=allow_collections,
                        allow_envelopes=allow_envelopes,
                        id=collection_id
                    )
                    messages['success'].append(country['name'])
                except KeyError:
                    err = "{0}: the specified path does not exist [{1}]".format(
                        country['name'], target_path)
                    messages['fail'].append(err)
        return self.index(messages=messages)

    def get_rod_obligations(self):
        """ Get activities from ROD """
        engine = self.context.unrestrictedTraverse('/'+ENGINE_ID)
        unique_uris = engine.getUniqueValuesFor('dataflow_uris')

        dataflow_rod = self.dataflow_rod
        data = []

        if dataflow_rod:
            data = sorted(dataflow_rod, key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            if obl.get('uri') in unique_uris:
                obligations[obl['SOURCE_TITLE']].append(obl)

        legal_instruments = sorted(obligations.keys())

        return {
            'legal_instruments': legal_instruments,
            'obligations': obligations
        }
