from collections import defaultdict
from operator import itemgetter
from Products.Five import BrowserView
import Zope2

from Products.Reportek import config

class BaseAdmin(BrowserView):
    """ Base view for users administration """

    def __call__(self, *args, **kwargs):
        super(BaseAdmin, self).__call__(*args, **kwargs)

        engine = self.context.ReportekEngine.getDeploymentType()
        if engine == config.DEPLOYMENT_BDR:
            is_bdr = True
        else:
            is_bdr = False

        return self.index(is_bdr=is_bdr)

    def get_view(self, view_name):
        """Returns the view coresponding to the view_name"""
        if self.request.QUERY_STRING:
            return view_name + '?' + self.request.QUERY_STRING
        else:
            return view_name

    def get_country_codes(self, countries):
        return [c['uri'] for c
                in self.context.localities_rod()
                if c['iso'] in countries]

    def get_obligations(self):
        return {o['PK_RA_ID']: o['uri'] for o
                in self.context.dataflow_rod()}

    def get_obligations_title(self):
        return {o['uri']: o['TITLE'] for o
                in self.context.dataflow_rod()}

    def get_roles(self):
        app = Zope2.bobo_application()
        return sorted(list(app.userdefined_roles()))

    def get_rod_obligations(self):
        """ Get activities from ROD """
        data = sorted(self.context.dataflow_rod(),
                      key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        return {'legal_instruments': sorted(obligations.keys()),
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
        username = self.request.get('username', '')

        records = []
        for brain in self.search_catalog(obligation,
                                         countries,
                                         role='',
                                         users=username):

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
