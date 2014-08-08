from collections import defaultdict
from operator import itemgetter
from Products.Five import BrowserView
import Zope2


class BaseAdmin(BrowserView):
    """ Base view for users administration """

    def get_view(self, view_name):
        """Returns the view coresponding to the view_name"""
        if self.context.REQUEST.QUERY_STRING:
            return view_name + '?' + self.context.REQUEST.QUERY_STRING
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
