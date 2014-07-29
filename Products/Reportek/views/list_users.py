from template_list_users import TemplateListUsers


class ListUsers(TemplateListUsers):
    """View for list_users_by_path, list_users_by_person"""

    def get_view_parent(self):
        """Returns an instance of TemplateListUsers """
        return self.context.restrictedTraverse('@@template_list_users')

    def get_view(self, group_criterion):
        """Returns the view coresponding to the group_criterion"""
        if self.context.REQUEST.QUERY_STRING:
            return group_criterion + '?' + self.context.REQUEST.QUERY_STRING
        else:
            return group_criterion
