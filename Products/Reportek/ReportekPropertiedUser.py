from Products.PluggableAuthService.PropertiedUser import PropertiedUser
from Products.Reportek.constants import ENGINE_ID, ECAS_ID
import logging
logger = logging.getLogger("Reportek")


class ReportekPropertiedUser(PropertiedUser):

    def getGroups(self):
        """ Also return LDAP groups if applicable
        """
        local_groups = super(ReportekPropertiedUser, self).getGroups()

        return list(set(local_groups) | set(self.get_ldap_groups()))

    def get_roles_for_user_in_context(self, obj, user_id):
        # path of form 'fagses/ro/collection_id/some_deeper_path'

        # when creating objects in a parent, we don't have an absolute_url yet
        # look for the parent
        if not hasattr(obj, 'absolute_url'):
            # when accessing ZMI specific objects we don't have im_self either
            # if the classical authorization failed then fail this one too
            # because this is not a FGAS Portal case
            if not hasattr(obj, 'im_self'):
                return []
            obj = obj.im_self
        current_path_parts = obj.absolute_url(1).split('/')
        if len(current_path_parts) < 3:
            return []

        col_path = '/'.join(current_path_parts[:3])
        if self.get_middleware_authorization(user_id, col_path):
            return ['Owner']
        ldap_roles = self.get_ldap_role_in_context(obj, user_id)
        if ldap_roles:
            return ldap_roles
        return []

    def getRolesInContext(self, object):
        """ Return the roles in the context
        """
        basic_roles = super(ReportekPropertiedUser, self).getRolesInContext(object)
        user_id = self.getId()
        middleware_roles = self.get_roles_for_user_in_context(object, user_id)
        return list(set(basic_roles) | set(middleware_roles))

    def allowed(self, object, object_roles=None):
        basic = super(ReportekPropertiedUser, self).allowed(object, object_roles)
        if basic:
            return 1

        user_id = self.getId()
        local_roles = self.get_roles_for_user_in_context(object, user_id)
        for role in object_roles:
            if role in local_roles:
                if self._check_context(object):
                    return 1
                return None

    def get_ldap_groups(self):
        """ Return the user's ldap groups
        """
        acl_users = getattr(self, 'acl_users')
        ldapplugins = acl_users.objectIds('LDAP Multi Plugin')

        for plugin_id in ldapplugins:
            plugin = acl_users[plugin_id]
            ldapfolder = getattr(plugin, 'acl_users')

            if ldapfolder:
                user = ldapfolder.getUserById(self.getId())
                return getattr(user, '_ldap_groups', [])

        return []

    def get_ldap_role_in_context(self, obj, user_id):
        """ Return the LDAP Group's role in context
        """
        ldap_groups = self.get_ldap_groups()
        roles = []
        if ldap_groups:
            for l_group in ldap_groups:
                g_roles = obj.get_local_roles_for_userid(l_group)
                for role in g_roles:
                    if role not in roles:
                        roles.append(role)
        return roles

    def get_middleware_authorization(self, user_id, base_path):
        engine = self.unrestrictedTraverse('/'+ENGINE_ID)
        authMiddleware = engine.authMiddlewareApi
        ecas = self.unrestrictedTraverse('/acl_users/' + ECAS_ID, None)
        if ecas:
            ecas_user_id = ecas.getEcasUserId(user_id)
            logger.debug(("Attempt to interrogate middleware for authorizations "
                          "for user:id %s:%s") % (user_id, ecas_user_id))
            if not ecas_user_id:
                return False
            if authMiddleware:
                return authMiddleware.authorizedUser(ecas_user_id, base_path)
            return False
