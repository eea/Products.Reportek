from collections import defaultdict
from operator import itemgetter
from Products.Five import BrowserView
from zope.browsermenu.menu import getMenu
import json

from Products.Reportek import config, constants
from Products.Reportek.catalog import searchResults


class BaseAdmin(BrowserView):
    """ Base view for users administration """

    def __init__(self, *args, **kwargs):
        super(BaseAdmin, self).__init__(*args, **kwargs)

        self._localities_rod = None
        self._dataflow_rod = None

    def __call__(self, *args, **kwargs):
        super(BaseAdmin, self).__call__(*args, **kwargs)

        deployment_type = self.get_deployment()
        if deployment_type == config.DEPLOYMENT_BDR:
            is_bdr = True
        else:
            is_bdr = False

        return self.index(is_bdr=is_bdr)

    def get_deployment(self):
        engine = getattr(self.context, constants.ENGINE_ID)
        return engine.getDeploymentType()

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
        engine = getattr(self.context, constants.ENGINE_ID)
        deployment_type = engine.getDeploymentType()
        l_roles = sorted(list(app.userdefined_roles()))
        if deployment_type == config.DEPLOYMENT_BDR:
            # For BDR, Reporters actually have local 'Owner' Roles
            l_roles = ['Reporter (Owner)' if role == 'Reporter' else role
                       for role in l_roles]
        return l_roles

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

    def search_catalog(self, obligations, countries, role, users=None, path=None):
        admin_check = False
        deployment_type = self.get_deployment()
        if deployment_type == config.DEPLOYMENT_BDR:
            admin_check = True

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
            query['dataflow_uris'] = obligations
        if users:
            query['local_defined_users'] = users
        if path:
            query['path'] = path

        return searchResults(self.context.Catalog, query,
                             admin_check=admin_check)

    def get_collections(self):
        obligations = self.request.get('dataflow_uris', [])
        countries = self.request.get('countries', [])
        search_type = self.request.get('search_type')
        entity = self.request.get('username', '')
        path = self.request.get('path_filter', '')
        use_path = None
        parts = None
        match_groups = []

        if search_type == 'groups':
            entity = self.request.get('groupsname')
            use_subgroups = self.request.get('use-subgroups')
            if use_subgroups:
                match_groups = use_subgroups.split(',')
                entity = match_groups

        if self.request.get('btn.find_collections', False):
            entity = ''

        if path:
            parts = path.split('/')
            if path.startswith('http') or path.startswith('/'):
                use_path = path
                if path.startswith('http'):
                    use_path = '/{0}'.format('/'.join(parts[3:]))
                parts = None
            else:
                parts = path

        records = []
        brains = self.search_catalog(obligations,
                                     countries,
                                     role='',
                                     users=entity,
                                     path=use_path)

        for brain in brains:
            col_obligations = []
            if not parts or parts in brain.getPath():
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
                l_roles = brain.local_defined_roles
                if config.REPORTEK_DEPLOYMENT == config.DEPLOYMENT_BDR:
                    # For BDR, Reporters actually have local 'Owner' Roles
                    for user in l_roles.keys():
                        l_roles[user] = ['Reporter (Owner)' if role == 'Owner'
                                         else role for role in l_roles[user]]
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

    def get_available_menu_items(self):
        return getMenu('reportek_utilities', self.context, self.request)

