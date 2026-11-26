import unittest
from unittest.mock import Mock, patch

from AccessControl.Permissions import view_management_screens
from zExceptions import BadRequest

from Products.Reportek import config, constants, qa

from .test_qa import QATestBase


def permission_of(klass, name):
    for perm, names, *_ in klass.__ac_permissions__:
        if name in names:
            return perm
    return None


class UNSSettingsTest(unittest.TestCase):
    def setUp(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        self.klass = ReportekEngine
        self.engine = ReportekEngine()
        self.engine.UNS_password = "old-secret"

    def edit(self, password, confirmation):
        return self.engine.manage_editUNSInterface(
            "http://uns", "user", password, confirmation, "1", ["a", ""]
        )

    def test_settings_page_is_for_managers(self):
        self.assertEqual(
            permission_of(self.klass, "uns_settings"), view_management_screens
        )

    def test_password_is_not_readable(self):
        self.assertEqual(self.klass.UNS_password__roles__, ())
        self.assertNotIn("UNS_password", [p["id"] for p in self.klass._properties])

    def test_form_does_not_show_the_password(self):
        with open(self.klass.uns_settings.filename) as f:
            self.assertNotIn("here/UNS_password", f.read())

    def test_empty_fields_keep_the_password(self):
        self.assertEqual(self.edit("", ""), 1)
        self.assertEqual(self.engine.UNS_password, "old-secret")
        self.assertEqual(self.engine.UNS_username, "user")

    def test_new_password(self):
        self.assertEqual(self.edit("new", "new"), 1)
        self.assertEqual(self.engine.UNS_password, "new")

    def test_the_password_can_be_removed(self):
        self.engine.manage_editUNSInterface(
            "http://uns", "user", "", "", "1", [], UNS_password_clear=True
        )
        self.assertEqual(self.engine.UNS_password, "")

    def test_removing_wins_over_a_new_password(self):
        self.engine.manage_editUNSInterface(
            "http://uns", "user", "new", "new", "1", [], UNS_password_clear=True
        )
        self.assertEqual(self.engine.UNS_password, "")

    def test_an_empty_server_url_turns_uns_off(self):
        self.engine.manage_editUNSInterface("", "user", "", "", "1", [])
        self.assertEqual(self.engine.UNS_server, "")

    def test_confirmation_must_match(self):
        self.assertEqual(self.edit("new", "other"), 0)
        self.assertEqual(self.engine.UNS_password, "old-secret")


class EnginePropertiesUpdateTest(unittest.TestCase):
    def setUp(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        from .utils import create_fake_root

        self.root = create_fake_root()
        engine = ReportekEngine()
        engine.UNS_password = "secret"
        setattr(self.root, constants.ENGINE_ID, engine)
        self.engine = engine

    def update(self):
        from Products.Reportek.updates import u20261126_engine_properties as upd

        return upd.drop_hidden_properties(self.root)

    def test_stored_list_loses_the_password_only(self):
        self.engine._properties = (
            {"id": "title", "type": "string", "mode": "w"},
            {"id": "UNS_password", "type": "string", "mode": "w"},
            {"id": "custom", "type": "string", "mode": "w"},
        )
        self.engine.custom = "kept"
        self.assertEqual(self.engine.getProperty("UNS_password"), "secret")
        self.assertTrue(self.update())
        self.assertEqual(
            [p["id"] for p in self.engine._properties], ["title", "custom"]
        )
        self.assertIsNone(self.engine.getProperty("UNS_password"))
        self.assertNotIn("UNS_password", dict(self.engine.propertyItems()))
        self.assertEqual(self.engine.UNS_password, "secret")

    def test_class_list_is_left_alone(self):
        self.assertTrue(self.update())
        self.assertNotIn("_properties", self.engine.__dict__)
        self.assertIsNone(self.engine.getProperty("UNS_password"))


class ManageRolesTest(unittest.TestCase):
    def setUp(self):
        from Products.Reportek.views.manage_roles import ManageRoles

        self.collection = Mock(meta_type=constants.METATYPE_COLLECTION)
        self.collection.get_local_roles_for_userid.return_value = []
        self.objects = {"/de/col": self.collection, "/": Mock(meta_type="Application")}
        context = Mock()
        context.unrestrictedTraverse.side_effect = lambda path, default=None: (
            self.objects.get(path, default)
        )
        self.request = {}
        self.view = ManageRoles(context, self.request)
        self.view.get_roles = Mock(return_value=["Client", "Reporter"])

    def assign(self, role, path):
        self.request.update(
            {"role": role, "username": "someone", "collections": ["%s," % path]}
        )
        self.view.assign_role()

    def test_offered_role_on_a_collection(self):
        self.assign("Client", "/de/col")
        self.collection.manage_setLocalRoles.assert_called_once_with(
            "someone", ["Client"]
        )

    def test_other_roles_are_refused(self):
        for role in ("Manager", "Owner", ""):
            with self.assertRaises(BadRequest):
                self.assign(role, "/de/col")
        self.collection.manage_setLocalRoles.assert_not_called()

    def test_only_on_collections(self):
        for path in ("/", "/missing"):
            with self.assertRaises(BadRequest):
                self.assign("Client", path)

    def test_revoke_only_on_collections(self):
        self.request.update(
            {"username": "someone", "collections": ["/,"], "_": ["Client"]}
        )
        with self.assertRaises(BadRequest):
            self.view.revoke_roles()

    def test_bulk_revoke_only_on_collections(self):
        self.request.update({"members": ["someone"], "someone": "/de/col,/"})
        with self.assertRaises(BadRequest):
            self.view.bulk_revoke_roles()


class QANoteTextTest(QATestBase):
    def setUp(self):
        super().setUp()
        self.session = {}
        self.request = Mock(
            SESSION=Mock(set=self.session.__setitem__), RESPONSE=Mock()
        )

    def test_file_ids_from_the_request_are_escaped(self):
        self.request.form = {"x/<svg onload=alert(1)>": "42"}
        result = ["text/html", qa.QAResult("<p>report</p>")]
        with patch.object(qa, "get_qa_application", return_value=Mock()), patch.object(
            qa, "run_qa_script", return_value=("x", result)
        ):
            self.envelope.runQAScripts(self.request)
        note = self.session["note_text"]
        self.assertIn("&lt;svg onload=alert(1)&gt;", note)
        self.assertNotIn("<svg", note)
        # the QA service's own HTML is shown as it is
        self.assertIn("<p>report</p>", note)

    def test_nothing_runs_without_a_qa_application(self):
        self.request.form = {"data.xml": "42"}
        with patch.object(qa, "get_qa_application", return_value=None), patch.object(
            qa, "run_qa_script"
        ) as run:
            self.envelope.runQAScripts(self.request)
            self.envelope.runQAScript("data.xml", "42", self.request)
        run.assert_not_called()

    def test_empty_result_message_is_escaped(self):
        with patch.object(qa, "get_qa_application", return_value=Mock()), patch.object(
            qa, "run_qa_script", return_value=("x", None)
        ):
            self.envelope.runQAScript("<b>f</b>", "<i>s</i>", self.request)
        self.assertNotIn("<b>", self.session["note_text"])
        self.assertNotIn("<i>", self.session["note_text"])

    def test_qa_error_text_is_escaped(self):
        qa_app = Mock(runQAScript=Mock(side_effect=ValueError("<b>boom</b>")))
        with patch.object(qa, "get_qa_application", return_value=qa_app):
            _, (_, result) = qa.run_qa_script(
                self.envelope, "http://example.com/envelope/data.xml", "42"
            )
        self.assertEqual(result.data, "QA error: &lt;b&gt;boom&lt;/b&gt;")


@unittest.skipUnless(
    config.REPORTEK_DEPLOYMENT == config.DEPLOYMENT_BDR, "BDR only methods"
)
class BDRAuditMethodsTest(unittest.TestCase):
    def test_engine_audit_methods_are_not_published(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        for name in (
            "validate_auditor",
            "assign_for_audit",
            "unassign_for_audit",
            "get_ecr_audit_envelopes",
        ):
            self.assertEqual(getattr(ReportekEngine, name + "__roles__"), (), name)
