from collections import defaultdict
from operator import itemgetter
from Products.Five import BrowserView
import json


class DataSources(BrowserView):
    def __init__(self, context, request):
        super(DataSources, self).__init__(context, request)
        self.dataflow_rod = self.context.dataflow_rod()
        self.obligation_uri = self._create_obligation_uri_dict()
        self.obligation_title = self._create_obligation_title_dict()

    def _create_obligation_uri_dict(self):
        result = {}
        for obligation in self.dataflow_rod:
            result[obligation['PK_RA_ID']] = obligation['uri']
        return result

    def _create_obligation_title_dict(self):
        result = {}
        for obligation in self.dataflow_rod:
            result[obligation['uri']] = obligation['TITLE']
        return result

    def get_brains(self):
        """Makes the query in catalog and returns the total number of hits and
        the hits
        """
        country_codes = [c['uri'] for c in self.context.localities_rod()
                         if c['iso'] in self.countries_filter()]
        query = {
            'meta_type': 'Report Collection',
            'roles': self.selected_role()
        }
        if country_codes:
            query['country'] = country_codes
        search_value = self.get_search_value()
        if search_value:
            query['path'] = self.get_search_value()


#       Get the total numbers of brains
        brains_number = len(self.context.Catalog(query))

        if self.obligations_filter():
            dataflow_uris = [self.obligation_uri[obl_id] for obl_id in
                             self.obligations_filter()]
            query['dataflow_uris'] = dataflow_uris

#       Added to query parameters for the specific page
        query['b_size'] = self.get_length()
        query['b_start'] = self.get_start()
        query['sort_order'] = self.get_order_direction()
        query['sort_on'] = self.get_order_column()

        brains = self.context.Catalog(query)

        return (brains_number, brains)

    def process_data(self):
        if self.context.REQUEST['REQUEST_METHOD'] == 'GET':
            results = []
            brains_number, brains = self.get_brains()

            for brain in brains:
                obj = brain.getObject()
                uris = list(obj.dataflow_uris)
                # TODO: Find out why uri is not always in dataflow_uris
                obligations = [
                    (uri, self.obligation_title.get(uri, '')) for uri in uris
                ]
                short_path = '/' + obj.absolute_url(1)
                full_path = obj.absolute_url(0)
                users = obj.users_with_local_role(self.selected_role())
                users_with_uri = [(self.user_uri(user), user) for user in users]
                results.append({
                    'path': [full_path, short_path],
                    'last_change': obj.bobobase_modification_time().Date(),
                    'obligations': obligations,
                    'users':  users_with_uri})

            data_to_return = {
                "recordsFiltered": brains_number,
                "draw": self.get_draw(),
                "data": results
            }
            return json.dumps(data_to_return)

    def user_uri(self, user):
        return "http://www.eionet.europa.eu/directory/user?uid=%s" % user

    def get_draw(self):
        return self.context.REQUEST.get('draw')

    def get_start(self):
        return self.context.REQUEST.get('start', '0')

    def get_length(self):
        return self.context.REQUEST.get('length', '10')

    def get_search_value(self):
        return self.context.REQUEST.get('search[value]')

    def get_order_column(self):
        col_idx = self.context.REQUEST.get('order[0][column]')
        if col_idx == '0':
            return 'path'
        elif col_idx == '1':
            return 'bobobase_modification_time'
        elif col_idx == '2':
            return 'dataflow_uris'
        else:
            raise NotImplementedError()

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


class ByPersonDataSource(DataSources):

    def get_brains(self):
        country_codes = [c['uri'] for c in self.context.localities_rod()
                         if c['iso'] in self.countries_filter()]
        query = {
            'meta_type': 'Report Collection',
            'roles': self.selected_role()
        }
        if country_codes:
            query['country'] = country_codes

        if self.obligations_filter():
            dataflow_uris = [self.obligation_uri[obl_id] for obl_id in
                             self.obligations_filter()]
            query['dataflow_uris'] = dataflow_uris

        brains = self.context.Catalog(query)

        return brains

    def process_data(self):
        results = []
        paths = defaultdict(list)
        brains = self.get_brains()

        for brain in brains:
            obj = brain.getObject()
            users = obj.users_with_local_role(self.selected_role())
            for user in users:
                full_path = obj.absolute_url(0)
                short_path = '/' + obj.absolute_url(1)
                paths[user].append((full_path, short_path))

        for user in paths.keys():
            results.append({
                'auditor': user,
                'path': paths[user]
            })

        json_res = json.dumps({
            'draw': self.get_draw(),
            'data': results
        })

        return json_res


class TemplateUsersAdmin(BrowserView):
    """The view's template for users administration"""

    def get_rod_obligations(self):
        """ Get activities from ROD """
        data = sorted(self.context.dataflow_rod(),
                      key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        return {'legal_instruments': sorted(obligations.keys()),
                'obligations': obligations}

    def obligations_filter(self):
        return self._get_filter('obligations')

    def _get_filter(self, filter_name):
        req_filter = self.context.REQUEST.get(filter_name, [])
        if not isinstance(req_filter, list):
            req_filter = [req_filter]
        return req_filter

    def get_roles(self):
        roles = list(self.context.valid_roles())
        filter(roles.remove,
               ['Authenticated', 'Anonymous', 'Manager', 'Owner'])
        return sorted(roles)


class ListUsers(TemplateUsersAdmin):
    """View for list_users_by_path, list_users_by_person"""

    def get_view_parent(self):
        """Returns an instance of TemplateUsersAdmin """
        return self.context.restrictedTraverse('@@template_users_admin')

    def get_view(self, group_criterion):
        """Returns the view coresponding to the group_criterion"""
        if self.context.REQUEST.QUERY_STRING:
            return group_criterion + '?' + self.context.REQUEST.QUERY_STRING
        else:
            return group_criterion
