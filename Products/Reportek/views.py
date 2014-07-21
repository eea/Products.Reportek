import json
from operator import itemgetter
from collections import defaultdict

from Products.Five import BrowserView


class DataSources(BrowserView):
    def __init__(self, context, request):
        super(DataSources, self).__init__(context, request)
        self.obligation_uri = self._create_obligation_uri_dict()

    def _create_obligation_uri_dict(self):
        result = {}
        for obligation in self.context.dataflow_rod():
            result[obligation['PK_RA_ID']] = obligation['uri']
        return result

    def get_brains(self):
        """Makes the query in catalog and returns the hits """
        country_codes = [c['uri'] for c in self.context.localities_rod()
                         if c['iso'] in self.countries_filter()]
        query = {
            'meta_type': 'Report Collection',
            'b_size': self.get_length(),
            'b_start': self.get_start(),
            'sort_order': self.get_order_direction(),
            'sort_on': self.get_order_column(),
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
                    'users': obj.users_with_local_role(self.selected_role())})

                data_to_return = {
                    "draw": self.get_draw(),
                    "data": results
                }
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
