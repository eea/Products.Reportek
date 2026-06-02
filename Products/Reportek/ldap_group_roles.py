# -*- coding: utf-8 -*-
"""PAS role plugin preserving LDAPUserFolder group-to-role mappings."""

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from App.Common import package_home
from OFS.SimpleItem import SimpleItem
from persistent.mapping import PersistentMapping
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.interfaces.plugins import IRolesPlugin
from Products.PluggableAuthService.permissions import ManageUsers
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from zope.interface import implementer

import os


PLUGIN_ID = "ldap_group_roles"
IGNORED_DEFAULT_ROLES = set(["Anonymous", "Authenticated"])


def manage_addLDAPGroupRolesPlugin(
    dispatcher, id=PLUGIN_ID, title="LDAP Group Role Mappings", RESPONSE=None
):
    plugin = LDAPGroupRolesPlugin(id, title)
    dispatcher._setObject(plugin.getId(), plugin)
    if RESPONSE is not None:
        RESPONSE.redirect("manage_workspace")


@implementer(IRolesPlugin)
class LDAPGroupRolesPlugin(BasePlugin, SimpleItem):
    """Map LDAP group ids from principal.getGroups() to Zope roles.

    This intentionally mirrors old Products.LDAPUserFolder behavior without
    assigning roles directly to group principal ids in ZODBRoleManager.
    """

    meta_type = "Reportek LDAP Group Roles Plugin"
    security = ClassSecurityInfo()
    manage_options = (
        {"label": "LDAP Role Mappings", "action": "manage_workspace"},
    ) + BasePlugin.manage_options

    manage_workspace = PageTemplateFile(
        os.path.join(package_home(globals()), "zpt/ldap_group_roles_manage.zpt")
    )

    def __init__(self, id=PLUGIN_ID, title="LDAP Group Role Mappings"):
        self._setId(id)
        self.title = title
        self.group_role_mappings = PersistentMapping()
        self.implicit_mapping = False
        self.default_roles = ()

    @security.protected(ManageUsers)
    def set_mappings(self, mappings, implicit_mapping=False, default_roles=()):
        self.group_role_mappings = PersistentMapping(dict(mappings or {}))
        self.implicit_mapping = bool(implicit_mapping)
        self.default_roles = tuple(
            role for role in default_roles or () if role not in IGNORED_DEFAULT_ROLES
        )

    @security.protected(ManageUsers)
    def listGroupRoleMappings(self):
        return [
            {"group": group, "role": role}
            for group, role in sorted(self.group_role_mappings.items())
        ]

    @security.protected(ManageUsers)
    def listAvailableRoles(self):
        roles = []
        for role in self.valid_roles():
            if role not in ("Anonymous", "Authenticated"):
                roles.append(role)
        return sorted(set(roles))

    @security.protected(ManageUsers)
    def manage_addGroupRoleMapping(self, group_id, role_id, REQUEST=None):
        group_id = group_id.strip()
        role_id = role_id.strip()
        if not group_id or not role_id:
            raise ValueError("Both LDAP group id and Zope role are required")
        self.group_role_mappings[group_id] = role_id
        self._p_changed = True
        if REQUEST is not None:
            return REQUEST.RESPONSE.redirect(
                self.absolute_url()
                + "/manage_workspace?manage_tabs_message=Mapping%20saved"
            )

    @security.protected(ManageUsers)
    def manage_deleteGroupRoleMappings(self, group_ids=(), REQUEST=None):
        for group_id in group_ids:
            self.group_role_mappings.pop(group_id, None)
        self._p_changed = True
        if REQUEST is not None:
            return REQUEST.RESPONSE.redirect(
                self.absolute_url()
                + "/manage_workspace?manage_tabs_message=Mapping%20deleted"
            )

    @security.protected(ManageUsers)
    def manage_setImplicitMapping(self, enabled=False, REQUEST=None):
        self.implicit_mapping = bool(enabled)
        self._p_changed = True
        if REQUEST is not None:
            return REQUEST.RESPONSE.redirect(
                self.absolute_url()
                + "/manage_workspace?manage_tabs_message=Implicit%20mapping%20saved"
            )

    @security.protected(ManageUsers)
    def searchPrincipals(self, search):
        if not search:
            return []
        acl = self.aq_parent
        results = []
        for item in acl.searchPrincipals(id=search, exact_match=False, max_results=50):
            item = dict(item)
            item["type"] = item.get("login") and "user" or "group"
            item["title"] = item.get("login") or item.get("title") or item.get("id")
            results.append(item)
        return results

    @security.protected(ManageUsers)
    def _principal_info(self, principal_id):
        acl = self.aq_parent
        try:
            matches = acl.searchPrincipals(id=principal_id, exact_match=True)
        except Exception:
            matches = ()
        for match in matches:
            info = dict(match)
            pluginid = info.get("pluginid") or info.get("plugin_id") or ""
            principal_type = info.get("login") and "user" or "group"
            if pluginid == "ldap":
                source = "LDAP"
            elif pluginid:
                source = "Local/PAS ({})".format(pluginid)
            else:
                source = "Unknown"
            return {
                "source": source,
                "pluginid": pluginid,
                "type": principal_type,
                "title": info.get("login") or info.get("title") or principal_id,
            }
        return {
            "source": "Unknown / not found",
            "pluginid": "",
            "type": "unknown",
            "title": "<{}: not found>".format(principal_id),
        }

    @security.protected(ManageUsers)
    def listDirectRoleAssignments(self):
        acl = self.aq_parent
        roles_plugin = getattr(acl, "roles", None)
        if roles_plugin is None:
            return []
        rows = []
        for role in self.listAvailableRoles():
            for principal, title in roles_plugin.listAssignedPrincipals(role):
                info = self._principal_info(principal)
                rows.append(
                    {
                        "role": role,
                        "principal": principal,
                        "title": info["title"] or title,
                        "source": info["source"],
                        "type": info["type"],
                        "pluginid": info["pluginid"],
                    }
                )
        return rows

    @security.protected(ManageUsers)
    def manage_assignRoleToPrincipal(self, role_id, principal_id, REQUEST=None):
        self.aq_parent.roles.assignRoleToPrincipal(role_id, principal_id.strip())
        if REQUEST is not None:
            return REQUEST.RESPONSE.redirect(
                self.absolute_url()
                + "/manage_workspace?manage_tabs_message=Role%20assigned"
            )

    @security.protected(ManageUsers)
    def listDirectPrincipalRoleAssignments(self):
        by_principal = {}
        for row in self.listDirectRoleAssignments():
            principal = row["principal"]
            if principal not in by_principal:
                by_principal[principal] = {
                    "principal": principal,
                    "title": row["title"],
                    "source": row["source"],
                    "type": row["type"],
                    "pluginid": row["pluginid"],
                    "roles": [],
                }
            by_principal[principal]["roles"].append(row["role"])
        available = self.listAvailableRoles()
        rows = []
        for principal, row in sorted(by_principal.items()):
            assigned = set(row["roles"])
            row["roles"] = sorted(assigned)
            row["available_roles"] = [
                {"id": role, "assigned": role in assigned} for role in available
            ]
            row["unassigned_roles"] = [
                role for role in available if role not in assigned
            ]
            rows.append(row)
        return rows

    @security.protected(ManageUsers)
    def manage_updatePrincipalRoles(self, principal_id, role_ids=(), REQUEST=None):
        principal_id = principal_id.strip()
        role_ids = set(role_ids or ())
        roles_plugin = self.aq_parent.roles
        for role in self.listAvailableRoles():
            if role in role_ids:
                roles_plugin.assignRoleToPrincipal(role, principal_id)
            else:
                roles_plugin.removeRoleFromPrincipal(role, principal_id)
        if REQUEST is not None:
            return REQUEST.RESPONSE.redirect(
                self.absolute_url()
                + "/manage_workspace?manage_tabs_message=Principal%20roles%20updated"
            )

    @security.protected(ManageUsers)
    def manage_removeRoleFromPrincipal(self, role_id, principal_id, REQUEST=None):
        self.aq_parent.roles.removeRoleFromPrincipal(role_id, principal_id)
        if REQUEST is not None:
            return REQUEST.RESPONSE.redirect(
                self.absolute_url()
                + "/manage_workspace?manage_tabs_message=Role%20removed"
            )

    @security.private
    def getRolesForPrincipal(self, principal, request=None):
        roles = []
        groups = getattr(principal, "getGroups", lambda: ())() or ()

        for group in groups:
            if self.implicit_mapping and group not in roles:
                roles.append(group)
            mapped = self.group_role_mappings.get(group)
            if mapped and mapped not in roles:
                roles.append(mapped)

        for role in self.default_roles:
            if role not in roles:
                roles.append(role)

        return tuple(roles)


InitializeClass(LDAPGroupRolesPlugin)
