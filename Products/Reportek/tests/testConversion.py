import os, sys
import unittest
from Testing import ZopeTestCase
from configurereportek import ConfigureReportek
from fileuploadmock import FileUploadMock
from utils import create_temp_reposit
from zExceptions import Redirect
from mock import patch

ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')

from Products.Reportek.constants import WEBQ_XML_REPOSITORY, CONVERTERS_ID
from Products.Reportek.Converters import Converters
from Products.Reportek.Converter import Converter


def setUpModule(self):
    self._cleanup_temp_reposit = create_temp_reposit()


def tearDownModule(self):
    self._cleanup_temp_reposit()


class FundamentalsTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def test_absolute_url(self):
        """ Small test to see if absolute_url returns the expected """
        self.assertEquals("http://nohost" , self.app.absolute_url())

    def test_servername(self):
        """ Check that the remote_converter is available and configured"""
        server_name = getattr(self.app, CONVERTERS_ID).remote_converter
        self.assertEquals("http://converters.eionet.europa.eu/RpcRouter", server_name)

class ConvertersTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    def afterSetUp(self):
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        self.envelope = self.createStandardEnvelope()

    def create_text_document(self):
        """ Supporting method
            Create a text document in the envelope
            Verify the content_type is text/plain
        """
        myfile = FileUploadMock('C:\\TEMP\\testfile.txt','content here')
        self.envelope.manage_addProduct['Reportek'].manage_addDocument('documentid',
          'Title', myfile)
        self.document = self.envelope.documentid
        self.assertEquals('text/plain', self.document.content_type)

    def test_hasConvertersObj(self):
        """ Check that there are no converters in the beginning """
        converters = getattr(self.app, CONVERTERS_ID)
        self.assertNotEqual(None, converters)
        local_converters, remote_converters = converters.displayPossibleConversions('text/plain')
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    def test_addLocalConverter(self):
        """ Add a local converter, check it is found, run a simple conversion """
        converters = getattr(self.app, CONVERTERS_ID)
        converters.manage_addConverter('reversetxt', title='Reverse', convert_url='rev %s', ct_input='text/plain', ct_output='text/plain')
        local_converters, remote_converters = converters.displayPossibleConversions('text/plain')
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        self.create_text_document()
        res = converters.reversetxt(self.document.absolute_url(1), converter_id='reversetxt', REQUEST=self.app.REQUEST)
        self.assertEquals('ereh tnetnoc\n', res)

    @patch.object(Converters, '_http_params')
    def test_suffixConverter(self, mock_http_params):
        """ Add a local pdf converter, check it is found on suffix """
        mock_http_params.return_value = []
        converters = getattr(self.app, CONVERTERS_ID)
        converters.manage_addConverter('reversetxt', title='Reverse',
               convert_url='pdf2txt %s', ct_input='application/pdf',
               ct_output='text/plain', suffix="pdf")
        # Lookup on content-type alone
        local_converters, remote_converters = converters.displayPossibleConversions('text/pdf')
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Lookup on suffix should fail in this case (no local converters)
        # because the mime type is not application/octet-stream and
        # there's no convertor accepting this mime-type
        local_converters, remote_converters = converters.displayPossibleConversions(
                                                  'text/pdf',
                                                  filename="myfile.pdf")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Check that the same converter is only listed once
        local_converters, remote_converters = converters.displayPossibleConversions(
                                                  'application/pdf',
                                                  filename="myfile.pdf")
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch('Products.Reportek.Converter.extension')
    @patch.object(Converters, '_http_params')
    def test_extension_detection_based_on_mimetype(self, mock_http_params, mock_extension):
        mock_http_params.return_value = [
            [
              "http_test",
              "Test converter",
              "convert/test",
              [
                "test/mime"
              ],
              "text/plain",
              "",
              [],
              "",
              ""
            ]
        ]

        mock_extension.return_value = 'tst'
        converters = getattr(self.app, CONVERTERS_ID)
        loc = converters._get_local_converters()
        assert len(loc)==1
        self.assertEqual(loc[0].suffix, 'tst')

    def test_nullSuffixConverter(self):
        """ Add a local pdf converter, check it is *not* found on suffix, because filename ends with . """
        converters = getattr(self.app, CONVERTERS_ID)
        converters.manage_addConverter('pdftext', title='Show as text',
               convert_url='pdf2txt %s', ct_input='application/pdf',
               ct_output='text/plain', suffix="")
        # Some people end the filename with a period - giving an empty suffix
        local_converters, remote_converters = converters.displayPossibleConversions('text/plain',filename="myfile.")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Some people has no period in the filename
        local_converters, remote_converters = converters.displayPossibleConversions('text/plain',filename="myfile")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch.object(Converters, '_http_params')
    def test_anonymousXml(self, mock_http_params):
        """ Test XML without schema """
        mock_http_params.return_value = []
        converters = getattr(self.app, CONVERTERS_ID)
        converters.manage_addConverter('prettyxml', title='Pretty XML',
                convert_url='xml2txt %s', ct_input='text/xml', ct_output='text/plain',
                ct_schema='', suffix="xml")
        # Lookup on content-type alone, must work, since converter was added with no schema
        local_converters, remote_converters = converters.displayPossibleConversions('text/xml')
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Lookup on filename, must work, since converter was added with no schema
        local_converters, remote_converters = converters.displayPossibleConversions('application/octet-stream', filename="xxx.xml")
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch.object(Converters, '_http_params')
    @patch('Products.Reportek.Converters.xmlrpclib')
    def test_suffixXmlConverter(self, mock_xmlrpclib, mock_http_params):
        """ Add a local XML converter, check it is found on suffix """
        mock_http_params.return_value = []
        server = mock_xmlrpclib.ServerProxy.return_value
        server.ConversionService.listConversions.return_value = []

        converters = getattr(self.app, CONVERTERS_ID)
        converters.manage_addConverter('prettyxml', title='Pretty XML',
                convert_url='xml2txt %s', ct_input='text/xml', ct_output='text/plain',
                ct_schema='http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd',
                suffix="xml")
        # Lookup on content-type alone, not supposed to work as content-type must also match
        local_converters, remote_converters = converters.displayPossibleConversions('text/xml')
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Lookup on schema
        server.ConversionService.listConversions.return_value = [{
            'description': 'Quickview in HTML',
            'content_type_out': 'text/html;charset=UTF-8',
            'xml_schema': ('http://biodiversity.eionet.europa.eu/'
                           'schemas/dir9243eec/generalreport.xsd'),
            'result_type': 'HTML',
            'xsl': 'art17-general.xsl',
            'convert_id': '26',
        },
        {
            'description': 'RDF output',
            'content_type_out': 'application/rdf+xml;charset=UTF-8',
            'xml_schema': ('http://biodiversity.eionet.europa.eu/'
                           'schemas/dir9243eec/generalreport.xsd'),
            'result_type': 'RDF',
            'xsl': 'art17-general-rdf.xsl',
            'convert_id': '179',
        }]
        local_converters, remote_converters = converters.displayPossibleConversions('text/xml',
           "http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd")
        self.assertEquals(1, len(local_converters))
        self.assertTrue(len(remote_converters) > 0)

        server.ConversionService.listConversions.return_value = []
        # Lookup on suffix or content-type, using a non-existing schema. Must not work
        local_converters, remote_converters = converters.displayPossibleConversions('text/xml',
           "http://localhost/schemas/dir5243eec/schema.xsd","generalreport.xml")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Lookup on suffix, using a non-existing schema. Must not work
        local_converters, remote_converters = converters.displayPossibleConversions('text/xml',
           "http://localhost/schemas/dir5243eec/schema.xsd","generalreport.xml")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch('Products.Reportek.Converters.xmlrpclib')
    def test_gmlConverter(self, mock_xmlrpclib):
        """ GML files ends by .gml """

        server = mock_xmlrpclib.ServerProxy.return_value
        server.ConversionService.listConversions.return_value = [{
            'description': 'GML metadata factsheet',
            'content_type_out': 'text/html;charset=UTF-8',
            'xml_schema': ('http://biodiversity.eionet.europa.eu/'
                           'schemas/dir9243eec/gml_art17.xsd'),
            'result_type': 'HTML',
            'xsl': 'art17-gml.xsl',
            'convert_id': '42',
        }]

        # Browsers might send application/octet-stream, text/xml or application/vnd.ogc.gml
        # when uploading a GML file. Therefore we sniff the suffix (currently hardwired)
        # We check in testDocument.py that the sniff works, so we can just assume it here
        # http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd
        converters = getattr(self.app, CONVERTERS_ID)
        converters.manage_addConverter('gmlaspng', title='GML as image',
                convert_url='gml2png %s', ct_input='text/xml', ct_output='image/png',
                ct_schema='http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd', suffix="gml")
        local_converters, remote_converters = converters.displayPossibleConversions('text/xml',
           "http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd","map-dist.gml")
        self.assertEquals(1, len(local_converters))
        # Create a converter without suffix
        converters.manage_addConverter('gmlaswobgr', title='GML as image without background',
                convert_url='gml2png %s', ct_input='text/xml', ct_output='image/png',
                ct_schema='http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd')
        local_converters, remote_converters = converters.displayPossibleConversions('text/xml',
           "http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd","map-dist.gml")
        self.assertEquals(2, len(local_converters))

    def testDefaultIdException(self):
        converters = getattr(self.app, CONVERTERS_ID)
        self.create_text_document()
        with self.assertRaises(Redirect) as raised:
            converters.run_conversion(self.document.absolute_url(1),
                                       converter_id='default',
                                       REQUEST=self.app.REQUEST)

    def testImageException(self):
        converters = getattr(self.app, CONVERTERS_ID)
        self.create_text_document()
        converters.manage_addConverter('reversetxt', title='Reverse',
               convert_url='pdf2txt %s', ct_input='image/jpg',
               ct_output='text/plain', suffix="pdf")
        self.document.content_type = 'image/'
        with self.assertRaises(Redirect) as raised:
            converters.run_conversion(self.document.absolute_url(1),
                                       converter_id='reversetxt',
                                       REQUEST=self.app.REQUEST)

    def testUnknownSourceException(self):
        converters = getattr(self.app, CONVERTERS_ID)
        self.create_text_document()
        converters.manage_addConverter('reversetxt', title='Reverse',
               convert_url='pdf2txt %s', ct_input='image/jpg',
               ct_output='text/plain', suffix="pdf")
        self.document.content_type = 'image/'
        with self.assertRaises(Redirect) as raised:
            converters.run_conversion(self.document.absolute_url(1),
                                       converter_id='reversetxt',
                                       source='xyz',
                                       REQUEST=self.app.REQUEST)

    def test_local_conversion(self):
        converters = getattr(self.app, CONVERTERS_ID)
        self.create_text_document()
        converters.manage_addConverter('reversetxt', title='Reverse', convert_url='rev %s', ct_input='text/plain', ct_output='text/plain')
        result = converters.run_conversion(self.document.absolute_url(1),
                                       converter_id='reversetxt',
                                       source='local',
                                       REQUEST=self.app.REQUEST)
        self.assertIn('ereh tnetnoc\n', result)
