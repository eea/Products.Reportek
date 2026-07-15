# -*- coding: utf-8 -*-
import unittest

from OFS.Folder import Folder
from types import MethodType
from Products.PluggableAuthService.plugins.ZODBRoleManager import addZODBRoleManager
from Products.Reportek.ldap_group_roles import (
    AddGroupRoleMappingView,
    AssignRoleToPrincipalView,
    LDAPGroupRolesPlugin,
    RemoveRoleFromPrincipalView,
    UpdatePrincipalRolesView,
)
from Products.Reportek.updates.migrate_ldap import migrate_local_groups_store


DUMMY_PRINCIPAL = "dummy_ldap_user"


class Principal(object):
    def __init__(self, groups):
        self.groups = groups

    def getGroups(self):
        return self.groups


class DummyResponse(object):
    def __init__(self):
        self.redirected_to = None

    def redirect(self, url):
        self.redirected_to = url
        return url


class DummyRequest(dict):
    def __init__(self, **kw):
        super(DummyRequest, self).__init__(**kw)
        self.RESPONSE = DummyResponse()


class LDAPGroupRolesPluginTest(unittest.TestCase):
    def _plugin_with_roles(self):
        acl = Folder("acl_users")
        acl.searchPrincipals = MethodType(
            lambda self, id=None, exact_match=False, max_results=None: (), acl
        )
        addZODBRoleManager(acl, "roles")
        acl.roles.addRole("Owner", "Owner")
        plugin = LDAPGroupRolesPlugin()
        acl._setObject("ldap_group_roles", plugin)
        plugin = acl.ldap_group_roles
        plugin.absolute_url = MethodType(
            lambda self: "http://nohost/acl_users/ldap_group_roles", plugin
        )
        return acl, plugin

    def test_explicit_group_mappings(self):
        plugin = LDAPGroupRolesPlugin()
        plugin.set_mappings({"DG ENV zope role": "Manager", "eea": "Reporter"})

        roles = plugin.getRolesForPrincipal(Principal(["DG ENV zope role", "eea"]))

        self.assertEqual(set(roles), {"Manager", "Reporter"})

    def test_unmapped_groups_do_not_become_roles_by_default(self):
        plugin = LDAPGroupRolesPlugin()
        plugin.set_mappings({"eea": "Reporter"})

        roles = plugin.getRolesForPrincipal(Principal(["unmapped"]))

        self.assertEqual(roles, ())

    def test_implicit_mapping_preserves_group_as_role(self):
        plugin = LDAPGroupRolesPlugin()
        plugin.set_mappings({}, implicit_mapping=True)

        roles = plugin.getRolesForPrincipal(Principal(["DG ENV zope role"]))

        self.assertEqual(roles, ("DG ENV zope role",))

    def test_default_roles_skip_anonymous_authenticated(self):
        plugin = LDAPGroupRolesPlugin()
        plugin.set_mappings({}, default_roles=["Anonymous", "Authenticated", "Member"])

        roles = plugin.getRolesForPrincipal(Principal([]))

        self.assertEqual(roles, ("Member",))

    def test_no_principal_id_collision(self):
        plugin = LDAPGroupRolesPlugin()
        plugin.set_mappings({"same-as-user-id": "Manager"})

        roles = plugin.getRolesForPrincipal(Principal([]))

        self.assertEqual(roles, ())

    def test_manage_mapping_methods(self):
        plugin = LDAPGroupRolesPlugin()

        plugin.manage_addGroupRoleMapping("DG ENV zope role", "Manager")
        self.assertEqual(
            plugin.listGroupRoleMappings(),
            [{"group": "DG ENV zope role", "role": "Manager"}],
        )

        plugin.manage_deleteGroupRoleMappings(["DG ENV zope role"])
        self.assertEqual(plugin.listGroupRoleMappings(), [])

    def test_direct_role_assignment_helpers_create_missing_role(self):
        acl, plugin = self._plugin_with_roles()

        plugin.manage_assignRoleToPrincipal("Manager", DUMMY_PRINCIPAL)

        self.assertIn("Manager", acl.roles.listRoleIds())
        self.assertIn(
            (DUMMY_PRINCIPAL, "<%s: not found>" % DUMMY_PRINCIPAL),
            acl.roles.listAssignedPrincipals("Manager"),
        )

        principals = plugin.listDirectPrincipalRoleAssignments()
        self.assertEqual(principals[0]["principal"], DUMMY_PRINCIPAL)
        self.assertIn("Manager", principals[0]["roles"])

        plugin.manage_updatePrincipalRoles(DUMMY_PRINCIPAL, ["Owner"])
        self.assertNotIn(
            (DUMMY_PRINCIPAL, "<%s: not found>" % DUMMY_PRINCIPAL),
            acl.roles.listAssignedPrincipals("Manager"),
        )
        self.assertIn(
            (DUMMY_PRINCIPAL, "<%s: not found>" % DUMMY_PRINCIPAL),
            acl.roles.listAssignedPrincipals("Owner"),
        )

    def test_migrate_local_groups_store_converts_uid_dn_to_direct_assignment(self):
        acl, plugin = self._plugin_with_roles()

        count = migrate_local_groups_store(
            plugin,
            {
                "uid=%s,ou=Users,o=EIONET,l=Europe" % DUMMY_PRINCIPAL: [
                    "Manager"
                ]
            },
        )

        self.assertEqual(count, 1)
        self.assertIn(
            (DUMMY_PRINCIPAL, "<%s: not found>" % DUMMY_PRINCIPAL),
            acl.roles.listAssignedPrincipals("Manager"),
        )

    def test_add_mapping_browser_view_redirects_to_workspace(self):
        acl, plugin = self._plugin_with_roles()
        request = DummyRequest(group_id="eea", role_id="Manager")

        result = AddGroupRoleMappingView(plugin, request)()

        self.assertEqual(plugin.group_role_mappings["eea"], "Manager")
        self.assertEqual(result, request.RESPONSE.redirected_to)
        self.assertIn("manage_workspace", result)
        self.assertIn("Mapping%20saved", result)

    def test_assign_role_browser_view_redirects_to_workspace(self):
        acl, plugin = self._plugin_with_roles()
        request = DummyRequest(role_id="Manager", principal_id=DUMMY_PRINCIPAL)

        result = AssignRoleToPrincipalView(plugin, request)()

        self.assertIn(
            (DUMMY_PRINCIPAL, "<%s: not found>" % DUMMY_PRINCIPAL),
            acl.roles.listAssignedPrincipals("Manager"),
        )
        self.assertEqual(result, request.RESPONSE.redirected_to)
        self.assertIn("manage_workspace", result)
        self.assertIn("Role%20assigned", result)

    def test_remove_and_update_browser_views(self):
        acl, plugin = self._plugin_with_roles()
        plugin.manage_assignRoleToPrincipal("Manager", DUMMY_PRINCIPAL)
        plugin.manage_assignRoleToPrincipal("Owner", DUMMY_PRINCIPAL)

        remove_request = DummyRequest(role_id="Manager", principal_id=DUMMY_PRINCIPAL)
        remove_result = RemoveRoleFromPrincipalView(plugin, remove_request)()
        self.assertNotIn(
            (DUMMY_PRINCIPAL, "<%s: not found>" % DUMMY_PRINCIPAL),
            acl.roles.listAssignedPrincipals("Manager"),
        )
        self.assertIn("Role%20removed", remove_result)

        update_request = DummyRequest(principal_id=DUMMY_PRINCIPAL, role_ids=["Manager"])
        update_result = UpdatePrincipalRolesView(plugin, update_request)()
        self.assertIn(
            (DUMMY_PRINCIPAL, "<%s: not found>" % DUMMY_PRINCIPAL),
            acl.roles.listAssignedPrincipals("Manager"),
        )
        self.assertNotIn(
            (DUMMY_PRINCIPAL, "<%s: not found>" % DUMMY_PRINCIPAL),
            acl.roles.listAssignedPrincipals("Owner"),
        )
        self.assertIn("Principal%20roles%20updated", update_result)


if __name__ == "__main__":
    unittest.main()
