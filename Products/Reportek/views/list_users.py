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

            entities = {}
            brains = self.context.Catalog(query)
            for brain in brains:
                for entity, roles in brain.local_defined_roles.items():
                    if role in roles:
                        user_ob = acl_users.getUserById(entity)
                        if user_ob:
                            if entities.get(entity):
                                paths = entities[entity].get('paths', [])
                                paths.append(brain.getURL())
                                paths.sort()
                            else:
                                user_info = {
                                    'uid': entity,
                                    'type': 'User',
                                    'name': unicode(user_ob.getProperty('cn'),
                                                    'latin-1'),
                                    'email': user_ob.getProperty('mail'),
                                    'paths': [brain.getURL()]}
                                entities[entity] = user_info
                        else:
                            groups = self.search_ldap_groups(entity)
                            if groups:
                                # Use only the first result
                                group = groups[0]
                                entities[entity] = {
                                    'uid': entity,
                                    'type': 'LDAP Group',
                                    'name': group.get('description'),
                                    'email': None,
                                    'paths': [brain.getURL()]
                                }

            entity_list = entities.values()

            entity_list.sort(key=itemgetter('uid'))
            return entity_list

        return []

    def get_middleware(self):
        engine = self.context.unrestrictedTraverse('/'+ENGINE_ID, None)
        if engine:
            return engine.authMiddlewareApi

    def is_ldap_user(self, username):
        acl_users = self.context.acl_users
        if (hasattr(acl_users, 'ldapmultiplugin')):
            ldap_users = acl_users.ldapmultiplugin.acl_users
            user_ob = ldap_users.getUserById(username)
            if user_ob:
                return True

    def is_ecas_user(self, username):
        ecas_path = '/acl_users/' + ECAS_ID
        ecas = self.context.unrestrictedTraverse(ecas_path, None)
        if ecas:
            if ecas.getEcasUserId(username):
                return True

    def is_local_user(self, username):
        acl_users = self.context.acl_users
        if acl_users.getUserById(username):
            return True

    def get_user_type(self, username):
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            if self.is_ecas_user(username):
                return 'ECAS'
        if self.is_ldap_user(username):
            return 'LDAP'
        elif self.is_local_user(username):
            return 'LOCAL'

        return 'N/A'

    def api_get_user_type(self, REQUEST):
        username = REQUEST.get('username')

        return json.dumps({"username": username,
                           "utype": self.get_user_type(username)})

    def get_records(self, REQUEST):

        obligation = REQUEST.get('obligation', '')
        countries = REQUEST.get('countries[]', [])
        role = REQUEST.get('role', '')

        if not isinstance(countries, list):
            countries = [countries]

        use_role = role
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            # ClientFG role users come from ECAS in BDR, this is why we need
            # all the collections
            if role == 'ClientFG':
                use_role = ''

        brains = self.search_catalog(obligation, countries, use_role)

        for brain in brains:
            users = {}
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
                                     }) for user, roles
                             in brain.local_defined_roles.iteritems()
                             if role in roles)
            else:
                if brain.local_defined_users:
                    users = dict((user, {'uid': user,
                                         'role': brain.local_defined_roles.get(user),
                                         })
                                 for user in brain.local_defined_users)
            if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                # Hide our internal user agent from search results
                if 'bdr_folder_agent' in users.keys():
                    del users['bdr_folder_agent']

                middleware = self.get_middleware()
                ecas_path = '/acl_users/' + ECAS_ID
                ecas = self.context.unrestrictedTraverse(ecas_path, None)

                if ecas:
                    ecas_users = getattr(ecas, '_ecas_id', {})
                    for ecas_user_id, user in ecas_users.iteritems():

                        # Normalize path object path
                        obj_path = brain.getPath()
                        if obj_path.startswith('/'):
                            obj_path = obj_path[1:]

                        if middleware.authorizedUser(ecas_user_id, obj_path):
                            username = getattr(user, 'username', None)
                            if username:
                                uid = username
                            else:
                                uid = getattr(user, 'email', None)
                            users[uid] = {
                                'uid': uid,
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
