"""The names of the permissions and the content types are constants.

The permission names are stored in the security settings of the objects, so
the values must not change.
"""

import unittest

from AccessControl.Permissions import view_management_screens

from Products.Reportek import config, constants, permissions


class PermissionConstantsTest(unittest.TestCase):
    def test_the_permissions_are_the_ones_that_are_stored(self):
        expected = {
            "add_collections": "Add Collections",
            "add_envelopes": "Add Envelopes",
            "add_feedback": "Add Feedback",
            "audit_envelopes": "Audit Envelopes",
            "change_collections": "Change Collections",
            "change_envelopes": "Change Envelopes",
            "change_feedback": "Change Feedback",
            "manage_openflow": "Manage OpenFlow",
            "release_envelopes": "Release Envelopes",
            "use_openflow": "Use OpenFlow",
            "view_configuration": "View configuration",
            "reportek_dataflow_admin": "Reportek Dataflow Admin",
        }
        for name, value in expected.items():
            self.assertEqual(getattr(permissions, name), value, name)

    def test_the_standard_permission_is_the_one_of_zope(self):
        self.assertEqual(view_management_screens, "View management screens")

    def test_the_permissions_of_the_properties_of_the_deployment(self):
        self.assertIn(
            config.permission_manage_properties_envelopes,
            (permissions.change_envelopes, "Manage properties"),
        )
        self.assertIn(
            config.permission_manage_properties_collections,
            (permissions.change_collections, "Manage properties"),
        )

    def test_the_content_types(self):
        self.assertEqual(constants.CONTENT_TYPE_HTML, "text/html")
        self.assertEqual(constants.CONTENT_TYPE_XML, "text/xml")
        self.assertEqual(constants.CONTENT_TYPE_JSON, "application/json")

    def test_the_path_of_the_user_folder(self):
        self.assertEqual(constants.ACL_USERS_PATH, "/acl_users/")

    def test_the_label_of_the_role_of_the_owner(self):
        self.assertEqual(constants.REPORTER_OWNER_ROLE, "Reporter (Owner)")
