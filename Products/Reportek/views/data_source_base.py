from Products.Five import BrowserView


class DataSourceBase(BrowserView):

    def __init__(self, context, request):
        super(DataSourceBase, self).__init__(context, request)
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
