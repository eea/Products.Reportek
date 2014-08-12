import json
from copy import copy
from operator import itemgetter
import Zope2

from base_admin import BaseAdmin


class ListUsers(BaseAdmin):

    def __call__(self, *args, **kwargs):
        super(ListUsers, self).__call__(*args, **kwargs)

        if self.__name__ == 'country.reporters':
            countries = self.get_available_countries()

            country = self.request.get('country')
            if not country:
                country = countries[0]

            reporters = self.get_reporters(country)

            return self.index(
                    reporters=reporters,
                    countries=countries)

        return self.index()


    def get_available_countries(self):
        app = Zope2.bobo_application()
        countries = app.objectValues('Report Collection')
        return sorted(countries, key=lambda x: x.title)


    def get_reporters(self, country, role='Reporter'):

        acl_users = self.context.acl_users.ldapmultiplugin.acl_users


        query = {
            'meta_type': 'Report Collection',
            'local_unique_roles': role,
            'path': '/{0}'.format(country)}

        users = []
        for brain in self.context.Catalog(query):
            for user, roles in brain.local_defined_roles.items():
                if role in roles:
                    user_ob = acl_users.getUserById(user)
                    user_info = {
                        'uid': user,
                        'name': user_ob.cn,
                        'email': user_ob.mail}
                    users.append(user_info)

        users.sort(key=itemgetter('name'))
        return sorted(users)


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
