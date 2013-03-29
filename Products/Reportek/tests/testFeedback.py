# -*- coding: utf-8 -*-
import os, sys
import unittest
import json
from Products.Reportek import constants
from mock import Mock, patch
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from configurereportek import ConfigureReportek
from fileuploadmock import FileUploadMock
from utils import create_temp_reposit, create_fake_root, create_envelope
from Products.Reportek import Converters
from OFS.SimpleItem import Item


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
        setattr(
            self.envelope.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(text='feedbacktext'))
        getattr(self.envelope.getPhysicalRoot(),
                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)

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
        setattr(
            self.envelope.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(text='feedbacktext'))
        getattr(self.envelope.getPhysicalRoot(),
                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)

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


class BlockerFeedbackTest(unittest.TestCase):

    def setUp(self):
        from Products.Reportek.RemoteApplication import RemoteApplication
        self.root = create_fake_root()
        self.root.getWorkitemsActiveForMe = Mock(return_value=[])
        self.envelope = create_envelope(self.root)
        self.envelope.getEngine = Mock()
        self.envelope.REQUEST = Mock()
        self.envelope.addWorkitem('AutomaticQA', False)

        self.remoteapp = RemoteApplication('remoteapp', '', '',
            'the_service', 'the_app').__of__(self.envelope)
        workitem = getattr(self.envelope, '0')
        workitem.the_app = the_app={
            'getResult': {
                'the_jobid': {
                    'fileURL': 'http://example.com/results_file',
                },
            }
        }
        setattr(
            self.envelope.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(text='feedbacktext'))
        getattr(self.envelope.getPhysicalRoot(),
                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)

    @patch('Products.Reportek.RemoteApplication.xmlrpclib')
    def receive_feedback(self, text, result, mock_xmlrpclib):
        mock_server = mock_xmlrpclib.ServerProxy.return_value
        getResult = mock_server.the_service.getResult
        getResult.return_value = result
        self.remoteapp._RemoteApplication__getResult4XQueryServiceJob(
            '0', 'the_jobid')

    def test_workitem_blocker_attr_is_set_to_True(self):
        text = 'blocker feedback'
        [workitem] = self.envelope.objectValues('Workitem')
        #assert the workitem has the 'blocker' attribute
        #and is False by default
        self.assertEqual(False, getattr(workitem, 'blocker', None))
        result = {
            'CODE': '0',
            'VALUE': text,
            'SCRIPT_TITLE': "mock script",
            'METATYPE': 'application/x-mock',
            'FEEDBACK_STATUS': 'BLOCKER',
            'FEEDBACK_MESSAGE': 'Blocker error'
        }
        self.receive_feedback(text, result)
        #assert 'blocker' is set to True due to errors in feedback
        self.assertEqual(True, workitem.blocker)

    def test_workitem_blocker_attr_remains_False(self):
        text = 'blocker feedback'
        [workitem] = self.envelope.objectValues('Workitem')
        #assert the workitem has the 'blocker' attribute
        #and is False by default
        self.assertEqual(False, getattr(workitem, 'blocker', None))
        result = {
            'CODE': '0',
            'VALUE': text,
            'SCRIPT_TITLE': "mock script",
            'METATYPE': 'application/x-mock',
            'FEEDBACK_STATUS': 'INFO',
            'FEEDBACK_MESSAGE': 'Non blocker error'
        }
        self.receive_feedback(text, result)
        #assert 'blocker' is set to True due to errors in feedback
        self.assertEqual(False, workitem.blocker)

    def test_envelope_blocked_by_feedback(self):
        text = 'blocker feedback'
        self.assertEqual(False, getattr(self.envelope, 'is_blocked', None))
        result = {
            'CODE': '0',
            'VALUE': text,
            'SCRIPT_TITLE': "mock script",
            'METATYPE': 'application/x-mock',
            'FEEDBACK_STATUS': 'BLOCKER',
            'FEEDBACK_MESSAGE': 'Non blocker error'
        }
        self.receive_feedback(text, result)
        self.assertEqual(True, self.envelope.is_blocked)

    def test_envelope_is_blocked_by_feedback(self):
        text = 'blocker feedback'
        [workitem] = self.envelope.objectValues('Workitem')
        #assert the workitem has the 'blocker' attribute
        #and is False by default
        self.assertEqual(False, getattr(workitem, 'blocker', None))
        result = {
            'CODE': '0',
            'VALUE': text,
            'SCRIPT_TITLE': "mock script",
            'METATYPE': 'application/x-mock',
            'FEEDBACK_STATUS': 'INFO',
            'FEEDBACK_MESSAGE': 'Non blocker error'
        }
        self.receive_feedback(text, result)
        self.assertEqual(False, self.envelope.is_blocked)


class GetAllFeedbackTest(RemoteApplicationFeedbackTest):

    def test_feedback_objects_details_small_file(self):
        result = {
            'CODE': '0',
            'VALUE': 'AQ feedback',
            'SCRIPT_TITLE': "mock script",
            'METATYPE': 'application/x-mock',
            'FEEDBACK_STATUS': 'BLOCKER',
            'FEEDBACK_MESSAGE': 'Blocker error'
        }
        self.receive_feedback('AQ feedback')
        from DateTime import DateTime
        self.maxDiff = None
        [feedback] = self.envelope.getFeedbacks()
        self.assertEqual(
            {'feedbacks':
              [
                {
                  'title'         : feedback.title,
                  'releasedate'   : feedback.releasedate.HTML4(),
                  'isautomatic'   : feedback.automatic,
                  'content_type'  : feedback.content_type,
                  'referred_file' : '%s/%s' %(self.envelope.absolute_url(), feedback.document_id),
                  'qa_output_url' : "%s" %feedback.absolute_url()
                },
              ]
            },
            self.envelope.feedback_objects_details()
        )

    def test_feedback_objects_details_big_file(self):
        self.maxDiff = None
        from DateTime import DateTime
        text = "large automatic feedback: " + (u"[10 chąṛŝ]" * 10240)
        self.receive_feedback(text)
        [feedback] = self.envelope.objectValues()
        attach = feedback.get('qa-output')
        self.assertEqual(
            {'feedbacks':
              [
                {
                  'title'         : feedback.title,
                  'releasedate'   : feedback.releasedate.HTML4(),
                  'isautomatic'   : feedback.automatic,
                  'content_type'  : feedback.content_type,
                  'referred_file' : '%s/%s' %(self.envelope.absolute_url(), feedback.document_id),
                  'qa_output_url' : "%s/qa-output" %feedback.absolute_url()
                },
              ]
            },
            self.envelope.feedback_objects_details()
        )

    def test_feedback_objects_details_without_reffered_file(self):
        self.maxDiff = None
        from DateTime import DateTime
        text = "short text"
        self.receive_feedback(text)
        [feedback] = self.envelope.objectValues()
        feedback.document_id = None
        self.assertEqual(
            {'feedbacks':
              [
                {
                  'title'         : feedback.title,
                  'releasedate'   : feedback.releasedate.HTML4(),
                  'isautomatic'   : feedback.automatic,
                  'content_type'  : feedback.content_type,
                  'referred_file' : '',
                  'qa_output_url' : "%s" %feedback.absolute_url()
                },
              ]
            },
            self.envelope.feedback_objects_details()
        )
