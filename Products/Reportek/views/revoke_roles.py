from Products.Five import BrowserView


class RevokeRoles(BrowserView):
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
