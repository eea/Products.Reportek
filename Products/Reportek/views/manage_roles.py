from base_admin import BaseAdmin
from operator import itemgetter
from Products.Reportek.constants import ENGINE_ID, ECAS_ID
from Products.Reportek.config import *


class ManageRoles(BaseAdmin):

    def __call__(self, *args, **kwargs):
        super(ManageRoles, self).__call__(*args, **kwargs)

        if self.__name__ == 'assign_role':
            if self.request.get('btn.assign'):
                self.assign_role()

        elif self.__name__ == 'revoke_roles':
            if self.request.get('btn.revoke'):
                self.revoke_roles()

        return self.index()

    def get_all_country_codes(self):
        return [c.get('iso') for c in self.localities_rod]

    def get_user_localroles(self, username):
        results = []
        for brain in self.context.Catalog(meta_type='Report Collection'):
            coll = brain.getObject()
            local_roles = coll.get_local_roles_for_userid(username)
            if local_roles:
                results.append({
                    'country': coll.getCountryName,
                    'collection': coll,
                    'roles': ', '.join([role for role in local_roles])
                })

        return results

    def assign_role(self):
        collections = self.request.get('collections', [])
        role = self.request.get('role', '')

        search_type = self.request.get('search_type')
        entity = self.request.get('username', '')
        match_groups = []
        groups = False

        results = []

        if search_type == 'groups':
            entity = self.request.get('groupsname', '')
            use_subgroups = self.request.get('use-subgroups')
            if use_subgroups:
                match_groups = use_subgroups.split(',')
                groups = True

        for collection in collections:
            cur_entity = entity
            path, matched = collection.split(',')
            obj = self.context.unrestrictedTraverse(path)

            if groups and (matched in match_groups):
                cur_entity = matched
            elif groups and not (matched in match_groups):
                continue

            roles = set(obj.get_local_roles_for_userid(cur_entity))
            roles.add(role)
            obj.manage_setLocalRoles(cur_entity, list(roles))
            obj.reindex_object()
            results.append({
                'entity': cur_entity,
                'path': path,
                'role': role
                })

        if results:
            results.sort(key=itemgetter('path'))
            self.request['search_term'] = ''
        self.request['op_results'] = results

    def revoke_roles(self):
        collections = self.request.get('collections', [])
        search_type = self.request.get('search_type')
        entity = self.request.get('username', '')
        match_groups = []
        results = []
        if search_type == 'groups':
            entity = self.request.get('groupsname', '')
            use_subgroups = self.request.get('use-subgroups', '')
            match_groups = use_subgroups.split(',')

        for collection in collections:
            path, matched = collection.split(',')
            obj = self.context.unrestrictedTraverse(path)

            if match_groups and matched:
                if matched in match_groups:
                    entity = matched

            revoke_roles = self.request.get(path.replace('/', '_'), [])
            roles = set(obj.get_local_roles_for_userid(entity))
            for role in revoke_roles:
                roles.remove(role)
            obj.manage_delLocalRoles([entity])
            if roles:
                obj.manage_setLocalRoles(entity, list(roles))
            obj.reindex_object()
            results.append({
                'entity': entity,
                'path': path,
                'role': role
                })

        if results:
            results.sort(key=itemgetter('path'))
            self.request['search_term'] = ''
        self.request['op_results'] = results

    def search_ldap_users(self, term):
        params = [name for name, value in self.get_ldap_schema()]
        acl_users = self.get_acl_users()

        users = [acl_users.findUser(search_param=p, search_term=term)
                 for p in params]
        users = reduce(lambda x, y: x + y, users)
        users = {user.get('uid'): user for user in users}.values()

        return users

    def search_ecas_users(self, term):
        ecas_path = '/' + ENGINE_ID + '/acl_users/' + ECAS_ID
        ecas = self.context.unrestrictedTraverse(ecas_path, None)
        ecas_db = getattr(ecas, '_ecas_id', None)
        users = []
        if ecas_db:
            for user in ecas_db.values():
                username = user.username
                email = user.email
                if isinstance(username, unicode):
                    username = username.encode('utf-8')
                if isinstance(email, unicode):
                    email = email.encode('utf-8')
                if username:
                    if isinstance(username, unicode):
                        username = username.encode('utf-8')
                    if term in username:
                        result = {
                            'uid': username,
                            'mail': email
                        }
                        users.append(result)
                        continue
                if email:
                    if term in email:
                        entity = username
                        if not entity:
                            entity = email
                        result = {
                            'uid': entity,
                            'mail': email
                        }
                        users.append(result)

        return users

    def search_entities(self):
        term = self.request.get('search_term')
        s_type = self.request.get('search_type')
        response = {}
        if term:
            if s_type == 'groups':
                groups = self.search_ldap_groups(term)
                response['groups'] = groups
            else:
                ldap_users = self.search_ldap_users(term)
                ecas_users = []
                if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                    ecas_users = self.search_ecas_users(term)

                if ldap_users:
                    err_users = [user for user in ldap_users
                                 if user.get('sn') == 'Error']
                    if err_users:
                        response['errors'] = True

                users = ecas_users + ldap_users

                if users:
                    users.sort(key=itemgetter('uid'))

                response['users'] = users

        return response

    def get_ldap_schema(self):
        return (self.get_acl_users()
                    .getLDAPSchema())

    def display_confirmation(self):
        return ((self.request.get('username', None) or
                 self.request.get('groupsname', None)) and
                self.request.get('countries', []) and
                self.request.get('role', None))
