import json
from base_admin import BaseAdmin


class ListUsers(BaseAdmin):
    """ View for get_users_by_path, get_users """

    def get_country_codes(self, countries):
        return [c['uri'] for c
                in self.context.localities_rod()
                if c['iso'] in countries]

    def get_obligations(self):
        return {o['PK_RA_ID']:o['uri'] for o
                in self.context.dataflow_rod()}

    def get_obligations_title(self):
        return {o['uri']:o['TITLE'] for o
                in self.context.dataflow_rod()}

    def get_order_column(self):
        #todo
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
        #todo
        request_param = self.context.REQUEST.get('order[0][dir]')
        if request_param == 'desc':
            return 'descending'
        return 'ascending'

    def search_catalog(self, obligations, countries, role, **kwargs):
        country_codes = self.get_country_codes(countries)
        dataflow_uris = [self.get_obligations[obl_id] for obl_id
                         in obligations]

        query = {'meta_type': 'Report Collection'}

        if role:
            query['local_defined_roles'] = role
        if country_codes:
            query['country'] = country_codes
        if dataflow_uris:
            query['dataflow_uris'] = dataflow_uris

        query['b_size'] = kwargs['b_size']
        query['b_start'] = kwargs['b_start']
        query['sort_order'] = kwargs['sort_order']
        query['sort_on'] = kwargs['sort_on']

        return self.context.Catalog(query)


    def getUsersByPath(self, REQUEST):

        obligations = REQUEST.get('obligations', [])
        countries = REQUEST.get('countries', [])
        role = REQUEST.get('role', '')

        brains = self.search_catalog(obligations, countries, role,
                            b_size=REQUEST.get('length', 10),
                            b_start=REQUEST.get('start', 0),
                            sort_order=self.get_order_direction(),
                            sort_on=self.get_order_column())

        results = []

        for brain in brains:

            obligations = [(uri, self.get_obligations_title()[uri]) for uri
                         in list(brain.dataflow_uris)]

            if role:
                users = [user for user,roles
                         in brain.local_defined_users.iteritems()
                         if role in roles]
            else:
                users = brain.local_defined_users.keys()

            if not users:
                continue

            results.append({
                'path': [brain.getPath(), brain.getPath(), brain.title],
                'last_change': brain.bobobase_modification_time.Date(),
                'obligations': obligations,
                'users':  users})

        return json.dumps({"data": results})
