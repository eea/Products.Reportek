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
        self.engine.UNS_password = "old-secret"  # betterleaks:allow (test fixture)

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


class UNSClientTest(unittest.TestCase):
    """The UNS credentials never show in errors, logs or redirects."""

    PASSWORD = "uns-s3cret"  # betterleaks:allow (test fixture)

    def setUp(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        self.engine = ReportekEngine()
        self.engine.UNS_server = "http://127.0.0.1:1"
        self.engine.UNS_username = "uns_user"
        self.engine.UNS_password = self.PASSWORD  # betterleaks:allow (test fixture)
        self.engine.UNS_channel_id = "1"
        patcher = patch.object(
            ReportekEngine, "uns_notifications_enabled", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def serve(self, status):
        """A UNS answering every call with ``status``; returns the
        Authorization headers it received."""
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                received.append(self.headers.get("Authorization"))
                self.send_response(status)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.engine.UNS_server = "http://127.0.0.1:%d" % server.server_address[1]
        return received

    def test_errors_do_not_show_the_password(self):
        import base64
        import xmlrpc.client

        received = self.serve(503)
        proxy = self.engine.get_uns_xmlrpc_server()
        with self.assertRaises(xmlrpc.client.ProtocolError) as cm:
            proxy.UNSService.canSubscribe("1", "someone")
        self.assertIn("503", str(cm.exception))
        self.assertNotIn(self.PASSWORD, str(cm.exception))
        self.assertNotIn(self.PASSWORD, repr(proxy))
        # still authenticated, with a header
        credentials = "uns_user:%s" % self.PASSWORD
        self.assertEqual(
            received, ["Basic " + base64.b64encode(credentials.encode()).decode()]
        )

    def test_https_and_no_username(self):
        import xmlrpc.client

        self.engine.UNS_server = "https://uns.example.com"
        proxy = self.engine.get_uns_xmlrpc_server()
        transport = proxy._ServerProxy__transport
        self.assertIsInstance(transport, xmlrpc.client.SafeTransport)
        self.assertEqual([name for name, _ in transport._headers], ["Authorization"])
        # without a username, no credentials are sent
        self.engine.UNS_username = ""
        proxy = self.engine.get_uns_xmlrpc_server()
        self.assertEqual(proxy._ServerProxy__transport._headers, [])

    def test_failed_subscription_does_not_show_the_error(self):
        self.serve(500)
        user = Mock()
        user.getUserName.return_value = "someone"
        self.engine.REQUEST = {"AUTHENTICATED_USER": user}
        request = Mock()
        with patch("Products.Reportek.ReportekEngine.logger") as logger:
            ok, message = self.engine.subscribeToUNS(REQUEST=request)
        self.assertEqual(ok, 0)
        [url] = request.RESPONSE.redirect.call_args[0]
        self.assertIn("info_title=Error", url)
        self.assertNotIn("ProtocolError", url)
        self.assertNotIn("127.0.0.1", url)
        self.assertNotIn(self.PASSWORD, url)
        logged = str(logger.warning.call_args)
        self.assertIn("500", logged)
        self.assertNotIn(self.PASSWORD, logged)

    def test_a_refusal_by_uns_is_shown(self):
        import xmlrpc.client
        from urllib.parse import parse_qs, urlparse

        user = Mock()
        user.getUserName.return_value = "someone"
        self.engine.REQUEST = {"AUTHENTICATED_USER": user}
        server = Mock()
        server.UNSService.makeSubscription.side_effect = xmlrpc.client.Fault(
            1, "Not allowed & <b>no</b>"
        )
        request = Mock()
        with patch.object(
            self.engine, "get_uns_xmlrpc_server", return_value=server
        ), patch("Products.Reportek.ReportekEngine.logger"):
            self.engine.subscribeToUNS(REQUEST=request)
        [url] = request.RESPONSE.redirect.call_args[0]
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["info_title"], ["Error"])
        self.assertEqual(
            query["info_msg"],
            ["Your subscription could not be made: Not allowed & <b>no</b>"],
        )


class EnginePropertiesUpdateTest(unittest.TestCase):
    def setUp(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        from .utils import create_fake_root

        self.root = create_fake_root()
        engine = ReportekEngine()
        engine.UNS_password = "secret"  # betterleaks:allow (test fixture)
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
        self.request = Mock(SESSION=Mock(set=self.session.__setitem__), RESPONSE=Mock())

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

    def test_unviewable_file_asks_to_log_in(self):
        from zExceptions import Unauthorized

        self.doc.manage_permission("View", ["Manager"], acquire=0)
        url = "http://example.com/envelope/data.xml"
        self.request.form = {url: "42"}
        with patch.object(qa, "get_qa_application", return_value=Mock()):
            with self.assertRaises(Unauthorized):
                self.envelope.runQAScript(url, "42", self.request)
            with self.assertRaises(Unauthorized):
                self.envelope.runQAScripts(self.request)

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


class SafeRedirectTest(unittest.TestCase):
    def setUp(self):
        self.context = Mock(
            absolute_url=Mock(return_value="https://cdr.example/de/env"),
            REQUEST={"SERVER_URL": "https://cdr.example"},
        )

    def check(self, url):
        from Products.Reportek.RepUtils import safe_redirect_url

        return safe_redirect_url(url, self.context)

    def test_same_site_urls_are_kept(self):
        for url in (
            "note",
            "/de/env/overview",
            "../other?x=1",
            "https://cdr.example/de/env",
            "http://CDR.example/x",
        ):
            self.assertEqual(self.check(url), url.strip(), url)

    def test_other_places_go_to_the_context(self):
        for url in (
            "https://evil.example/",
            "//evil.example/x",
            "/\\evil.example",
            "javascript:alert(1)",
            "data:text/html,x",
            "https://cdr.example.evil.example/",
            "http:evil.example",
            "",
            None,
            "/x\r\nSet-Cookie: a=b",
        ):
            self.assertEqual(self.check(url), "https://cdr.example/de/env", url)


class ValidateFileUrlTest(unittest.TestCase):
    def test_external_urls_are_refused(self):
        from Products.Reportek.Converter import validate_file_url

        for url in ("https://evil", "//evil/x", " //evil", "\\\\evil\\x", "/\\evil"):
            with self.assertRaises(BadRequest, msg=url):
                validate_file_url(url)
        for url in ("de/env/data.xml", "/de/env/data.xml", "", None):
            validate_file_url(url)


class ZipAndExportFilterTest(unittest.TestCase):
    def setUp(self):
        from .common import BaseTest
        from .utils import add_document, create_envelope, create_fake_root
        from .utils import create_upload_file

        self.root = create_fake_root()
        self.engine = BaseTest.create_reportek_engine(self.root)
        self.envelope = create_envelope(self.root)
        add_document(self.envelope, create_upload_file("x", "foo.txt"))
        self.envelope.released = True
        self.envelope.title = "Env"

    def security(self, user="someone", can_view=True):
        sm = Mock()
        sm.getUser.return_value.getUserName.return_value = user
        sm.checkPermission.return_value = can_view
        return patch(
            "Products.Reportek.ReportekEngine.getSecurityManager", return_value=sm
        )

    def zip_names(self, **kwargs):
        import zipfile
        from io import BytesIO

        with self.security(**kwargs):
            body = self.engine.zipEnvelopes(["/envelope", "/missing"], Mock(), Mock())
        with zipfile.ZipFile(BytesIO(b"".join(body))) as z:
            return z.namelist()

    def test_logged_in_user_gets_the_history(self):
        self.assertIn("Env/history.txt", self.zip_names())

    def test_anonymous_gets_no_history(self):
        names = self.zip_names(user="Anonymous User")
        self.assertIn("Env/metadata.txt", names)
        self.assertNotIn("Env/history.txt", names)

    def test_envelopes_the_user_cannot_view_are_left_out(self):
        self.assertEqual(self.zip_names(can_view=False), [])

    def test_zip_is_declared(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        self.assertEqual(permission_of(ReportekEngine, "zipEnvelopes"), "View")

    def test_export_leaves_out_what_the_user_cannot_view(self):
        self.envelope.get_export_data = Mock(return_value={})
        self.engine.download_xls = Mock(return_value=b"xls")
        with self.security(can_view=False):
            self.engine.xls_export(envelopes=["/envelope", "/missing"])
        self.envelope.get_export_data.assert_not_called()


class SubscribeAllActorsTest(QATestBase):
    def call(self, published):
        sm = Mock()
        sm.getUser.return_value.getUserName.return_value = "Anonymous User"
        self.root.REQUEST = {"PUBLISHED": published}
        # no UNS server: nothing is sent
        setattr(self.root, constants.ENGINE_ID, Mock(UNS_server=""))
        with patch(
            "Products.Reportek.EnvelopeCustomDataflows.getSecurityManager",
            return_value=sm,
        ):
            return self.envelope.subscribe_all_actors()

    def test_anonymous_request_by_url_is_refused(self):
        from zExceptions import Unauthorized

        with self.assertRaises(Unauthorized):
            self.call(self.envelope.subscribe_all_actors)

    def test_workflow_scripts_still_call_it(self):
        # released through a workflow step, whoever triggered it
        self.call(self.envelope.completeWorkitem)


class MigrationTableTest(unittest.TestCase):
    def setUp(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        self.engine = ReportekEngine()
        self.engine._migration_rows = Mock(
            return_value=(
                [],
                [
                    {"name": "u_pending", "applicable": True, "version": 2},
                    {"name": "u_other", "applicable": False, "version": 1},
                ],
            )
        )
        self.engine._migration_table = Mock(return_value="page")
        self.engine.unrestrictedTraverse = Mock()
        patches = [
            patch("Products.Reportek.ReportekEngine.importlib"),
            patch("Products.Reportek.ReportekEngine.CheckAuthenticator"),
        ]
        self.importlib, self.check_authenticator = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)

    def run_update(self, name, method="POST"):
        self.engine.REQUEST = Mock(form={"update": name})
        self.engine.REQUEST.__getitem__ = Mock(return_value=method)
        return self.engine.migration_table()

    def test_pending_update_runs_with_post_and_token(self):
        self.assertEqual(self.run_update("u_pending"), "page")
        self.check_authenticator.assert_called_once()
        self.importlib.import_module.assert_called_once_with(
            "Products.Reportek.updates.u_pending"
        )

    def test_get_is_refused(self):
        with self.assertRaises(BadRequest):
            self.run_update("u_pending", method="GET")
        self.importlib.import_module.assert_not_called()

    def test_other_modules_are_refused(self):
        for name in ("u_other", "cleanup_staging", "../x"):
            with self.assertRaises(BadRequest, msg=name):
                self.run_update(name)
        self.importlib.import_module.assert_not_called()

    def test_listing_without_update(self):
        self.engine.REQUEST = Mock(form={})
        self.assertEqual(self.engine.migration_table(), "page")
        self.importlib.import_module.assert_not_called()


X = "python: 6*7"
TAL = "http://xml.zope.org/namespaces/tal"


class SafeToCompileTest(unittest.TestCase):
    def check(self, html):
        from Products.Reportek.Feedback import is_safe_to_compile

        return is_safe_to_compile(html)

    def test_feedback_markup_is_compiled(self):
        for html in (
            "",
            "plain text: 3 errors, 100% done, a = b",
            # BDR QA feedback
            '<div xmlns:i18n="http://namespaces.zope.org/i18n"><p class="x" '
            'i18n:translate="">Found <span i18n:name="n">3</span></p></div>',
            '<p xmlns:i8n="http://namespaces.zope.org/i8n" i8n:translate="">a</p>',
            "<script>function toggle(divName, linkName) { if (a > b) {} }</script>"
            "<a href=\"javascript:toggle('d', 'l')\">x</a>",
            # CDR QA feedback quoting reported data
            '<r xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="a b">x</r>',
            '<td aqd:change="true">x</td>',
            '<rsm:NationalID xmlns:rsm="urn:eu:com:env:prtr:data:standard:2">'
            "1</rsm:NationalID>",
            '<?xml:namespace prefix = o ns = "urn:schemas-microsoft-com:office:'
            'office" /><o:p>w</o:p>',
            '<?xml version="1.0"?><p xmlns="http://www.w3.org/1999/xhtml">x</p>',
            # inert: the engine interpolates nothing in feedback
            "<script>var s = `${a}`;</script><p>${b}</p>",
            "<p>total: 5</p><p>metal: iron</p><td>tal:foo</td>",
        ):
            self.assertTrue(self.check(html), html)

    def test_template_code_is_not_compiled(self):
        for html in (
            '<p tal:content="%s">a</p>' % X,
            '<p TAL:content="%s">a</p>' % X,
            "<p tal:content=python:6*7>a</p>",
            '<p/tal:content="%s">a</p>' % X,
            '<p a="1"tal:content="%s">a</p>' % X,
            '<p tal:con i18n:data="1"tent="%s">a</p>' % X,
            '<tal:x replace="%s">c</tal:x>' % X,
            '<metal:block define-macro="m">x</metal:block>',
            '<div metal:use-macro="here/x">y</div>',
            '<p meta:interpolation="true">${%s}</p>' % X,
            '<i18n:x translate="">a</i18n:x>',
            '<p i18n:translate="" i18n:data="%s">a</p>' % X,
            '<p data-tal-content="%s">a</p>' % X,
            '<p DATA-METAL-use-macro="x">a</p>',
            "a<?python x = 1 ?>b",
        ):
            self.assertFalse(self.check(html), html)

    def test_template_namespaces_under_any_prefix(self):
        for uri in (
            TAL,
            TAL + "/",
            " %s " % TAL,
            TAL.upper(),
            "http://xml.zope.org/namespaces/metal",
            "http://xml.zope.org/namespaces/i18n",
            "http://xml.zope.org/namespaces/meta",
            "http://xml.zope.org/namespaces/&#116;al",
            "http://xml.zope.org/namespaces/&#x74;&#x61;l",
            "http:&#47;&#47;xml.zope.org&#47;namespaces&#47;tal",
        ):
            for html in (
                '<p xmlns:z="%s" z:content="%s">a</p>' % (uri, X),
                "<p xmlns:z='%s' z:content='%s'>a</p>" % (uri, X),
                '<p xmlns="%s">a</p>' % uri,
            ):
                self.assertFalse(self.check(html), html)
        # unquoted, unclosed, spaced or upper case declarations
        for html in (
            '<p xmlns:z=%s z:content="%s">a</p>' % (TAL, X),
            '<p xmlns:z="%s z:content="%s">a</p>' % (TAL, X),
            '<p xmlns:z = "%s" z:content="%s">a</p>' % (TAL, X),
            '<p XMLNS:z="%s" z:content="%s">a</p>' % (TAL, X),
        ):
            self.assertFalse(self.check(html), html)

    def test_runs_in_linear_time(self):
        import time

        for html in (
            "<p" + " " * 40000,
            "a:b=" * 40000,
            ' xmlns:a="x"' * 20000,
            ' xmlns:a="' * 20000,
            "<a:" * 40000,
        ):
            started = time.time()
            self.check(html)
            self.assertLess(time.time() - started, 1, html[:20])
