# -*- coding: utf-8 -*-
import os, sys
import unittest
from mock import Mock, patch
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from configurereportek import ConfigureReportek
from fileuploadmock import FileUploadMock
from utils import create_temp_reposit, create_fake_root, create_envelope


def setUpModule(self):
    self._cleanup_temp_reposit = create_temp_reposit()


def tearDownModule(self):
    self._cleanup_temp_reposit()


class MockResponse:
    def __init__(self):
        self.headers = {}
    def setHeader(self, name, value):
        self.headers[name] = value
    def write(self, data):
        pass


class FeedbackTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    def afterSetUp(self):
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),
                        'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        self.envelope = self.createStandardEnvelope()

    def create_feedback(self):
        """ Create an automatic feedback in the envelope
        """
        adder = self.envelope.manage_addProduct['Reportek']
        adder.manage_addFeedback('feedbackid', 'Title',
            'Feedback text', '','WorkflowEngine/begin_end', 1)
        self.feedback = self.envelope.feedbackid

    def testCreation(self):
        self.create_feedback()
        self.assertTrue(hasattr(self.envelope, 'feedbackid'),
                        'Feedback did not get created')

    def testZipSimple(self):
        self.create_feedback()
        self.app.REQUEST.PARENTS = [self.envelope, self.app.collection]
        MOCKRESPONSE = MockResponse()
        self.envelope.canViewContent = Mock(return_value=True)
        self.envelope.envelope_zip(self.app.REQUEST, MOCKRESPONSE)
        self.assertTrue(MOCKRESPONSE.headers['Content-Type'].startswith(
            'application/x-zip'))

    def testNationalChars(self):
        self.envelope.manage_addProduct['Reportek'].manage_addFeedback('feedbackid',
          'Æblegrød title',
          'ÐBlåbærgrød content text', '','Script URL', 0)

    def testZipNational(self):
        self.testNationalChars()
        self.app.REQUEST.PARENTS = [self.envelope, self.app.collection]
        MOCKRESPONSE = MockResponse()
        self.envelope.canViewContent = Mock(return_value=True)
        self.envelope.envelope_zip(self.app.REQUEST, MOCKRESPONSE)
        self.assertTrue(MOCKRESPONSE.headers['Content-Type'].startswith(
            'application/x-zip'))

    def test_uploadFeedback(self):
        """ Test the manage_uploadFeedback method
        """
        self.create_feedback()
        # Create a file inside it
        file = FileUploadMock('C:\\TEMP\\testfile.txt','content here')
        self.feedback.manage_uploadFeedback(file)
        self.assertTrue(hasattr(self.feedback, 'testfile.txt'),
                        'File did not get created')
        with self.feedback['testfile.txt'].data_file.open() as f:
            self.assertEqual(f.read(), 'content here')

    def test_add_feedback_with_attached_file(self):
        upload_file = FileUploadMock('testfile.txt','content here')
        adder = self.envelope.manage_addProduct['Reportek']
        adder.manage_addFeedback('feedbackid', 'Title',
            'Feedback text', upload_file,'WorkflowEngine/begin_end', 1)
        feedback = self.envelope.feedbackid
        self.assertTrue(hasattr(feedback, 'testfile.txt'),
                        'File did not get created')
        with feedback['testfile.txt'].data_file.open() as f:
            self.assertEqual(f.read(), 'content here')

    def test_AttFeedback(self):
        """ Test the manage_uploadAttFeedback method
            Replace the content of an existing file with manage_uploadAttFeedback
            Test the delete of an attachement
        """
        self.create_feedback()
        # Create a file inside it
        file = FileUploadMock('C:\\TEMP\\testfile.txt','content here')
        self.feedback.manage_uploadFeedback(file)
        self.assertTrue(hasattr(self.feedback, 'testfile.txt'),
                        'File did not get created')

        # Replace the file content
        file2 = FileUploadMock('C:\\TEMP\\anotherfile.txt','something else here')
        self.feedback.manage_uploadAttFeedback('testfile.txt', file)
        self.assertTrue(hasattr(self.feedback, 'testfile.txt'))
        self.assertFalse(hasattr(self.feedback, 'anotherfile.txt'))

        # Delete the attachment
        self.app.REQUEST.set('go', "Delete")
        self.feedback.manage_deleteAttFeedback('testfile.txt', self.app.REQUEST)
        self.assertFalse(hasattr(self.feedback, 'testfile.txt'))

    def test_restrictFeedback(self):
        self.create_feedback()
        self.feedback.manage_restrictFeedback()
        assert self.feedback.acquiredRolesAreUsedBy('View') == ''

        self.feedback.manage_unrestrictFeedback()
        assert self.feedback.acquiredRolesAreUsedBy('View') == 'CHECKED'


class RemoteApplicationFeedbackTest(unittest.TestCase):

    def setUp(self):
        from Products.Reportek.RemoteApplication import RemoteApplication
        self.root = create_fake_root()
        self.root.getWorkitemsActiveForMe = Mock(return_value=[])
        self.envelope = create_envelope(self.root)
        self.envelope.getEngine = Mock()
        self.envelope.REQUEST = Mock()

        self.remoteapp = RemoteApplication('remoteapp', '', '',
            'the_service', 'the_app').__of__(self.envelope)
        self.remoteapp.the_workitem = Mock(the_app={
            'getResult': {
                'the_jobid': {
                    'fileURL': 'http://example.com/results_file',
                },
            }
        })

    @patch('Products.Reportek.RemoteApplication.xmlrpclib')
    def receive_feedback(self, text, mock_xmlrpclib):
        mock_server = mock_xmlrpclib.ServerProxy.return_value
        getResult = mock_server.the_service.getResult
        getResult.return_value = {
            'CODE': '0',
            'VALUE': text,
            'SCRIPT_TITLE': "mock script",
            'METATYPE': 'application/x-mock',
        }
        self.remoteapp._RemoteApplication__getResult4XQueryServiceJob(
            'the_workitem', 'the_jobid')

    def test_24bytes_feedback_is_saved_inline(self):
        text = 'small automatic feedback'
        self.receive_feedback(text)

        [feedback] = self.envelope.objectValues()
        self.assertEqual(feedback.objectValues(), [])
        self.assertEqual(feedback.content_type, 'application/x-mock')
        self.assertEqual(feedback.feedbacktext, text)

    def test_100kb_feedback_creates_attachment_and_explanation(self):
        text = 'large automatic feedback: ' + ('[10 bytes]' * 10240)
        self.receive_feedback(text)

        [feedback] = self.envelope.objectValues()
        [attach] = feedback.objectValues()
        with attach.data_file.open() as f:
            self.assertEqual(f.read(), text)

        self.assertEqual(attach.data_file.content_type, 'application/x-mock')

        self.assertIn('see attachment', feedback.feedbacktext)
        self.assertEqual(feedback.content_type, 'text/html')
