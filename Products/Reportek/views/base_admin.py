import json
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

    def get_country_code(self, countryname):
        c_codes = [c.get('iso') for c in self.localities_rod
                   if c['name'] == countryname]
        if c_codes:
            return c_codes[-1]

    def get_obligations(self):
        return {o['PK_RA_ID']: o['uri'] for o
                in self.dataflow_rod}

    def get_obligations_title(self):
        dataflow_rod = self.dataflow_rod
        return {o['uri']: o['TITLE'] for o in dataflow_rod}

    def get_roles(self):
        app = self.context.getPhysicalRoot()
        return sorted(list(app.userdefined_roles()))

    def get_raw_rod_obligations(self):
        """ Returns a sorted list of obligations from ROD
        """
        dataflow_rod = self.dataflow_rod
        data = []

        if dataflow_rod:
            data = sorted(dataflow_rod, key=itemgetter('SOURCE_TITLE'))

        return data

    def get_rod_obligations(self):
        """ Get all activities from ROD """
        data = self.get_raw_rod_obligations()
        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        legal_instruments = sorted(obligations.keys())

        return {'legal_instruments': legal_instruments,
                'obligations': obligations}

    def get_assigned_rod_obligations(self):
        """ Returns activities that have already been assigned to collections or
            envelopes and that exist in ROD
        """
        data = self.get_raw_rod_obligations()
        obligations = defaultdict(list)
        engine = getattr(self.context, constants.ENGINE_ID)
        unique_uris = engine.getUniqueValuesFor('dataflow_uris')
        obligations = defaultdict(list)
        for obl in data:
            if obl.get('uri') in unique_uris:
                obligations[obl['SOURCE_TITLE']].append(obl)

        legal_instruments = sorted(obligations.keys())

        return {
            'legal_instruments': legal_instruments,
            'obligations': obligations
        }

    def search_catalog(self, obligations, countries, role, users=[]):
        if len(countries) == len(self.localities_rod):
            country_codes = None
        else:
            country_codes = self.get_country_codes(countries)

        query = {'meta_type': 'Report Collection'}

        if role:
            query['local_unique_roles'] = role
        if country_codes:
            query['country'] = country_codes
        if obligations:
            if not isinstance(obligations, list):
                obligations = [obligations]
            df_uris = [self.get_obligations()[obl] for obl in obligations]
            query['dataflow_uris'] = df_uris
        if users:
            query['local_defined_users'] = users

        return self.context.Catalog(query)

    def get_collections(self):
        obligations = self.request.get('obligations', [])
        countries = self.request.get('countries', [])
        search_type = self.request.get('search_type')
        entity = self.request.get('username', '')
        match_groups = []

        if search_type == 'groups':
            entity = self.request.get('groupsname')
            use_subgroups = self.request.get('use-subgroups')
            if use_subgroups:
                match_groups = use_subgroups.split(',')
                entity = match_groups

        if self.request.get('btn.find_collections', False):
            entity = ''

        records = []
        brains = self.search_catalog(obligations,
                                     countries,
                                     role='',
                                     users=entity)
        for brain in brains:
            col_obligations = []
            for uri in list(brain.dataflow_uris):
                try:
                    title = self.get_obligations_title()[uri]
                except KeyError:
                    title = 'Unknown/Deleted obligation'
                col_obligations.append({
                    'uri': uri,
                    'title': title
                })
            col_obligations.sort(key=itemgetter('title'))
            collection = {
                'path': brain.getPath(),
                'country': brain.getCountryName,
                'obligations': col_obligations,
                'roles': brain.local_defined_roles,
                'title': brain.title
            }

            if match_groups:
                c_code = self.get_country_code(brain.getCountryName).lower()
                c_codes = [c_code]
                c_exc = {'gb': 'uk',
                         'gr': 'el'}.get(c_code)
                if c_exc:
                    c_codes.append(c_exc)

                for code in c_codes:
                    group = self.request.get('groupsname') + '-' + code
                    if group in match_groups:
                        collection['matched_group'] = group
                        break

            records.append(collection)

        records.sort(key=itemgetter('path'))
        return records

    def api_get_collections(self):

        return json.dumps({"data": list(self.get_collections())})

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

    def get_acl_users(self):
        pas = getattr(self.context, 'acl_users')
        if pas:
            ldapmultiplugin = getattr(pas, 'ldapmultiplugin')
            if ldapmultiplugin:
                return getattr(ldapmultiplugin, 'acl_users')

    def search_ldap_groups(self, term):
        acl_users = self.get_acl_users()
        groups = acl_users.searchGroups(cn=term)

        if groups:
            group_list = {group.get('cn'): group for group in groups}.values()
            group_list.sort(key=itemgetter('cn'))
            return group_list
