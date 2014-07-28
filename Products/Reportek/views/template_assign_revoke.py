from template_users_admin import TemplateUsersAdmin


class TemplateAssignRevoke(TemplateUsersAdmin):
    def get_title(self):
        """ Returns the title of the view """
#        raise NotImplemented
        return "TEMPLATE"

    def get_select_user_legend(self):
        """ Returns the """
#        raise NotImplemented
        return "TEMPLATE_SELECT_USERS"

    def get_users_LDAPSchema(self):
        return self.context.acl_users['ldapmultiplugin']['acl_users'].getLDAPSchema()

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
