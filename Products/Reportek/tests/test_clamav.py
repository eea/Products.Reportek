"""The virus scan: a virus is refused; a file that could not be scanned is
accepted or refused as CLAMAV_FAIL_MODE says, and logged either way."""

import io
import os
import unittest
from unittest.mock import Mock, patch

import clamd

from Products.Reportek import constants
from Products.Reportek.clamav import DEFAULT_MAX_FILE_SIZE, AVService
from Products.Reportek.exceptions import UploadValidationException

from .common import BaseTest
from .fileuploadmock import FileUploadMock
from .utils import create_temp_reposit

CLEAN = {"stream": ("OK", None)}
INFECTED = {"stream": ("FOUND", "Eicar-Test-Signature")}
SCAN_ERROR = {"stream": ("ERROR", "Can't allocate memory")}


def upload(data=b"content", name="file.txt"):
    f = io.BytesIO(data)
    f.filename = name
    return f


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.av = AVService(clamd_host="clamav", clam_max_file_size=1000)
        self.av.clamd = Mock()
        patcher = patch("Products.Reportek.clamav.time.sleep")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.logger = self.patch("Products.Reportek.clamav.logger")
        self.mode("open")

    def patch(self, target):
        patcher = patch(target)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def mode(self, mode):
        patcher = patch.dict(os.environ, {"CLAMAV_FAIL_MODE": mode})
        patcher.start()
        self.addCleanup(patcher.stop)

    def answer(self, result):
        if isinstance(result, Exception):
            self.av.clamd.instream.side_effect = result
        else:
            self.av.clamd.instream.return_value = result

    def logged(self):
        return " ".join(str(c) for c in self.logger.error.call_args_list)

    def test_a_clean_file_passes(self):
        self.answer(CLEAN)
        self.av.scan(upload())
        self.logger.error.assert_not_called()

    def test_a_virus_is_refused_in_both_modes(self):
        self.answer(INFECTED)
        for mode in ("open", "closed"):
            self.mode(mode)
            with self.assertRaisesRegex(UploadValidationException, "Eicar"):
                self.av.scan(upload())

    def test_unreachable_scanner(self):
        self.answer(clamd.ConnectionError("refused"))
        self.av.scan(upload(name="a.txt"))
        self.assertIn('"a.txt" was not scanned', self.logged())
        self.assertIn("accepted", self.logged())
        self.assertEqual(self.av.clamd.instream.call_count, 3)
        self.mode("closed")
        with self.assertRaisesRegex(UploadValidationException, "not available"):
            self.av.scan(upload())

    def test_a_scan_error_is_not_a_clean_file(self):
        self.answer(SCAN_ERROR)
        self.av.scan(upload())
        self.assertIn("allocate memory", self.logged())
        self.mode("closed")
        with self.assertRaises(UploadValidationException):
            self.av.scan(upload())

    def test_no_answer_is_not_a_clean_file(self):
        self.answer(None)
        self.mode("closed")
        with self.assertRaises(UploadValidationException):
            self.av.scan(upload())

    def test_too_big_for_the_scanner(self):
        self.answer(CLEAN)
        self.av.scan(upload(b"x" * 1001, "big.bin"))
        self.av.clamd.instream.assert_not_called()
        self.assertIn('"big.bin" was not scanned', self.logged())
        self.mode("closed")
        with self.assertRaisesRegex(UploadValidationException, "too big"):
            self.av.scan(upload(b"x" * 1001))

    def test_the_size_given_counts(self):
        # as for a file stored compressed, which cannot tell its size
        self.answer(CLEAN)
        self.av.scan(upload(b"x"), filesize=5000)
        self.av.clamd.instream.assert_not_called()
        self.av.scan(upload(b"x" * 1001), filesize=10)
        self.av.clamd.instream.assert_called_once()

    def test_without_a_limit_everything_is_scanned(self):
        self.av.clam_max_file_size = None
        self.answer(INFECTED)
        with self.assertRaises(UploadValidationException):
            self.av.scan(upload(b"x" * 10**6))

    def test_without_a_scanner_nothing_is_scanned(self):
        av = AVService(clam_max_file_size=1000)
        self.mode("closed")
        av.scan(upload())
        self.logger.error.assert_not_called()

    def test_an_unknown_mode_is_open(self):
        self.mode("whatever")
        self.answer(clamd.ConnectionError("refused"))
        self.av.scan(upload())

    def test_the_file_is_rewound(self):
        self.answer(CLEAN)
        f = upload(b"content")
        self.av.scan(f)
        self.assertEqual(f.read(), b"content")


class RestScanTest(ScanTest):
    """The same answers from the REST scanner."""

    def setUp(self):
        super().setUp()
        self.av = AVService(clamav_rest_host="clamav-rest", clam_max_file_size=1000)
        self.post = self.patch("Products.Reportek.clamav.requests.post")

    def answer(self, result):
        if isinstance(result, Exception):
            import requests

            self.post.side_effect = requests.exceptions.ConnectionError("refused")
        elif result is None:
            self.post.return_value = Mock(status_code=500, text="")
        elif result["stream"][0] == "OK":
            self.post.return_value = Mock(status_code=200, text="Everything ok : true")
        elif result["stream"][0] == "FOUND":
            self.post.return_value = Mock(status_code=200, text="Eicar found")
        else:
            self.post.return_value = Mock(status_code=500, text="Can't allocate memory")

    def test_unreachable_scanner(self):
        self.answer(clamd.ConnectionError("refused"))
        self.av.scan(upload(name="a.txt"))
        self.assertIn('"a.txt" was not scanned', self.logged())
        self.assertEqual(self.post.call_count, 3)

    def test_a_scan_error_is_not_a_clean_file(self):
        self.answer(SCAN_ERROR)
        self.av.scan(upload())
        self.assertIn("HTTP 500", self.logged())
        self.mode("closed")
        with self.assertRaises(UploadValidationException):
            self.av.scan(upload())

    def test_a_virus_is_refused_in_both_modes(self):
        self.answer(INFECTED)
        for mode in ("open", "closed"):
            self.mode(mode)
            with self.assertRaisesRegex(UploadValidationException, "REST"):
                self.av.scan(upload())

    def test_too_big_for_the_scanner(self):
        self.answer(CLEAN)
        self.av.scan(upload(b"x" * 1001, "big.bin"))
        self.post.assert_not_called()

    def test_the_size_given_counts(self):
        self.answer(CLEAN)
        self.av.scan(upload(b"x"), filesize=5000)
        self.post.assert_not_called()


class EngineServiceTest(BaseTest):
    def test_the_limit_is_clamavs(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        self.assertEqual(ReportekEngine.clam_max_file_size, DEFAULT_MAX_FILE_SIZE)
        self.assertEqual(DEFAULT_MAX_FILE_SIZE, 2147483648)

    def test_a_service_made_on_demand_has_the_limit(self):
        from Products.Reportek.ReportekEngine import ReportekEngine

        engine = ReportekEngine()
        engine.clamd_host = "clamav"
        engine.clam_max_file_size = 12345
        self.assertEqual(engine.AVService.clam_max_file_size, 12345)


class UploadsAreScannedTest(BaseTest):
    """Every way a file is stored goes through the scan."""

    def afterSetUp(self):
        super().afterSetUp()
        self._cleanup_temp_reposit = create_temp_reposit()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.envelope = self.createStandardEnvelope()
        # feedback text goes through the converters' safe_html
        from Products.Reportek import Converters

        root = self.envelope.getPhysicalRoot()
        setattr(root, constants.CONVERTERS_ID, Converters.Converters())
        getattr(root, constants.CONVERTERS_ID).__getitem__ = Mock(
            return_value=Mock(convert=Mock(text="feedbacktext"))
        )
        engine = getattr(self.app, constants.ENGINE_ID)
        self.scan = Mock()
        engine._AVService = Mock(scan=self.scan)

    def beforeTearDown(self):
        self._cleanup_temp_reposit()

    def add_feedback(self, files=""):
        self.envelope.manage_addProduct["Reportek"].manage_addFeedback(
            "feedbackid", "Title", "Feedback text", files, "WorkflowEngine/begin_end", 1
        )
        return self.envelope.feedbackid

    def test_a_document_is_scanned_with_its_unpacked_size(self):
        content = b"<r>%s</r>" % (b"<v>1</v>" * 10000)
        self.envelope.manage_addProduct["Reportek"].manage_addDocument(
            "data.xml", "", upload(content, "data.xml")
        )
        self.assertEqual(self.scan.call_args[1]["filesize"], len(content))

    def test_feedback_attachments_are_scanned(self):
        feedback = self.add_feedback([FileUploadMock("a.txt", "a")])
        self.assertEqual(self.scan.call_args[1]["filename"], "a.txt")
        feedback.manage_uploadAttFeedback("a.txt", FileUploadMock("a.txt", "b"))
        self.assertEqual(self.scan.call_count, 2)

    def test_an_infected_attachment_is_not_stored(self):
        self.scan.side_effect = UploadValidationException("Virus found")
        with self.assertRaises(UploadValidationException):
            self.add_feedback([FileUploadMock("a.txt", "a")])
        self.scan.side_effect = None
        feedback = self.add_feedback()
        feedback.manage_uploadFeedback(FileUploadMock("a.txt", "clean"))
        self.scan.side_effect = UploadValidationException("Virus found")
        with self.assertRaises(UploadValidationException):
            feedback.manage_uploadAttFeedback("a.txt", FileUploadMock("a.txt", "bad"))
        with feedback["a.txt"].data_file.open() as f:
            self.assertEqual(f.read(), b"clean")


class RefusedUploadPageTest(unittest.TestCase):
    """A refused upload gets the site error page with its message, 400."""

    def view(self, accept=None):
        from Products.Reportek.errors import ErrorView

        request = Mock(environ={"HTTP_ACCEPT": accept} if accept else {})
        view = ErrorView()
        view.context = UploadValidationException(
            "The virus scanner is not available; please try again later."
        )
        view.request = request
        return view, request

    def test_zope_answers_it_with_400(self):
        # as Zope, and plone.transformchain after it, set the status of an
        # error: from the name of its class
        from ZPublisher.HTTPResponse import HTTPResponse

        response = HTTPResponse()
        response.setStatus(UploadValidationException)
        self.assertEqual(response.getStatus(), 400)

    def test_json_clients(self):
        import json

        view, request = self.view("application/json")
        body = json.loads(view())
        request.response.setStatus.assert_called_with(400)
        self.assertEqual(body["errors"][0]["title"], "UploadValidationException")
        self.assertIn("try again later", body["errors"][0]["description"])

    def test_the_site_error_page(self):
        view, request = self.view()
        parent = Mock()
        with patch("Products.Reportek.errors.aq_parent", return_value=parent):
            view()
        kwargs = parent.standard_error_message.call_args[1]
        self.assertIn("try again later", kwargs["error_value"])
