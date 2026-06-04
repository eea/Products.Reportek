# -*- coding: utf-8 -*-
from unittest.mock import Mock

from Products.Reportek import Converters, constants
from Products.Reportek.RemoteApplication import RemoteApplication
from Products.Reportek.RemoteFMEConversionApplication import (
    RemoteFMEConversionApplication,
)
from .common import BaseUnitTest
from .utils import create_envelope, create_fake_root


class RemoteApplicationFeedbackContentTest(BaseUnitTest):
    def setUp(self):
        self.root = create_fake_root()
        self.root.getWorkitemsActiveForMe = Mock(return_value=[])
        self.envelope = create_envelope(self.root)
        self.envelope.getEngine = Mock()
        self.envelope.REQUEST = Mock()
        setattr(
            self.envelope.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters(),
        )
        safe_html = Mock(convert=Mock(text="feedbacktext"))
        getattr(
            self.envelope.getPhysicalRoot(), constants.CONVERTERS_ID
        ).__getitem__ = Mock(return_value=safe_html)

    def test_legacy_remote_application_bytes_feedback_is_saved_as_text(self):
        text = "smałl aut°mătic feedback"
        remoteapp = RemoteApplication("remoteapp", "", "", "", "the_app").__of__(
            self.envelope
        )
        remoteapp.QARepository = {
            "mock-script": Mock(title="mock script"),
        }
        workitem = Mock(activity_id="mock-activity")

        remoteapp._addFeedback(
            "results_file",
            ("application/x-mock", Mock(data=text.encode("utf-8"))),
            workitem,
            "mock-script",
        )

        [feedback] = self.envelope.objectValues()
        self.assertIsInstance(feedback.feedbacktext, str)
        self.assertEqual(feedback.feedbacktext, text)
        self.assertEqual(feedback.content_type, "application/x-mock")


class RemoteFMEConversionApplicationFeedbackContentTest(BaseUnitTest):
    def test_fme_bytes_are_decoded_to_text(self):
        text = "smałl FME feedback"
        app = RemoteFMEConversionApplication(
            "fme",
            "",
            "",
            "",
            None,
            "",
            "",
            "",
            "minute",
            "",
            "",
            "",
            None,
            None,
            False,
            "",
            None,
            True,
            300,
            "fme_app",
        )

        self.assertEqual(app.ensure_text(text.encode("utf-8")), text)
