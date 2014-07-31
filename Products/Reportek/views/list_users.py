import json
from copy import copy
from base_admin import BaseAdmin


class ListUsers(BaseAdmin):
    """ View for get_users_by_path, get_users """

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


    def search_catalog(self, obligations, countries, role):
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

        return self.context.Catalog(query)


    def get_records(self, REQUEST):
        obligations = REQUEST.get('obligations', [])
        countries = REQUEST.get('countries', [])
        role = REQUEST.get('role', '')

        for brain in self.search_catalog(obligations, countries, role):

            obligations = []
            for uri in list(brain.dataflow_uris):
                try:
                    title = self.get_obligations_title()[uri]
                except KeyError:
                    title = 'Unknown/Deleted obligation'
                obligations.append((uri, title))

            if role:
                users = [user for user, roles
                         in brain.local_defined_users.iteritems()
                         if role in roles]
            else:
                if isinstance(brain.local_defined_users, dict):
                    users = brain.local_defined_users.keys()

            if not users:
                continue

            yield {
                'path': [brain.getPath(), brain.title],
                'last_change': brain.bobobase_modification_time.Date(),
                'obligations': obligations,
                'users':  users}


    def getUsers(self, REQUEST):

        records = []
        for record in self.get_records(REQUEST):
            res = copy(record)
            del res['users']
            for user in record['users']:
                rr = copy(res)
                rr['user'] = user
                records.append(rr)

        return json.dumps({"data": records})


    def getUsersByPath(self, REQUEST):

        records = []
        for record in self.get_records(REQUEST):
            records.append(record)

        return json.dumps({"data": records})
