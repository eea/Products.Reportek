from base_admin import BaseAdmin


class ManageRoles(BaseAdmin):
    """ ManageRoles view """

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

    def get_collections(self):
        obligations = self.context.REQUEST.get('obligations', [])
        countries = self.context.REQUEST.get('countries', [])
        user = self.context.REQUEST.get('username', '')

        results = []
        for brain in self.search_catalog(obligations,
                                         countries,
                                         role='',
                                         users=user):

            record_obligations = []
            for uri in list(brain.dataflow_uris):
                try:
                    title = self.get_obligations_title()[uri]
                except KeyError:
                    title = 'Unknown/Deleted obligation'
                record_obligations.append({
                    'uri': uri,
                    'title': title
                })

            results.append({
                'path': brain.getPath(),
                'country': brain.getCountryName,
                'obligations': record_obligations,
                'roles': brain.local_defined_roles,
            })

        return results

    def revoke_roles(self):
        collections = self.context.REQUEST.get('collections', [])
        username = self.context.REQUEST.get('username', '')
        for collection in collections:
            obj = self.context.unrestrictedTraverse(collection)
            obj.manage_delLocalRoles(userids=[username])
            obj.reindex_object()

    def search_ldap_users(self):
        search_term = self.context.REQUEST.get('search_term')
        search_param = self.context.REQUEST.get('search_param')

        users = (self.context
                     .acl_users['ldapmultiplugin']['acl_users']
                     .findUser(search_param=search_param,
                               search_term=search_term))

        response = {'users': users}

        if (users and users[0]['sn'] == 'Error'):
            response['errors'] = True

        return response


    def get_ldap_schema(self):
        return (self.context
                    .acl_users['ldapmultiplugin']['acl_users']
                    .getLDAPSchema())
