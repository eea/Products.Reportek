from Products.Five import BrowserView


class RevokeRoles(BrowserView):
    """TODO
    """
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

    def revoke_roles(self, paths, username):
        for path in paths:
            folder = self.context.restrictedTraverse(path)
            folder.manage_delLocalRoles(userids=[username, ])

    def get_username_information(self):
        """ Returns ('success'/'error', users_infs)
        where:
            users_infs is the result of the findUser()
        """

        containing = self.context.REQUEST.get('search_term')
        matching_criteria = self.context.REQUEST.get('search_param')

        users_infs = self.context.acl_users['ldapmultiplugin']['acl_users'].findUser(
            search_param=matching_criteria, search_term=containing)
        if users_infs[0]['sn'] == "Error":
            return ('error', )

        return ('success', users_infs)

    def get_users_LDAPSchema(self):
        return self.context.acl_users['ldapmultiplugin']['acl_users'].getLDAPSchema()
