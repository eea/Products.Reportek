import json
from Products.Reportek.config import REPORTEK_DEPLOYMENT, DEPLOYMENT_BDR
from copy import copy
from operator import itemgetter
from Products.Reportek.constants import ENGINE_ID, ECAS_ID

from base_admin import BaseAdmin


class ListUsers(BaseAdmin):

    def __call__(self, *args, **kwargs):
        super(ListUsers, self).__call__(*args, **kwargs)
        if self.__name__ == 'country.reporters':
            countries = self.get_available_countries()

            country = self.request.get('country')

            if not country:
                country = countries[0].getId()

            reporters = self.get_reporters(country)

            return self.index(reporters=reporters,
                              countries=countries)

        return self.index()


    def get_available_countries(self):
        app = self.context.getPhysicalRoot()
        countries = app.objectValues('Report Collection')
        return sorted(countries, key=lambda x: x.title)


    def get_reporters(self, country, role='Reporter'):
        acl_users = self.context.acl_users
        if (hasattr(acl_users, 'ldapmultiplugin')):
            acl_users = self.context.acl_users.ldapmultiplugin.acl_users
            query = {
                'meta_type': 'Report Collection',
                'local_unique_roles': role,
                'path': '/{0}'.format(country)}

            users = []
            brains = self.context.Catalog(query)
            for brain in brains:
                for user, roles in brain.local_defined_roles.items():
                    if role in roles:
                        user_ob = acl_users.getUserById(user)
                        if user_ob:
                            user_info = {
                                'uid': user,
                                'name': unicode(user_ob.cn, 'latin-1'),
                                'email': user_ob.mail}
                            users.append(user_info)

            users.sort(key=itemgetter('name'))
            return sorted(users)
        return []

    def get_middleware(self):
        engine = self.context.unrestrictedTraverse('/'+ENGINE_ID)
        return engine.authMiddlewareApi

    def get_ecas_users(self):
        ecas_path = '/'+ENGINE_ID+'/acl_users/'+ECAS_ID
        ecas = self.context.unrestrictedTraverse(ecas_path)

        return ecas._user2ecas_id.keys()

    def get_records(self, REQUEST):

        obligation = REQUEST.get('obligation', '')
        countries = REQUEST.get('countries[]', [])
        role = REQUEST.get('role', '')

        if not isinstance(countries, list):
            countries = [countries]

        use_role = role
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            if role == 'ClientFG':
                use_role = ''

        brains = self.search_catalog(obligation, countries, use_role)

        for brain in brains:
            obligations = []
            for uri in list(brain.dataflow_uris):
                try:
                    title = self.get_obligations_title()[uri]
                except KeyError:
                    title = 'Unknown/Deleted obligation'
                obligations.append((uri, title))

            if role:
                users = dict((user, {'uid': user,
                                     'role': role,
                                     'type': 'Local/LDAP'
                                     }) for user, roles
                             in brain.local_defined_roles.iteritems()
                             if role in roles)
            else:
                if brain.local_defined_users:
                    users = dict((user, {'uid': user,
                                         'role': brain.local_defined_roles.get(user),
                                         'type': 'Local/LDAP'
                                         })
                                 for user in brain.local_defined_users
                                 if brain.local_defined_users)

            if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                ecas_users = self.get_ecas_users()
                middleware = self.get_middleware()
                ecas = self.context.unrestrictedTraverse('/acl_users/'+ECAS_ID)

                for user in ecas_users:
                    ecas_user_id = ecas.getEcasUserId(user)

                    # Normalize path object path
                    obj_path = brain.getPath()
                    if obj_path.startswith('/'):
                        obj_path = obj_path[1:]

                    if middleware.authorizedUser(ecas_user_id, obj_path):
                        users[user] = {
                            'uid': user,
                            'type': 'ECAS',
                            'role': 'ClientFG'
                        }

            if not users:
                continue

            yield {
                'path': [brain.getPath(), brain.title],
                'obligations': obligations,
                'users':  users}

    def getUsers(self, REQUEST):

        records = []
        recs = self.get_records(REQUEST)
        for record in recs:
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
        return json.dumps({"data": list(self.get_records(REQUEST))})
