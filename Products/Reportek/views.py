import json
from operator import itemgetter
from collections import defaultdict

from Products.Five import BrowserView


class DataSources(BrowserView):

    def get_brains(self):
        """
        Makes the query in catalog and returns the hits
        """
        country_codes = [c['uri'] for c in self.context.localities_rod()
                         if c['iso'] in self.countries_filter()]

        query = {
            'meta_type': 'Report Collection',
            'b_size': self.get_length(),
            'b_start': self.get_start(),
            'sort_order': self.get_order_direction(),

        }
        if country_codes:
            query['country'] = country_codes
        brains = self.context.Catalog(query)
        if self.obligations_filter():
            query['obligations_uri'] = list(self.obligations_filter())

        return brains

    def process_data(self):
        if self.context.REQUEST['REQUEST_METHOD'] == 'GET':
            results = []
            brains = self.get_brains()
            for brain in brains:
                obj = brain.getObject()
                results.append({
                    'short_path': '/' + obj.absolute_url(1),
                    'full_path': obj.absolute_url(0),
                    'last_change': obj.bobobase_modification_time().Date(),
                    'obligations': list(obj.dataflow_uris),
                    'clients': obj.users_with_local_role(self.selected_role())})

            data_to_return = {"recordsTotal": 90, "draw": self.get_draw(),
                              "data": results}
            return json.dumps(data_to_return)

    def get_draw(self):
        return self.context.REQUEST.get('draw')

    def get_start(self):
        return self.context.REQUEST.get('start', '0')

    def get_length(self):
        return self.context.REQUEST.get('length', '10')

    def get_global_search(self):
        return self.context.REQUEST.get('search[value]')

    def get_order_column(self):
        return self.context.REQUEST.get('order[0][column]')

    def get_order_direction(self):
        return self.context.REQUEST.get('order[0][dir]')

    def countries_filter(self):
        return self._filter_as_list('countries[]')

    def obligations_filter(self):
        return self._filter_as_list('obligations[]')

    def _filter_as_list(self, filter_name):
        req_filter = self.context.REQUEST.get(filter_name, [])
        if isinstance(req_filter, str):
            req_filter = [req_filter]
        return req_filter

    def selected_role(self):
        return self.context.REQUEST.get('role', self.get_roles()[0])

    def get_roles(self):
        roles = list(self.context.valid_roles())
        filter(roles.remove,
               ['Authenticated', 'Anonymous', 'Manager', 'Owner'])
        return sorted(roles)

    def get_rod_obligations(self):
        """ Get activities from ROD """

        data = sorted(self.context.dataflow_rod(),
                    key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        return {
            'legal_instruments': sorted(obligations.keys()),
            'obligations': obligations }


class ListUsers(BrowserView):

    def get_rod_obligations(self):
        """ Get activities from ROD """

        data = sorted(self.context.dataflow_rod(),
                    key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        return {
            'legal_instruments': sorted(obligations.keys()),
            'obligations': obligations }

    def get_brains(self):
        query = {'meta_type': 'Report Collection'}
        obligations_filter = self.obligations_filter()
        if obligations_filter:
            query['dataflow_uris'] = map(self.get_obligation_uri,
                                         obligations_filter)
        if self.countries_filter():
            filtered_countries = [c['uri'] for c in self.context.localities_rod()
                                  if c['iso'] in self.countries_filter()]
            query['country'] = filtered_countries

        return self.context.Catalog(query)

    def get_data(self):
        def path_compare(p1, p2):
            return cmp(p1['path_prefix'], p2['path_prefix'])

        role = self.selected_role()
        brains = self.get_brains()
        results = []
        for brain in brains:
            obj = brain.getObject()
            results.append({
                'path_prefix': obj.absolute_url(0),
                'path_suffix': '/' + obj.absolute_url(1),
                'last_change': obj.bobobase_modification_time().Date(),
                'persons': obj.users_with_local_role(role),
                'obligation_uris': list(obj.dataflow_uris)
            })

        results.sort(path_compare)
        return results

    def get_data_by_person(self):
        brains = self.get_brains()

        role = self.selected_role()
        results = {}
        for brain in brains:
            obj = brain.getObject()
            persons = obj.users_with_local_role(role)
            for person in persons:
                paths = results.get(person, [])
                paths.append(obj.absolute_url(1))
                results[person] = paths

        return results

    def has_common_elements(self, l1, l2):
        return bool(set(l1) & set(l2))

    def person_uri(self, person):
        return 'http://www.eionet.europa.eu/directory/user?uid=%s' % person

    def obligations_filter(self):
        return self._get_filter('obligations')

    def countries_filter(self):
        return self._get_filter('countries')

    def selected_role(self):
        return self.context.REQUEST.get('role', self.get_roles()[0])

    def _get_filter(self, filter_name):
        req_filter = self.context.REQUEST.get(filter_name, [])
        if not isinstance(req_filter, list):
            req_filter = [req_filter]
        return req_filter

    def by_person_url(self):
        base_url = 'list_users_by_person'
        if self.context.REQUEST.QUERY_STRING:
            return base_url + '?' + self.context.REQUEST.QUERY_STRING
        else:
            return base_url

    def by_path_url(self):
        base_url = 'list_users'
        if self.context.REQUEST.QUERY_STRING:
            return base_url + '?' + self.context.REQUEST.QUERY_STRING
        else:
            return base_url

    def get_roles(self):
        roles = list(self.context.valid_roles())
        filter(roles.remove,
               ['Authenticated', 'Anonymous', 'Manager', 'Owner'])
        return sorted(roles)
