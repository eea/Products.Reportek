from copy import copy
from operator import itemgetter
from plone.memoize import ram
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import REPORTEK_DEPLOYMENT
from Products.Reportek.constants import ENGINE_ID, ECAS_ID
from time import time
import json

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
                        if entities.get(entity):
                            paths = entities[entity].get('paths', [])
                            paths.append(brain.getURL())
                            paths.sort()
                        else:
                            e_info = {
                                'uid': entity,
                            }
                            user_ob = acl_users.getUserById(entity)
                            if user_ob:
                                e_info['type'] = 'User'
                                e_info['name'] = unicode(user_ob.getProperty('cn'),
                                                         'latin-1')
                                e_info['email'] = user_ob.getProperty('mail')
                                e_info['paths'] = [brain.getURL()]
                            else:
                                groups = self.search_ldap_groups(entity)
                                if groups:
                                    # Use only the first result
                                    group = groups[0]
                                    e_info['type'] = 'LDAP Group'
                                    e_info['name'] = group.get('description')
                                    e_info['email'] = None
                                    e_info['paths'] = [brain.getURL()]
                            entities[entity] = e_info

            entity_list = entities.values()

            entity_list.sort(key=itemgetter('uid'))
            return entity_list

        return []

    def get_middleware(self):
        engine = self.context.unrestrictedTraverse('/'+ENGINE_ID, None)
        if engine:
            return engine.authMiddleware

    def is_ldap_user(self, username):
        acl_users = self.context.acl_users
        if (hasattr(acl_users, 'ldapmultiplugin')):
            ldap_users = acl_users.ldapmultiplugin.acl_users
            user_ob = ldap_users.getUserById(username)
            if user_ob:
                return user_ob

    @ram.cache(lambda *args: time() // (60*60*12))
    def getLDAPGroups(self):
        """ Return a list of LDAP group ids
        """
        group_ids = []
        acl_users = self.context.acl_users
        if (hasattr(acl_users, 'ldapmultiplugin')):
            ldap_users = acl_users.ldapmultiplugin.acl_users
            groups = ldap_users.getGroups()
            group_ids = [group[0] for group in groups if group[0]]

        return group_ids

    def is_ldap_group(self, username):
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
            ldap_groups = self.getLDAPGroups()
            if username in ldap_groups:
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
            return 'LDAP User'
        elif self.is_local_user(username):
            return 'LOCAL'
        elif self.is_ldap_group(username):
            return 'LDAP Group'

        return 'N/A'

    def api_get_user_type(self, REQUEST):
        username = REQUEST.get('username')

        return json.dumps({"username": username,
                           "utype": self.get_user_type(username)})

    def api_get_users_type(self, REQUEST):
        users = list(set(REQUEST.get('users[]', [])))
        users_type = []
        for user in users:
            users_type.append({"username": user,
                               "utype": self.get_user_type(user)})

        return json.dumps(users_type)

    def get_records(self, REQUEST):

        obligations = REQUEST.get('obligations[]', [])
        countries = REQUEST.get('countries[]', [])
        role = REQUEST.get('role', '')
        path = REQUEST.get('path_filter', '')
        use_path = None
        parts = None
        if not isinstance(countries, list):
            countries = [countries]

        use_role = role
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            if role == 'Reporter (Owner)':
                use_role = 'Owner'

        if path:
            parts = path.split('/')
            if path.startswith('http') or path.startswith('/'):
                use_path = path
                if path.startswith('http'):
                    use_path = '/{0}'.format('/'.join(parts[3:]))
                parts = None
            else:
                parts = path

        brains = self.search_catalog(obligations, countries, use_role,
                                     path=use_path)
        for brain in brains:
            users = {}
            col_obligations = []
            if not parts or parts in brain.getPath():
                for uri in list(brain.dataflow_uris):
                    try:
                        title = self.get_obligations_title()[uri]
                    except KeyError:
                        title = 'Unknown/Deleted obligation'
                    col_obligations.append((uri, title))

                if use_role:
                    users = dict((user, {'uid': user,
                                         'role': role,
                                         }) for user, roles
                                 in brain.local_defined_roles.iteritems()
                                 if use_role in roles)
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
                                    'role': 'Reporter (Owner)'
                                }
                if not users:
                    continue

                yield {
                    'collection': {
                        'path': brain.getPath(),
                        'title': brain.title,
                        'type': brain.meta_type
                    },
                    'obligations': col_obligations,
                    'users':  users}

    def getUsersByPath(self, REQUEST):
        return json.dumps({"data": list(self.get_records(REQUEST))})
