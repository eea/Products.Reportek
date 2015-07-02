from collections import defaultdict
from operator import itemgetter
from Products.Five import BrowserView

from Products.Reportek import config, constants


class BaseAdmin(BrowserView):
    """ Base view for users administration """

    def __init__(self, *args, **kwargs):
        super(BaseAdmin, self).__init__(*args, **kwargs)

        self._localities_rod = None
        self._dataflow_rod = None

    def __call__(self, *args, **kwargs):
        super(BaseAdmin, self).__call__(*args, **kwargs)

        engine = getattr(self.context, constants.ENGINE_ID)
        deployment_type = engine.getDeploymentType()
        if deployment_type == config.DEPLOYMENT_BDR:
            is_bdr = True
        else:
            is_bdr = False

        return self.index(is_bdr=is_bdr)

    @property
    def localities_rod(self):
        if not self._localities_rod:
            engine = getattr(self.context, constants.ENGINE_ID)
            self._localities_rod = engine.localities_rod()
        return self._localities_rod

    @property
    def dataflow_rod(self):
        if not self._dataflow_rod:
            engine = getattr(self.context, constants.ENGINE_ID)
            self._dataflow_rod = engine.dataflow_rod()
        return self._dataflow_rod

    def get_view(self, view_name):
        """Returns the view coresponding to the view_name"""
        if self.request.QUERY_STRING:
            return view_name + '?' + self.request.QUERY_STRING
        else:
            return view_name

    def get_country_codes(self, countries):
        return [c['uri'] for c
                in self.localities_rod
                if c['iso'] in countries]

    def get_obligations(self):
        return {o['PK_RA_ID']: o['uri'] for o
                in self.dataflow_rod}

    def get_obligations_title(self):
        dataflow_rod = self.dataflow_rod
        return {o['uri']: o['TITLE'] for o in dataflow_rod}

    def get_roles(self):
        app = self.context.getPhysicalRoot()
        return sorted(list(app.userdefined_roles()))

    def get_rod_obligations(self):
        """ Get activities from ROD """

        dataflow_rod = self.dataflow_rod
        data = []

        if dataflow_rod:
            data = sorted(dataflow_rod, key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        legal_instruments = sorted(obligations.keys())

        return {'legal_instruments': legal_instruments,
                'obligations': obligations}

    def search_catalog(self, obligation, countries, role, users=[]):
        country_codes = self.get_country_codes(countries)

        query = {'meta_type': 'Report Collection'}

        if role:
            query['local_unique_roles'] = role
        if country_codes:
            query['country'] = country_codes
        if obligation:
            query['dataflow_uris'] = self.get_obligations()[obligation]
        if users:
            query['local_defined_users'] = users

        return self.context.Catalog(query)

    def get_collections(self):
        obligation = self.request.get('obligation', '')
        countries = self.request.get('countries', [])
        search_type = self.request.get('search_type')
        entity = self.request.get('username', '')

        if search_type == 'groups':
            entity = self.request.get('groupsname')

        if self.request.get('btn.find_collections', False):
            entity = ''

        records = []
        brains = self.search_catalog(obligation,
                                     countries,
                                     role='',
                                     users=entity)
        for brain in brains:

            obligations = []
            for uri in list(brain.dataflow_uris):
                try:
                    title = self.get_obligations_title()[uri]
                except KeyError:
                    title = 'Unknown/Deleted obligation'
                obligations.append({
                    'uri': uri,
                    'title': title
                })

            records.append({
                'path': brain.getPath(),
                'country': brain.getCountryName,
                'obligations': obligations,
                'roles': brain.local_defined_roles,
                'title': brain.title
            })

        records.sort(key=itemgetter('country'))
        return records

    def get_breadcrumbs(self):
        breadcrumbs = []

        for item in self.request.get('PARENTS'):
            crumb = {
                'title': item.title_or_id,
                'url': item.absolute_url(),
            }
            breadcrumbs.append(crumb)

        current = self.request.getURL()
        crumb = {
            'title': current.split('/')[-1],
            'url': ''
        }

        breadcrumbs.insert(0, crumb)

        return breadcrumbs
