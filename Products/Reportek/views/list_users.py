from base_admin import BaseAdmin


class ListUsers(BaseAdmin):
    """View for list_users_by_path, list_users_by_person"""

    def get_view_parent(self):
        """Returns an instance of BaseAdmin """
        return self.context.restrictedTraverse('@@template_list_users')

    def get_view(self, view_name):
        """Returns the view coresponding to the view_name"""
        if self.context.REQUEST.QUERY_STRING:
            return view_name + '?' + self.context.REQUEST.QUERY_STRING
        else:
            return view_name
