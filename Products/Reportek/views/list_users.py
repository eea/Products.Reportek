import json
from copy import copy
from operator import itemgetter
from base_admin import BaseAdmin


class ListUsers(BaseAdmin):
    """ View for get_users_by_path, get_users """


    def get_records(self, REQUEST):

        obligation = REQUEST.get('obligation', '')
        countries = REQUEST.get('countries[]', [])
        role = REQUEST.get('role', '')

        if not isinstance(countries, list):
            countries = [countries]


        for brain in self.search_catalog(obligation, countries, role):

            obligations = []
            for uri in list(brain.dataflow_uris):
                try:
                    title = self.get_obligations_title()[uri]
                except KeyError:
                    title = 'Unknown/Deleted obligation'
                obligations.append((uri, title))

            if role:
                users = [user for user, roles
                         in brain.local_defined_roles.iteritems()
                         if role in roles]
            else:
                users = brain.local_defined_users

            if not users:
                continue

            yield {
                'path': [brain.getPath(), brain.title],
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

        # Datatable needs items sorted by user in order to group them
        records.sort(key=itemgetter('user'))
        return json.dumps({"data": records})


    def getUsersByPath(self, REQUEST):

        records = []
        for record in self.get_records(REQUEST):
            records.append(record)

        return json.dumps({"data": records})
