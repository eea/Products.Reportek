from plone.memoize import ram
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import REPORTEK_DEPLOYMENT
from Products.Reportek.constants import ENGINE_ID, ECAS_ID
from time import time
import json

from base_admin import BaseAdmin


class ListUsers(BaseAdmin):

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

    def get_ecas_user(self, username):
        user = None
        ecas_path = '/acl_users/' + ECAS_ID
        ecas = self.context.unrestrictedTraverse(ecas_path, None)
        if ecas:
            user = ecas.getEcasUserId(username)
        return user

    def get_ecas_email(self, username):
        email = None
        ecas_path = '/acl_users/' + ECAS_ID
        ecas = self.context.unrestrictedTraverse(ecas_path, None)
        if ecas:
            email = ecas.getEcasIDEmail(username)
        return email

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

    def get_user_details(self, username):
        r = {'fullname': '', 'email': ''}

        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            user = self.get_ecas_user(username)
            if user:
                r['email'] = self.get_ecas_email(user)

        user = self.is_ldap_user(username)
        if user:
            r['fullname'] = getattr(user, 'cn', 'N/A')
            r['email'] = getattr(user, 'mail', 'N/A')

        return r

    def api_get_user_type(self, REQUEST):
        username = REQUEST.get('username')

        return json.dumps({"username": username,
                           "utype": self.get_user_type(username)})

    def api_get_users_type(self, REQUEST):
        users = REQUEST.get('users[]', [])
        if not isinstance(users, list):
            users = [users]
        users = list(set(users))
        users_type = []
        for user in users:
            user_details = self.get_user_details(user)

            users_type.append({'username': user,
                               'utype': self.get_user_type(user),
                               'fullname': user_details['fullname'],
                               'email': user_details['email']})

        return json.dumps(users_type)

    def get_ecas_reporters_by_path(self, REQUEST):
        paths = REQUEST.get('paths[]', [])
        middleware = self.get_middleware()
        users = {}
        for path in paths:
            col = self.context.unrestrictedTraverse(path, None)
            users[path] = []
            if col and col.company_id:
                col_obligations = []
                for uri in list(col.dataflow_uris):
                    try:
                        title = self.get_obligations_title()[uri]
                    except KeyError:
                        title = 'Unknown/Deleted obligation'
                    col_obligations.append((uri, title))
                c_data = col.get_company_data()
                if c_data:
                    role_map = {
                        'RW': 'Reporter (Owner)',
                        'RO': 'Reader'
                    }
                    check_path = path[1:] if path.startswith('/') else path
                    users[path] = [{'uid': u.get('username'),
                                    'role': role_map.get(middleware.authorizedUser(u.get('username'), check_path)),
                                    'collection': col.title,
                                    'path': path,
                                    'obligations': col_obligations,
                                    'email': u.get('email'),
                                    'username': u.get('username'),
                                    'fullname': ' '.join([u.get('first_name'), u.get('last_name')])}
                                   for u in c_data.get('users', [])]
        return json.dumps(users)

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

                if not users:
                    continue

                yield {
                    'collection': {
                        'path': brain.getPath(),
                        'title': brain.title,
                        'type': brain.meta_type,
                        'company_id': getattr(brain, 'company_id', None)
                    },
                    'obligations': col_obligations,
                    'users':  users}

    def getUsersByPath(self, REQUEST):
        return json.dumps({"data": list(self.get_records(REQUEST))})
