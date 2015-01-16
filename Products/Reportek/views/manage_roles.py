from base_admin import BaseAdmin


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

    def search_ldap_users(self):
        search_term = self.request.get('search_term')
        search_param = self.request.get('search_param')

        users = (self.get_acl_users()
                 .findUser(search_param=search_param,
                           search_term=search_term))

        response = {'users': users}

        if (users and users[0]['sn'] == 'Error'):
            response['errors'] = True

        return response

    def get_ldap_schema(self):
        return (self.get_acl_users()
                    .getLDAPSchema())

    def display_confirmation(self):
        return (self.request.get('username', None) and
               self.request.get('countries', []) and
               self.request.get('role', None))

