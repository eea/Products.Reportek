import logging

from Products.PluggableAuthService.PropertiedUser import PropertiedUser
from Products.Reportek.config import DEPLOYMENT_CDR as CDR
from Products.Reportek.config import REPORTEK_DEPLOYMENT
from Products.Reportek.constants import ECAS_ID, ENGINE_ID

logger = logging.getLogger("Reportek")


class ReportekPropertiedUser(PropertiedUser):
    def getGroups(self):
        """Also return LDAP groups for CDR deployments.

        LDAP groups are now provided by pas.plugins.ldap via PAS IGroupsPlugin.
        Do not query the legacy Products.LDAPUserFolder here: doing so performs
        LDAP bind/search calls while PAS is resolving roles and can exhaust all
        Waitress workers when LDAP is slow.
        """
        local_groups = super(ReportekPropertiedUser, self).getGroups()
        if REPORTEK_DEPLOYMENT == CDR:
            return list(set(local_groups) | set(self.get_ldap_groups()))

        return local_groups

    def get_roles_for_user_in_context(self, obj, user_id):
        # path of form 'fagses/ro/collection_id/some_deeper_path'

        # when creating objects in a parent, we don't have an absolute_url yet
        # look for the parent
        if not hasattr(obj, "absolute_url"):
            # when accessing ZMI specific objects we don't have im_self either
            # if the classical authorization failed then fail this one too
            # because this is not a FGAS Portal case
            if not hasattr(obj, "im_self"):
                return []
            obj = obj.__self__
        current_path_parts = obj.absolute_url(1).split("/")
        if len(current_path_parts) < 3:
            return []

        col_path = "/".join(current_path_parts)
        m_auth = self.get_middleware_authorization(user_id, col_path)
        if m_auth:
            return {
                "RW": ["Owner"],
                "RO": ["Reader"],
                "AUDIT": ["AuditorFgas"],
            }.get(m_auth)
        ldap_roles = self.get_ldap_role_in_context(obj, user_id)
        if ldap_roles:
            return ldap_roles
        return []

    def getRolesInContext(self, object):
        """Return the roles in the context"""
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
        """Return LDAP/PAS groups without using legacy LDAPUserFolder.

        During migration, pas.plugins.ldap became responsible for LDAP group
        enumeration. The ldap_group_roles PAS plugin then maps these group ids
        to Zope roles. Calling the old LDAP Multi Plugin/LDAPUserFolder here
        re-enters LDAP during authorization and can block all Waitress workers.
        """
        return super(ReportekPropertiedUser, self).getGroups()

    def get_ldap_role_in_context(self, obj, user_id):
        """Return the LDAP Group's role in context"""
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
        engine = self.unrestrictedTraverse("/" + ENGINE_ID)
        authMiddleware = engine.authMiddleware
        ecas = self.unrestrictedTraverse("/acl_users/" + ECAS_ID, None)
        if ecas:
            ecas_user_id = ecas.getEcasUserId(user_id)
            logger.debug(
                (
                    "Attempt to interrogate middleware for "
                    "authorizations for user:id %s:%s"
                )
                % (user_id, ecas_user_id)
            )
            if not ecas_user_id:
                return False
            if authMiddleware:
                userdata = {"username": user_id, "ecas_id": ecas_user_id}
                return authMiddleware.authorizedUser(
                    ecas_user_id, base_path, userdata=userdata
                )
            return False
