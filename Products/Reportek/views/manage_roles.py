from base_admin import BaseAdmin
from Products.Reportek.constants import ENGINE_ID, ECAS_ID
from Products.Reportek.config import *


class ManageRoles(BaseAdmin):


    def __call__(self, *args, **kwargs):
        super(ManageRoles, self).__call__(*args, **kwargs)

        if self.__name__ == 'assign_role':
            if self.request.get('btn.assign'):
                self.assign_role()
                return self.request.response.redirect('%s/%s?done=1' % (
                        self.context.absolute_url(), self.__name__))

        elif self.__name__ == 'revoke_roles':
            if self.request.get('btn.revoke'):
                self.revoke_roles()
                return self.request.response.redirect('%s/%s?done=1' % (
                        self.context.absolute_url(), self.__name__))

        return self.index()

    def get_acl_users(self):
        pas = getattr(self.context, 'acl_users')
        if pas:
            ldapmultiplugin = getattr(pas, 'ldapmultiplugin')
            if ldapmultiplugin:
                return getattr(ldapmultiplugin, 'acl_users')

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
        username = self.request.get('username', '')
        role = self.request.get('role', '')
        for collection in collections:
            obj = self.context.unrestrictedTraverse(collection)
            roles = set(obj.get_local_roles_for_userid(username))
            roles.add(role)
            obj.manage_setLocalRoles(username, list(roles))
            obj.reindex_object()

    def revoke_roles(self):
        collections = self.request.get('collections', [])
        username = self.request.get('username', '')
        for collection in collections:
            obj = self.context.unrestrictedTraverse(collection)
            revoke_roles = self.request.get(collection.replace('/', '_'), [])
            roles = set(obj.get_local_roles_for_userid(username))
            for role in revoke_roles:
                roles.remove(role)
            obj.manage_delLocalRoles([username])
            if roles:
                obj.manage_setLocalRoles(username, list(roles))
            obj.reindex_object()

    def search_ldap_users(self, term):
        params = [name for name, value in self.get_ldap_schema()]
        acl_users = self.get_acl_users()

        users = [acl_users.findUser(search_param=p, search_term=term) for p in params]
        users = reduce(lambda x, y: x + y, users)
        users = {user.get('uid'): user for user in users}.values()

        return users

    def search_ecas_users(self, term):
        ecas = self.context.unrestrictedTraverse('/'+ENGINE_ID+'/acl_users/'+ECAS_ID)
        ecas_db = getattr(ecas, '_ecas_id', None)
        users = []
        if ecas_db:
            for user in ecas_db.values():
                if user.username:
                    if term in user.username:
                        result = {
                            'uid': user.username,
                            'mail': user.email
                        }
                        users.append(result)
                        continue
                if user.email:
                    if term in user.email:
                        username = user.username
                        if not username:
                            username = user.email
                        result = {
                            'uid': username,
                            'mail': user.email
                        }
                        users.append(result)

        return users

    def search_users(self):
        term = self.request.get('search_term')
        response = {}
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
        response['users'] = users

        return response

    def get_ldap_schema(self):
        return (self.get_acl_users()
                    .getLDAPSchema())

    def display_confirmation(self):
        return (self.request.get('username', None) and
               self.request.get('countries', []) and
               self.request.get('role', None))

