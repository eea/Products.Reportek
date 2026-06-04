# -*- coding: utf-8 -*-
from io import BytesIO

from .common import BaseUnitTest
from Products.Reportek.BaseRemoteApplication import BaseRemoteApplication
from Products.Reportek.constants import FEEDBACKTEXT_LIMIT


class FakeDataFile(object):
    def __init__(self, data=b""):
        self.data = data
        self.content_type = None

    def open(self, mode="rb"):
        return BytesIO(self.data)


class FakeAttachment(object):
    def __init__(self, data=b""):
        self.data_file = FakeDataFile(data)


class FakeFeedback(object):
    def __init__(self):
        self.feedbacktext = ""
        self.content_type = ""
        self.attachments = {}

    def unrestrictedTraverse(self, name, default=None):
        return self.attachments.get(name, default)

    def manage_uploadFeedback(self, fileobj, filename=None, REQUEST=None):
        self.attachments[filename] = FakeAttachment(fileobj.read())

    def manage_uploadAttFeedback(self, file_id="", file="", REQUEST=None):
        self.attachments[file_id] = FakeAttachment(file.read())


class BaseRemoteApplicationFeedbackContentTest(BaseUnitTest):

    def setUp(self):
        self.app = BaseRemoteApplication()

    def test_ensure_text_decodes_utf8_bytes(self):
        text = u"smałl aut°mătic feedback"

        self.assertEqual(
            self.app.ensure_text(text.encode("utf-8")),
            text,
        )

    def test_ensure_bytes_encodes_text(self):
        text = u"smałl aut°mătic feedback"

        self.assertEqual(
            self.app.ensure_bytes(text),
            text.encode("utf-8"),
        )

    def test_small_bytes_feedback_is_stored_inline_as_text(self):
        feedback = FakeFeedback()
        text = u'<div class="feedbacktext">smałl</div>'

        self.app.store_feedback_content(
            feedback,
            text.encode("utf-8"),
            "text/html",
        )

        self.assertIsInstance(feedback.feedbacktext, str)
        self.assertEqual(feedback.feedbacktext, text)
        self.assertEqual(feedback.content_type, "text/html")
        self.assertEqual(feedback.attachments, {})

    def test_small_custom_content_type_stays_inline(self):
        feedback = FakeFeedback()
        text = u"custom textual output"

        self.app.store_feedback_content(
            feedback,
            text.encode("utf-8"),
            "application/x-mock",
        )

        self.assertIsInstance(feedback.feedbacktext, str)
        self.assertEqual(feedback.feedbacktext, text)
        self.assertEqual(feedback.content_type, "application/x-mock")
        self.assertEqual(feedback.attachments, {})

    def test_large_bytes_feedback_creates_bytes_attachment(self):
        feedback = FakeFeedback()
        text = u"large automatic feedback: " + (u"[10 chąṛŝ]" * 10240)
        raw = text.encode("utf-8")
        self.assertGreater(len(raw), FEEDBACKTEXT_LIMIT)

        self.app.store_feedback_content(
            feedback,
            raw,
            "text/html",
        )

        self.assertIsInstance(feedback.feedbacktext, str)
        self.assertIn("see attachment", feedback.feedbacktext)
        self.assertEqual(feedback.content_type, "text/html")
        self.assertEqual(feedback.attachments["qa-output"].data_file.data, raw)
        self.assertEqual(
            feedback.attachments["qa-output"].data_file.content_type,
            "text/html",
        )
