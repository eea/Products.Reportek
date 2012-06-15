# -*- coding: utf-8 -*-
import os, sys
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from configurereportek import ConfigureReportek
from fileuploadmock import FileUploadMock
from utils import create_temp_reposit


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
        self.assertTrue(hasattr(self.app, 'collection'),'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        self.envelope = self.createStandardEnvelope()

    def create_feedback(self):
        """ Create an automatic feedback in the envelope
        """
        self.envelope.manage_addProduct['Reportek'].manage_addFeedback('feedbackid',
          'Title',
          'Feedback text', '','WorkflowEngine/begin_end', 1)
        self.feedback = self.envelope.feedbackid

    def testCreation(self):
        self.create_feedback()
        self.assertTrue(hasattr(self.envelope, 'feedbackid'),'Feedback did not get created')

    def testZipSimple(self):
        self.create_feedback()
        self.app.REQUEST.PARENTS = [self.envelope, self.app.collection]
        MOCKRESPONSE = MockResponse()
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
        self.assertTrue(hasattr(self.feedback, 'testfile.txt'),'File did not get created')

    def test_AttFeedback(self):
        """ Test the manage_uploadAttFeedback method
            Replace the content of an existing file with manage_uploadAttFeedback
            Test the delete of an attachement
        """
        self.create_feedback()
        # Create a file inside it
        file = FileUploadMock('C:\\TEMP\\testfile.txt','content here')
        self.feedback.manage_uploadFeedback(file)
        self.assertTrue(hasattr(self.feedback, 'testfile.txt'),'File did not get created')

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
