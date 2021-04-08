# -*- coding: utf-8 -*-
import json
import unittest

from mock import Mock, patch
from Products.Reportek import Converters, constants
from Products.Reportek.RemoteRestQaApplication import RemoteRestQaApplication
from utils import create_envelope, create_fake_root


class RemoteApplicationFeedbackTest(unittest.TestCase):

    def setUp(self):
        self.root = create_fake_root()
        self.root.getWorkitemsActiveForMe = Mock(return_value=[])
        self.envelope = create_envelope(self.root)
        self.envelope.getEngine = Mock()
        self.envelope.REQUEST = Mock()

        self.remoteapp = RemoteRestQaApplication('remoteapp', '', '', '',
                                                 'the_app').__of__(self.envelope)
        self.remoteapp.the_workitem = Mock(the_app={
            'getResult': {
                'the_jobid': {
                    'fileURL': 'http://example.com/results_file',
                },
            }
        })
        setattr(
            self.envelope.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(text='feedbacktext'))
        getattr(self.envelope.getPhysicalRoot(),
                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)

    @patch('Products.Reportek.RemoteApplication.requests.get')
    def receive_feedback(self, text, mock_requests):
        mock_requests.return_value = Mock(
            content=json.dumps({
                'executionStatus': {
                    'statusId': '0',
                    'statusName': '',
                },
                'scriptTitle': "mock script",
                'feedbackContent': text,
                'feedbackContentType': 'application/x-mock',
                'feedbackMessage': '',
                'feedbackStatus': 'success',
            })
        )

        self.remoteapp._RemoteRestQaApplication__getResult4XQueryServiceJob(
            'the_workitem', 'the_jobid')
        # mock_requests.codes.ok = 200
        # mock_requests.post.return_value = Mock(
        #     status_code=200,
        #     reason='OK',
        #     json=Mock(return_value={
        #     }))
        # mock_requests.codes.ok = 200

    def test_24_char_feedback_is_saved_inline(self):
        text = u"smałl aut°mătic feedback"
        self.receive_feedback(text)
        [feedback] = self.envelope.objectValues()
        self.assertEqual(feedback.objectValues(), [])
        self.assertEqual(feedback.content_type, 'application/x-mock')
        self.assertEqual(feedback.feedbacktext, text)

    def test_100k_char_feedback_creates_attachment_and_explanation(self):
        text = "large automatic feedback: " + (u"[10 chąṛŝ]" * 10240)
        self.receive_feedback(text)

        [feedback] = self.envelope.objectValues()
        [attach] = feedback.objectValues()
        with attach.data_file.open() as f:
            self.assertEqual(f.read().decode('utf-8'), text)

        self.assertEqual(attach.data_file.content_type, 'application/x-mock')

        self.assertIn('see attachment', feedback.feedbacktext)
        self.assertEqual(feedback.content_type, 'text/html')

    def test_feedback_for_file_with_space_chars(self):
        self.remoteapp.the_workitem = Mock(the_app={
            'getResult': {
                'the_jobid': {
                    'fileURL': 'http://example.com/name%20with%20spaces.txt',
                },
            }
        })

        from Products.Reportek.Document import Document
        doc = Document('name with spaces.txt', '', content_type="text/plain")
        doc = doc.__of__(self.envelope)
        self.envelope._setObject('name with spaces.txt', doc)

        assert self.envelope['name with spaces.txt']
        self.receive_feedback('text')
        [feedback] = [item for item in self.envelope.objectValues()
                      if item.meta_type == 'Report Feedback']
        self.assertEqual('name with spaces.txt', feedback.document_id)


class GetAllFeedbackTest(RemoteApplicationFeedbackTest):

    def test_feedback_objects_details_small_file(self):
        self.receive_feedback('AQ feedback')
        self.maxDiff = None
        [feedback] = self.envelope.getFeedbacks()
        self.assertEqual(
            {'feedbacks':
             [
                 {
                     'title': feedback.title,
                     'releasedate': feedback.releasedate.HTML4(),
                     'isautomatic': feedback.automatic,
                     'content_type': feedback.content_type,
                     'referred_file': '%s/%s' % (self.envelope.absolute_url(), feedback.document_id),
                     'qa_output_url': "%s" % feedback.absolute_url()
                 },
             ]
             },
            self.envelope.feedback_objects_details()
        )

    def test_feedback_objects_details_big_file(self):
        self.maxDiff = None
        text = "large automatic feedback: " + (u"[10 chąṛŝ]" * 10240)
        self.receive_feedback(text)
        [feedback] = self.envelope.objectValues()
        self.assertEqual(
            {'feedbacks':
             [
                 {
                     'title': feedback.title,
                     'releasedate': feedback.releasedate.HTML4(),
                     'isautomatic': feedback.automatic,
                     'content_type': feedback.content_type,
                     'referred_file': '%s/%s' % (self.envelope.absolute_url(), feedback.document_id),
                     'qa_output_url': "%s/qa-output" % feedback.absolute_url()
                 },
             ]
             },
            self.envelope.feedback_objects_details()
        )

    def test_feedback_objects_details_without_reffered_file(self):
        self.maxDiff = None
        text = "short text"
        self.receive_feedback(text)
        [feedback] = self.envelope.objectValues()
        feedback.document_id = None
        self.assertEqual(
            {'feedbacks':
             [
                 {
                     'title': feedback.title,
                     'releasedate': feedback.releasedate.HTML4(),
                     'isautomatic': feedback.automatic,
                     'content_type': feedback.content_type,
                     'referred_file': '',
                     'qa_output_url': "%s" % feedback.absolute_url()
                 },
             ]
             },
            self.envelope.feedback_objects_details()
        )
