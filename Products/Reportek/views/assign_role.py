from template_assign_revoke import TemplateAssignRevoke


class AssignRole(TemplateAssignRevoke):
    """ TODO: """

    def get_view_parent(self):
        """Returns an instance of TemplateUsersAdmin """
        return self.context.restrictedTraverse('@@template_assign_revoke')

    def get_title(self):
        """ Returns the title of the view """
        return "Assign Role"

    def get_select_user_legend(self):
        """ Returns the title of the view """
        return "Select user(s) to assign 'Client' role"

    def get_username_information(self):
        """ Returns ('success'/'error', users_infs)
        where:
            users_infs is the result of the findUser()
        """
        containing = self.context.REQUEST.get('search_term')
        matching_criteria = self.context.REQUEST.get('search_param')

        users_infs = self.context.acl_users['ldapmultiplugin']['acl_users'].findUser(
            search_param=matching_criteria, search_term=containing)

        if (users_infs and users_infs[0]['sn'] == "Error"):
            return ('error', )

        return ('success', users_infs)

    def get_all_countries(self):
        """TODO: verify why the function don't return Algeria, Egypt, Lybia"""
        return [country for country in self.context.Catalog.uniqueValuesFor(
                'getCountryName') if country not in ['', 'Unknown']]

    def get_XXX(self):
        crole = 'Client'
        query = {
            'dataflow_uris':  '',
            'meta_type': 'Report Collection',
        }

        catalog = self.context.Catalog
        brains = catalog(**query)

        countries = []
        res = []
        for brain in brains:
            doc = brain.getObject()
            try:
                country = doc.getCountryCode()
            except KeyError:
                continue
            if country.lower() not in countries:
                continue
            for user in []:
                doc.manage_setLocalRoles(user, [crole, ])
            res.append(doc)
        return res
