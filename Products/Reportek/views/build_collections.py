from collections import defaultdict
from operator import itemgetter

from base_admin import BaseAdmin
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
        countries = self.request.form.pop('countries', [])
        title = self.request.form.pop('ctitle', '')
        obligations = self.request.form.pop('dataflow_uris', [])

        collection_id = self.request.form.pop('cid', '')
        allow_collections = int(self.request.form.pop('allow_collections', 0))
        allow_envelopes = int(self.request.form.pop('allow_envelopes', 0))
        allow_referrals = int(self.request.form.pop('allow_referrals', 0))
        year = self.request.form.pop('year', '')
        endyear = self.request.form.pop('endyear', '')
        partofyear = self.request.form.pop('partofyear', '')

        if not countries:
            err = "No country selected! Please select at least one country."
            messages['fail'].append(err)
            return self.index(messages=messages)
        # get ReportekEngine object
        engine = self.context.unrestrictedTraverse('/'+ENGINE_ID)

        for iso in countries:
            # get country uri
            country = filter(lambda c: c.get('iso') == iso, self.localities_rod)[0]
            if country:
                target_path = str(country['iso'].lower())
                try:
                    if pattern:
                        pattern = engine.clean_pattern(pattern)
                        target_path = '/'.join([str(country['iso'].lower()), pattern])

                    target = engine.getPhysicalRoot().restrictedTraverse(target_path)
                    kwargs = {
                        'allow_collections': allow_collections,
                        'allow_envelopes': allow_envelopes,
                        'allow_referrals': allow_referrals,
                        'id': collection_id
                    }
                    target.manage_addCollection(title, '', year, endyear,
                                                partofyear, country['uri'], '',
                                                obligations, **kwargs)
                    messages['success'].append(country['name'])
                except KeyError:
                    err = "{0}: the specified path does not exist [{1}]".format(
                        country['name'], target_path)
                    messages['fail'].append(err)
        return self.index(messages=messages)
