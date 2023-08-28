import json

from Products.Five import BrowserView


class RolesMGMTAPI(BrowserView):
    """Roles management view, specific for BDR Registry colls"""

    def add_owner(self, obj, user):
        """Add the owner role for user on obj"""
        roles = set(obj.get_local_roles_for_userid(user.getId()))
        roles.add('Owner')
        obj.manage_setLocalRoles(user.getId(), list(roles))
        obj.reindexObject()

    def remove_owner(self, obj, user):
        """Remove the role owner for user on obj"""
        roles = set(obj.get_local_roles_for_userid(user.getId()))
        if 'Owner' in roles:
            roles.remove('Owner')
            obj.manage_delLocalRoles([user.getId()])
            if roles:
                obj.manage_setLocalRoles(user.getId(), list(roles))
            obj.reindexObject()

    def manage_ownership(self):
        """Manage the Owner role for a user on a collection"""
        self.request.RESPONSE.setHeader("Content-Type", "application/json")
        if self.request.method == 'POST':
            data = json.loads(self.request.get("BODY") or "{}")
            uid = data.get('uid', '').encode('utf-8')
            obl_folder = data.get('obl_folder', '').encode('utf-8')
            country = data.get('country', '').encode('utf-8')
            c_folder = data.get('c_folder', '').encode('utf-8')
            action = data.get('action', '').encode('utf-8')
            user = None
            wrapped_user = None
            res = {
                'message': '',
                'errors': []
            }
            has_action = action and action in ["add", "remove"]
            if uid and obl_folder and country and c_folder and has_action:
                c_path = '/'.join([obl_folder, country, c_folder])
                obj = self.context.unrestrictedTraverse(c_path, None)
                try:
                    user = self.context.acl_users.getUser(uid)
                    wrapped_user = user.__of__(self.context.acl_users)
                except Exception:
                    error = {
                        'title': 'Error',
                        'description': 'User not found'
                    }
                    res['errors'].append(error)
                if wrapped_user:
                    if obj:
                        try:
                            if action == 'add':
                                self.add_owner(obj, wrapped_user)
                            elif action == 'remove':
                                self.remove_owner(obj, wrapped_user)
                            res['message'] = 'Operation completed'
                        except Exception as e:
                            error = {
                                'title': 'Error',
                                'description': str(e)
                            }
                            res['errors'].append(error)
                    else:
                        error = {
                            'title': 'Error',
                            'description': 'Collection not found: {}'.format(
                                c_path)
                        }
                        res['errors'].append(error)
            else:
                self.request.RESPONSE.setStatus(400)
                error = {
                    'title': 'Error',
                    'description': 'Bad request'
                }
                res['errors'].append(error)
            return json.dumps(res)
