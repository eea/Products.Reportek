"""QA runs only in the QA application; local QA scripts and in-process
converters, which ran stored command lines on the Zope host, are gone."""

import inspect
from unittest.mock import Mock, patch

from OFS.Folder import Folder

from Products.Reportek import constants, qa
from Products.Reportek.QARepository import QARepository
from Products.Reportek.QAScript import QAScript

from .common import BaseUnitTest
from .utils import add_document, create_envelope, create_fake_root, create_upload_file


class Engine:
    """Stands in for ReportekEngine: only the attributes qa.py reads."""

    QA_application = ""
    qa_httpres = False

    def __init__(self):
        # add_document scans uploads with the engine's AV service
        self.AVService = Mock()


def legacy_qa_script(script_id, script_url="x %s"):
    """A QAScript as it is stored in an old Data.fs."""
    script = QAScript.__new__(QAScript)
    script.__setstate__(
        {
            "id": script_id,
            "title": script_id,
            "xml_schema": "schema.xsd",
            "workflow": "",
            "content_type_in": "",
            "script_url": script_url,
            "max_size": 10.0,
            "qa_extraparams": [],
        }
    )
    return script


def add_legacy_repository(root, qa_application="", scripts=()):
    repo = QARepository()
    repo.id = constants.QAREPOSITORY_ID
    repo.QA_application = qa_application
    root._setObject(constants.QAREPOSITORY_ID, repo)
    repo = root[constants.QAREPOSITORY_ID]
    for script_id in scripts:
        repo._setObject(script_id, legacy_qa_script(script_id))
    return repo


class QATestBase(BaseUnitTest):
    def setUp(self):
        self.root = create_fake_root()
        self.engine = Engine()
        setattr(self.root, constants.ENGINE_ID, self.engine)
        # not a WebDAV client, or traversal yields NullResource for missing ids
        self.root.REQUEST = Mock(
            SERVER_URL="http://example.com", maybe_webdav_client=False
        )
        self.envelope = create_envelope(self.root)
        self.envelope.getMySelf = Mock(side_effect=Exception("no process"))
        self.doc = add_document(self.envelope, create_upload_file("<a/>", "data.xml"))
        self.doc.xml_schema_location = "schema.xsd"
        self.mappings = Mock(getSchemasForDataflows=Mock(return_value=[]))
        setattr(self.root, constants.DATAFLOW_MAPPINGS, self.mappings)
        # a public site: anonymous users can view the files
        self.root.manage_permission("View", ["Anonymous"], acquire=1)

    def add_qa_application(self, path=("Applications", "QAApp")):
        parent = self.root
        for name in path:
            parent._setObject(name, Folder(name))
            parent = parent[name]
        return parent


class GetQAApplicationTest(QATestBase):
    def test_engine_property(self):
        app = self.add_qa_application()
        self.engine.QA_application = "Applications/QAApp"
        self.assertEqual(qa.get_qa_application(self.envelope), app)

    def test_none_when_not_configured(self):
        self.assertIsNone(qa.get_qa_application(self.envelope))

    def test_legacy_repository_value_until_migrated(self):
        app = self.add_qa_application()
        add_legacy_repository(self.root, qa_application="Applications/QAApp")
        self.assertEqual(qa.get_qa_application(self.envelope), app)

    def test_legacy_repository_value_wins_while_it_exists(self):
        # before the update it is the value that was in effect; the engine
        # property was not read by anything
        self.add_qa_application()
        legacy = self.add_qa_application(("Legacy",))
        add_legacy_repository(self.root, qa_application="Legacy")
        self.engine.QA_application = "Applications/QAApp"
        self.assertEqual(qa.get_qa_application(self.envelope), legacy)

    def test_engine_property_when_legacy_repository_has_none(self):
        app = self.add_qa_application()
        add_legacy_repository(self.root, qa_application="")
        self.engine.QA_application = "Applications/QAApp"
        self.assertEqual(qa.get_qa_application(self.envelope), app)

    def test_automatic_qa_activity_mapping_wins(self):
        self.add_qa_application()
        mapped = self.add_qa_application(("Mapped",))
        self.engine.QA_application = "Applications/QAApp"
        aqa = Mock(mapped_application_details=Mock(return_value={"path": "Mapped"}))
        process = Mock(
            listActivities=Mock(return_value=["AutomaticQA"]), AutomaticQA=aqa
        )
        self.envelope.getMySelf = Mock(
            return_value=Mock(getProcess=Mock(return_value=process))
        )
        self.assertEqual(qa.get_qa_application(self.envelope), mapped)


class CanRunQAOnFilesTest(QATestBase):
    def test_lists_remote_scripts_without_zip_output(self):
        qa_app = Mock(
            listQAScripts=Mock(
                return_value=[
                    ["42", "Remote check", None, "10", "HTML"],
                    ["43", "Zipped", None, "10", "ZIP"],
                ]
            )
        )
        with patch.object(qa, "get_qa_application", return_value=qa_app):
            result = qa.can_run_qa_on_files(self.envelope, [self.doc])
        self.assertEqual(
            result, {"data.xml": [["42", "Remote check", None, "10", "HTML"]]}
        )
        qa_app.listQAScripts.assert_called_once_with("schema.xsd")

    def test_legacy_local_scripts_are_not_offered(self):
        add_legacy_repository(self.root, scripts=["script1", "script2"])
        qa_app = Mock(listQAScripts=Mock(return_value=[]))
        self.doc.content_type = "application/msaccess"
        self.doc.xml_schema_location = ""
        with patch.object(qa, "get_qa_application", return_value=qa_app):
            result = qa.can_run_qa_on_files(self.envelope, [self.doc])
        self.assertEqual(result, {})

    def test_nothing_without_qa_application(self):
        with patch.object(qa, "get_qa_application", return_value=None):
            self.assertEqual(qa.can_run_qa_on_files(self.envelope, [self.doc]), {})

    def test_envelope_and_document_use_it(self):
        with patch.object(qa, "can_run_qa_on_files", return_value={"x": []}) as run:
            self.assertEqual(self.doc.getQAScripts(), {"x": []})
            self.assertEqual(self.envelope.canRunQAOnFiles(), {"x": []})
        self.assertEqual(run.call_count, 2)


class RunQAScriptTest(QATestBase):
    file_url = "http://example.com/envelope/data.xml"

    def test_remote_script_runs_in_qa_application(self):
        qa_app = Mock(runQAScript=Mock(return_value=["text/html", qa.QAResult("ok")]))
        with patch.object(qa, "get_qa_application", return_value=qa_app):
            file_id, (content_type, result) = qa.run_qa_script(
                self.envelope, self.file_url, "42"
            )
        qa_app.runQAScript.assert_called_once_with(self.file_url, "42")
        self.assertEqual(
            (file_id, content_type, result.data), ("data.xml", "text/html", "ok")
        )

    def test_local_script_ids_are_refused(self):
        add_legacy_repository(self.root, scripts=["script1"])
        qa_app = Mock()
        with patch.object(qa, "get_qa_application", return_value=qa_app):
            file_id, (content_type, result) = qa.run_qa_script(
                self.envelope, self.file_url, "loc_script1"
            )
        qa_app.runQAScript.assert_not_called()
        self.assertEqual(result.data, qa.LOCAL_SCRIPT_REFUSED)

    def test_qa_application_error_is_reported(self):
        qa_app = Mock(runQAScript=Mock(side_effect=ValueError("boom")))
        with patch.object(qa, "get_qa_application", return_value=qa_app):
            _, (_, result) = qa.run_qa_script(self.envelope, self.file_url, "42")
        self.assertEqual(result.data, "QA error: boom")

    def test_relative_file_path_resolves_from_the_envelope(self):
        qa_app = Mock(runQAScript=Mock(return_value=["text/html", qa.QAResult("ok")]))
        with patch.object(qa, "get_qa_application", return_value=qa_app):
            file_id, (_, result) = qa.run_qa_script(self.envelope, "data.xml", "42")
        self.assertEqual((file_id, result.data), ("data.xml", "ok"))

    def test_file_the_user_cannot_view_is_refused(self):
        from zExceptions import Unauthorized

        self.doc.manage_permission("View", ["Manager"], acquire=0)
        qa_app = Mock()
        with patch.object(qa, "get_qa_application", return_value=qa_app):
            with self.assertRaises(Unauthorized):
                qa.run_qa_script(self.envelope, self.file_url, "42")
        qa_app.runQAScript.assert_not_called()

    def test_unknown_file(self):
        _, (_, result) = qa.run_qa_script(
            self.envelope, "http://example.com/envelope/missing.xml", "42"
        )
        self.assertEqual(result.data, "QA error")

    def test_no_qa_application(self):
        with patch.object(qa, "get_qa_application", return_value=None):
            _, (_, result) = qa.run_qa_script(self.envelope, self.file_url, "42")
        self.assertEqual(result.data, "QA error: no QA application")


class RetiredClassesTest(BaseUnitTest):
    def test_qa_repository_accepts_nothing(self):
        self.assertEqual(QARepository.all_meta_types, ())
        self.assertFalse(hasattr(QARepository, "manage_addQAScript"))
        self.assertFalse(hasattr(QARepository, "_runQAScript"))

    def test_legacy_qa_script_loads_and_runs_nothing(self):
        script = legacy_qa_script("script1", script_url="check.sh %s")
        self.assertEqual(script.meta_type, constants.METATYPE_QASCRIPT)
        self.assertFalse(hasattr(script, "manage_settings"))
        self.assertFalse(hasattr(QAScript, "manage_addQAScript"))

    def test_qaresult_old_import_path(self):
        from Products.Reportek.QARepository import QAResult

        self.assertIs(QAResult, qa.QAResult)

    def test_no_command_execution_left(self):
        from Products.Reportek import Converter, QARepository as qarepo_module

        for module in (qa, qarepo_module, Converter):
            source = inspect.getsource(module)
            for needle in ("subprocess", "os.popen", "os.system", "eval("):
                self.assertNotIn(needle, source, (module.__name__, needle))

    def test_converters_accept_no_persistent_converters(self):
        from Products.Reportek import Converter
        from Products.Reportek.Converters import Converters

        self.assertEqual(Converters.all_meta_types, ())
        self.assertFalse(hasattr(Converters, "manage_addConverter"))
        self.assertFalse(hasattr(Converter, "manage_addConverter"))

    def test_base_converter_does_not_convert(self):
        from Products.Reportek.Converter import Converter

        conv = Converter("c", "", "cat %s", [], "text/plain", "", [], "")
        with self.assertRaises(NotImplementedError):
            conv.convert(Mock(), "c")


class AutomaticQAWithoutLocalScriptsTest(BaseUnitTest):
    def setUp(self):
        self.root = create_fake_root()
        self.envelope = create_envelope(self.root)
        xml = add_document(self.envelope, create_upload_file("<a/>", "data.xml"))
        xml.content_type = "text/xml"
        xml.xml_schema_location = "schema.xsd"
        add_document(self.envelope, create_upload_file("text", "notes.txt"))

    def check(self, app_class):
        app = app_class("remoteapp", "", "", "", "the_app").__of__(self.envelope)
        workitem = Mock(the_app={})
        app.runAutomaticLocalApps(workitem)
        # one empty entry per XML file, as before when there were no scripts
        self.assertEqual(workitem.the_app["localQA"], {"data.xml": {}})
        self.assertEqual(self.envelope.objectIds("Report Feedback"), [])
        self.assertFalse(hasattr(app, "_runLocalQAScripts"))
        self.assertFalse(hasattr(app, "_addFeedback"))

    def check_in_flight(self, app_class):
        """A workitem started before the removal, with local scripts pending."""
        app = app_class("remoteapp", "", "", "", "the_app").__of__(self.envelope)
        workitem = Mock(
            the_app={
                "localQA": {
                    "data.xml": {"script1": "in progress", "script2": "done"},
                    "old.xml": {"script3": "failed"},
                }
            }
        )
        app.runAutomaticLocalApps(workitem)
        self.assertEqual(
            workitem.the_app["localQA"],
            {"data.xml": {"script2": "done"}, "old.xml": {}},
        )
        self.assertTrue(workitem._p_changed)
        # nothing pending any more, so a failed remote analyze can finish
        self.assertTrue(app._local_scripts_done(workitem.the_app["localQA"]))

    def test_xmlrpc_application(self):
        from Products.Reportek.RemoteApplication import RemoteApplication

        self.check(RemoteApplication)
        self.check_in_flight(RemoteApplication)

    def test_rest_application(self):
        from Products.Reportek.RemoteRestQaApplication import RemoteRestQaApplication

        self.check(RemoteRestQaApplication)
        self.check_in_flight(RemoteRestQaApplication)


class RetireLocalQAUpdateTest(BaseUnitTest):
    def setUp(self):
        from Products.Reportek.Converter import Converter
        from Products.Reportek.Converters import Converters

        self.root = create_fake_root()
        self.engine = Engine()
        setattr(self.root, constants.ENGINE_ID, self.engine)
        self.root._setObject(constants.CONVERTERS_ID, Converters())
        self.converters = self.root[constants.CONVERTERS_ID]
        self.converters._setObject(
            "legacy", Converter("legacy", "", "convert.sh %s", [], "", "", [], "")
        )

    def retire(self, **kwargs):
        from Products.Reportek.updates import u20261125_retire_local_qa as upd

        return upd.retire_local_qa(self.root, **kwargs)

    def test_refuses_to_delete_unexported_scripts(self):
        add_legacy_repository(self.root, "Applications/QAApp", ["script1"])
        self.assertFalse(self.retire())
        self.assertIn(constants.QAREPOSITORY_ID, self.root.objectIds())
        self.assertIn("legacy", self.converters.objectIds())

    def test_removes_everything_once_confirmed(self):
        add_legacy_repository(self.root, "Applications/QAApp", ["script1", "script2"])
        self.assertTrue(self.retire(confirm_exported=True))
        self.assertNotIn(constants.QAREPOSITORY_ID, self.root.objectIds())
        self.assertEqual(self.converters.objectIds(), [])
        self.assertEqual(self.engine.QA_application, "Applications/QAApp")

    def test_empty_repository_needs_no_confirmation(self):
        add_legacy_repository(self.root, "Applications/QAApp")
        self.engine.QA_application = "Applications/QAApp"
        self.assertTrue(self.retire())
        self.assertNotIn(constants.QAREPOSITORY_ID, self.root.objectIds())

    def test_without_repository(self):
        self.assertTrue(self.retire())
        self.assertEqual(self.converters.objectIds(), [])
