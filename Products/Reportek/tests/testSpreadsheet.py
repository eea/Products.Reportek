# flake8: noqa
from Products.Reportek.Converters import Converters
from mock import patch, Mock
from fileuploadmock import FileUploadMock
from common import BaseTest, ConfigureReportek
import os
from StringIO import StringIO
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')

TESTDIR = os.path.abspath(os.path.dirname(__file__))


class SpreadsheetTestCase(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(SpreadsheetTestCase, self).afterSetUp()
        self.createStandardCatalog()
        self.createStandardDependencies()
        self.app._setObject('Converters', Converters())
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),
                        'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        self.envelope = self.createStandardEnvelope()
        self.envelope.manage_addFeedback = Mock(return_value='feedbacktext')

    def test_upload_nothing(self):
        """ Check convert_excel_file when no file is uploaded
            The expected result is -1
        """
        res = self.envelope.convert_excel_file('')
        # Test the *effect* of the call.
        self.assertEquals(0, len(self.envelope.objectIds('Report Document')))
        self.assertEquals(-1, res)

    @patch('transaction.commit')
    @patch('Products.Reportek.EnvelopeCustomDataflows.invoke_conversion_service')  # noqa
    def test_convert_text(self, mock_invoke, mock_commit):
        """ Create a text document in the envelope and try to convert to XML
            This doesn't work, but the original file is uploaded
            Verify the content_type is text/plain
        """
        mock_invoke.return_value = {
            'conversionLog': '-- the log --',
            'convertedFiles': [],
            'resultCode': '2',
            'resultDescription': 'whatever error',
        }
        myfile = FileUploadMock('C:\\TEMP\\testfile.txt', 'content here')
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
        myfile = FileUploadMock('C:\\TEMP\\testfile.xml',
                                '''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="de"
        xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
         </report>''')
        self.envelope.manage_addDocument('testfile.xml', 'Title', myfile)
        document = self.envelope['testfile.xml']
        self.assertEquals('text/xml', document.content_type)

    @patch('transaction.commit')
    @patch('Products.Reportek.EnvelopeCustomDataflows.invoke_conversion_service')
    def test_upload_empty_excel(self, mock_invoke, mock_commit):
        mock_invoke.return_value = {
            'conversionLog': '-- conversion log --',
            'convertedFiles': [],
            'resultCode': '0',
            'resultDescription': 'Conversion successful.',
        }
        myfile = StringIO('-- some reporting data --')
        myfile.filename = 'Rivers_empty.xls'
        res = self.envelope.convert_excel_file(myfile)
        self.assertEquals(1, res)
        document = self.envelope['Rivers_empty.xls']
        self.assertEquals('application/vnd.ms-excel', document.content_type)
        self.assertEquals([], [x for x in self.envelope.objectValues(
            'Report Document') if x.content_type == 'text/xml'])

    @patch('transaction.commit')
    @patch('Products.Reportek.EnvelopeCustomDataflows.invoke_conversion_service')
    def test_convert_excel(self, mock_invoke, mock_commit):
        """ Check convert_excel_file when an correct template is uploaded
            The conversion works and produces XML files in the envelope
            The original file is also uploaded
            Verify the content_type is 'application/vnd.ms-excel'
            The expected result is 1
        """
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="https://schema.eu/schema1 https://schema.eu/schema.xsd">
         </report>'''

        mock_invoke.return_value = {
            'conversionLog': '-- conversion log --',
            'convertedFiles': [{'content': Mock(data=xml_content),
                                'fileName': 'StationsRivers.xml'},
                               {'content': Mock(data=xml_content),
                                'fileName': 'NutrientsRivers_Agg.xml'},
                               {'content': Mock(data=xml_content),
                                'fileName': 'HazSubstRivers_Agg.xml'},
                               {'content': Mock(data=xml_content),
                                'fileName': 'HazSubstRivers_Disagg.xml'}],
            'resultCode': '0',
            'resultDescription': 'Conversion successful.',
        }
        myfile = StringIO('-- some reporting data --')
        myfile.filename = 'Rivers_2011.xls'
        res = self.envelope.convert_excel_file(myfile)
        self.assertEquals(1, res)
        self.assertEquals(
            5, len(self.envelope.objectValues('Report Document')))
        document = self.envelope['Rivers_2011.xls']
        self.assertEquals('application/vnd.ms-excel', document.content_type)
        document = self.envelope['Rivers_2011_StationsRivers.xml']
        self.assertEquals('text/xml', document.content_type)

        # NOTE don't test feedback creation here
        # feedback creation already tested in testFeedback.py
        #feedback = self.envelope['conversion_log_Rivers_2011.xls']
        #self.assertEquals(feedback.meta_type, 'Report Feedback')

        # Now try it again to make sure there's no error in deleting old files
        myfile = StringIO('-- some reporting data --')
        myfile.filename = 'Rivers_2011.xls'
        res = self.envelope.convert_excel_file(myfile)
        self.assertEquals(1, res)
        self.assertEquals(
            5, len(self.envelope.objectValues('Report Document')))
