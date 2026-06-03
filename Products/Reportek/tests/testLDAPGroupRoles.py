# -*- coding: utf-8 -*-
import unittest

from OFS.Folder import Folder
from types import MethodType
from Products.PluggableAuthService.plugins.ZODBRoleManager import addZODBRoleManager
from Products.Reportek.ldap_group_roles import LDAPGroupRolesPlugin


class Principal(object):
    def __init__(self, groups):
        self.groups = groups

    def getGroups(self):
        return self.groups


class LDAPGroupRolesPluginTest(unittest.TestCase):
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

    def test_direct_role_assignment_helpers(self):
        acl = Folder("acl_users")
        acl.searchPrincipals = MethodType(
            lambda self, id=None, exact_match=False: (), acl
        )
        addZODBRoleManager(acl, "roles")
        acl.roles.addRole("Owner", "Owner")
        plugin = LDAPGroupRolesPlugin()
        acl._setObject("ldap_group_roles", plugin)
        plugin = acl.ldap_group_roles

        plugin.manage_assignRoleToPrincipal("Manager", "robaaoli")

        self.assertIn(
            ("robaaoli", "<robaaoli: not found>"),
            acl.roles.listAssignedPrincipals("Manager"),
        )

        principals = plugin.listDirectPrincipalRoleAssignments()
        self.assertEqual(principals[0]["principal"], "robaaoli")
        self.assertIn("Manager", principals[0]["roles"])

        plugin.manage_updatePrincipalRoles("robaaoli", ["Owner"])
        self.assertNotIn(
            ("robaaoli", "<robaaoli: not found>"),
            acl.roles.listAssignedPrincipals("Manager"),
        )
        self.assertIn(
            ("robaaoli", "<robaaoli: not found>"),
            acl.roles.listAssignedPrincipals("Owner"),
        )


if __name__ == "__main__":
    unittest.main()
