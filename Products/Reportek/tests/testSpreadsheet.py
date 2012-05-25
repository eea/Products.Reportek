import os, sys, transaction
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from configurereportek import ConfigureReportek
from fileuploadmock import FileUploadMock
from mock import patch
from utils import create_temp_reposit

TEST_DATA_URL = ('https://svn.eionet.europa.eu/repositories/Zope'
                 '/trunk/Products.Reportek/Products/Reportek/tests/data/')
TESTDIR = os.path.abspath(os.path.dirname(__file__))


def setUpModule():
    global cleanup_temp_reposit
    cleanup_temp_reposit = create_temp_reposit()


def tearDownModule():
    cleanup_temp_reposit()


class FileUploadTest(file):
    __allow_access_to_unprotected_subobjects__=1

    def __init__(self, path, name):
        self.filename = name
        file.__init__(self, os.path.join(TESTDIR, path))


class SpreadsheetTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    def afterSetUp(self):
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        self.envelope = self.createStandardEnvelope()
        from Products.Reportek import EnvelopeCustomDataflows
        self._orig_invoke = EnvelopeCustomDataflows.invoke_conversion_service
        transaction.begin()

    def test_upload_nothing(self):
        """ Check convert_excel_file when no file is uploaded
            The expected result is -1
        """
        res = self.envelope.convert_excel_file('')
        # Test the *effect* of the call.
        self.assertEquals(0, len(self.envelope.objectIds('Report Document')))
        self.assertEquals(-1, res)

    def x_test_convert_text(self):
        """ Create a text document in the envelope and try to convert to XML
            This doesn't work, but the original file is uploaded
            Verify the content_type is text/plain
        """
        myfile = FileUploadMock('C:\\TEMP\\testfile.txt','content here')
        res = self.envelope.convert_excel_file(myfile)
        self.assertEquals(0, res)
        # Test the *effect* of the call.
        document = self.envelope['testfile.txt']
        self.assertEquals('text/plain', document.content_type)

    def test_upload_empty_xml(self):
        """ Check convert_excel_file when an empty template is uploaded
            The conversion works but it doesn't produce XML files
            The original file is uploaded
            Verify the content_type is 'application/vnd.ms-excel'
            The expected result is 0
        """
        myfile = FileUploadMock('C:\\TEMP\\testfile.xml','''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="de"
        xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
         </report>''')
        self.envelope.manage_addDocument('testfile.xml', 'Title', myfile)
        document = self.envelope['testfile.xml']
        self.assertEquals('text/xml', document.content_type)

    @patch('Products.Reportek.EnvelopeCustomDataflows.invoke_conversion_service')
    def test_upload_empty_excel(self, mock_invoke):
        test_url = TEST_DATA_URL + 'Rivers_empty.xls'
        def test_invoke(server_name, method_name, url):
            # replace the URL with a public SVN URL
            return self._orig_invoke(server_name, method_name, test_url)
        mock_invoke.side_effect = test_invoke

        myfile = FileUploadTest('data/Rivers_empty.xls','Rivers_empty.xls')
        res = self.envelope.convert_excel_file(myfile)
        self.assertEquals(1, res)
        document = self.envelope['Rivers_empty.xls']
        self.assertEquals('application/vnd.ms-excel', document.content_type)
        self.assertEquals([], [x for x in self.envelope.objectValues('Report Document') if x.content_type == 'text/xml'])

    @patch('Products.Reportek.EnvelopeCustomDataflows.invoke_conversion_service')
    def test_convert_excel(self, mock_invoke):
        """ Check convert_excel_file when an correct template is uploaded
            The conversion works and produces XML files in the envelope
            The original file is also uploaded
            Verify the content_type is 'application/vnd.ms-excel'
            The expected result is 1
        """
        test_url = TEST_DATA_URL + 'Rivers_2011.xls'
        def test_invoke(server_name, method_name, url):
            # replace the URL with a public SVN URL
            return self._orig_invoke(server_name, method_name, test_url)
        mock_invoke.side_effect = test_invoke

        myfile = FileUploadTest('data/Rivers_2011.xls','Rivers_2011.xls')
        res = self.envelope.convert_excel_file(myfile)
        self.assertEquals(1, res)
        self.assertEquals(5, len(self.envelope.objectValues('Report Document')))
        document = self.envelope['Rivers_2011.xls']
        self.assertEquals('application/vnd.ms-excel', document.content_type)
        document = self.envelope['Rivers_2011_StationsRivers.xml']
        self.assertEquals('text/xml', document.content_type)
        feedback = self.envelope['conversion_log_Rivers_2011.xls']
        self.assertEquals(feedback.meta_type, 'Report Feedback')
        #Now try it again to make sure there's no error in deleting old files
        myfile = FileUploadTest('data/Rivers_2011.xls','Rivers_2011.xls')
        res = self.envelope.convert_excel_file(myfile)
        self.assertEquals(1, res)
        self.assertEquals(5, len(self.envelope.objectValues('Report Document')))


def test_suite():
    import unittest
    suite = unittest.makeSuite(SpreadsheetTestCase)
    return suite

if __name__ == '__main__':
    framework()

