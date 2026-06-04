# -*- coding: utf-8 -*-
from unittest.mock import Mock, patch

from Products.Reportek import Converters, constants
from Products.Reportek.RemoteRabbitMQQAApplication import (
    RemoteRabbitMQQAApplication,
)
from .common import BaseUnitTest
from .utils import create_envelope, create_fake_root


class RemoteRabbitMQApplicationFeedbackTest(BaseUnitTest):
    def setUp(self):
        self.root = create_fake_root()
        self.root.getWorkitemsActiveForMe = Mock(return_value=[])
        self.envelope = create_envelope(self.root)
        self.envelope.getEngine = Mock()
        self.envelope.REQUEST = Mock()

        self.remoteapp = RemoteRabbitMQQAApplication(
            "remoteapp", "", "", "", "", "", "token", "the_app"
        ).__of__(self.envelope)
        self.remoteapp.the_workitem = Mock(
            activity_id="mock-activity",
            addEvent=Mock(),
        )
        setattr(
            self.envelope.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters(),
        )
        safe_html = Mock(convert=Mock(text="feedbacktext"))
        getattr(
            self.envelope.getPhysicalRoot(), constants.CONVERTERS_ID
        ).__getitem__ = Mock(return_value=safe_html)

    def test_direct_bytes_feedback_content_is_saved_as_text(self):
        text = '<div class="feedbacktext">smałl aut°mătic feedback</div>'
        payload = {
            "jobId": "the-job-id",
            "documentURL": "http://example.com/results_file",
            "scriptTitle": "mock script",
            "jobResult": {
                "feedbackContent": text.encode("utf-8"),
                "feedbackContentType": "text/html",
                "feedbackMessage": "message",
                "feedbackStatus": "SUCCESS",
            },
        }

        self.remoteapp.handle_result(self.remoteapp.the_workitem, payload)

        [feedback] = self.envelope.objectValues()
        self.assertIsInstance(feedback.feedbacktext, str)
        self.assertEqual(feedback.feedbacktext, text)
        self.assertEqual(feedback.content_type, "text/html")

    @patch("Products.Reportek.BaseRemoteApplication.requests.get")
    def test_remote_file_html_bytes_are_saved_as_text(self, mock_get):
        text = '<div class="feedbacktext">smałl aut°mătic feedback</div>'
        response = Mock(
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            content=text.encode("utf-8"),
            close=Mock(),
        )
        mock_get.return_value = response

        self.remoteapp.handle_remote_file(
            "http://example.com/qa-output",
            "results_file",
            "the_workitem",
            {
                "SCRIPT_TITLE": "mock script",
                "feedbackContentType": "text/html",
                "feedbackStatus": "SUCCESS",
                "feedbackMessage": "message",
            },
            "the-job-id",
        )

        [feedback] = self.envelope.objectValues()
        self.assertIsInstance(feedback.feedbacktext, str)
        self.assertEqual(feedback.feedbacktext, text)
        self.assertEqual(feedback.content_type, "text/html")
