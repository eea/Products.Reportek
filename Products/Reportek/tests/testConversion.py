# flake8: noqa
from Products.Reportek.Converters import Converters
from Products.Reportek.constants import CONVERTERS_ID
from common import BaseTest
from mock import Mock
from Testing import ZopeTestCase
from common import ConfigureReportek
from fileuploadmock import FileUploadMock
from zExceptions import Redirect
from mock import patch

ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')


class FundamentalsTestCase(BaseTest):

    _setup_fixture = 0

    def afterSetUp(self):
        super(FundamentalsTestCase, self).afterSetUp()
        setattr(self.root.getPhysicalRoot(), CONVERTERS_ID, Converters())
        safe_html = Mock(convert=Mock(text='feedbacktext'))
        getattr(self.root.getPhysicalRoot(), CONVERTERS_ID).__getitem__ = Mock(
            return_value=safe_html)

    def test_absolute_url(self):
        """ Small test to see if absolute_url returns the expected """
        self.assertEquals("http://nohost", self.app.absolute_url())

    def test_servername(self):
        """ Check that the remote_converter is available and configured"""
        server_name = getattr(self.app, CONVERTERS_ID).remote_converter
        self.assertEquals(
            "http://converters.eionet.europa.eu/RpcRouter", server_name)


class ConvertersTestCase(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(ConvertersTestCase, self).afterSetUp()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),
                        'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        self.envelope = self.createStandardEnvelope()
        setattr(self.root.getPhysicalRoot(), CONVERTERS_ID, Converters())
        safe_html = Mock(convert=Mock(text='feedbacktext'))
        getattr(self.root.getPhysicalRoot(), CONVERTERS_ID).__getitem__ = Mock(
            return_value=safe_html)

    def create_text_document(self):
        """ Supporting method
            Create a text document in the envelope
            Verify the content_type is text/plain
        """
        myfile = FileUploadMock('C:\\TEMP\\testfile.txt', 'content here')
        self.envelope.manage_addProduct['Reportek'].manage_addDocument(
            'documentid',
            'Title', myfile)
        self.document = getattr(self.envelope, 'documentid.txt')
        self.assertEquals('text/plain', self.document.content_type)

    @patch.object(Converters, '_http_params')
    def test_hasConvertersObj(self, mock_http_params):
        """ Check that there are no converters in the beginning """
        mock_http_params.return_value = []
        converters = getattr(self.app, CONVERTERS_ID)
        self.assertNotEqual(None, converters)
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'text/plain')
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch.object(Converters, '_http_params')
    def test_addLocalConverter(self, mock_http_params):
        """ Add a local converter, check it is found, run a simple conversion
        """
        mock_http_params.return_value = [
            [
                "prettyxml",
                "Pretty XML",
                "convert/xml2txt",
                [
                    "text/plain"
                ],
                "text/plain",
                "",
                [],
                "",
                "xml"
            ]
        ]
        converters = getattr(self.app, CONVERTERS_ID)
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'text/plain')
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch.object(Converters, '_http_params')
    def test_suffixConverter(self, mock_http_params):
        """ Add a local pdf converter, check it is found on suffix """
        mock_http_params.return_value = [
            [
                "reversetxt",
                "Reverse",
                "convert/pdf2txt",
                [
                    "application/pdf"
                ],
                "text/plain",
                "",
                [],
                "",
                "pdf"
            ]
        ]
        converters = getattr(self.app, CONVERTERS_ID)
        # Lookup on content-type alone
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'text/pdf')
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Lookup on suffix alone
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'text/pdf',
            filename="myfile.pdf")
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Check that the same converter is only listed once
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'application/pdf',
            filename="myfile.pdf")
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch('Products.Reportek.Converter.extension')
    @patch.object(Converters, '_http_params')
    def test_extension_detection_based_on_mimetype(self, mock_http_params,
                                                   mock_extension):
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
        assert len(loc) == 1
        self.assertEqual(loc[0].suffix, 'tst')

    @patch.object(Converters, '_http_params')
    def test_nullSuffixConverter(self, mock_http_params):
        """ Add a local pdf converter, check it is *not* found on suffix,
            because filename ends with . """
        mock_http_params.return_value = []
        converters = getattr(self.app, CONVERTERS_ID)
        converters.manage_addConverter('pdftext', title='Show as text',
                                       convert_url='pdf2txt %s',
                                       ct_input='application/pdf',
                                       ct_output='text/plain', suffix="")
        # Some people end the filename with a period - giving an empty suffix
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'text/plain', filename="myfile.")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Some people has no period in the filename
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'text/plain', filename="myfile")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch.object(Converters, '_http_params')
    def test_anonymousXml(self, mock_http_params):
        """ Test XML without schema """
        mock_http_params.return_value = [
            [
                "http_test",
                "Test xml",
                "convert/test",
                [
                    "text/xml"
                ],
                "text/plain",
                "",
                [],
                "",
                "xml"
            ]
        ]
        converters = getattr(self.app, CONVERTERS_ID)
        # Lookup on content-type alone, must work, since converter was added
        # with no schema
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'text/xml')
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Lookup on filename, must work, since converter was added with no
        # schema
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'application/octet-stream', filename="xxx.xml")
        self.assertEquals(1, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch.object(Converters, '_http_params')
    @patch('Products.Reportek.Converters.xmlrpclib')
    def test_suffixXmlConverter(self, mock_xmlrpclib, mock_http_params):
        """ Add a local XML converter, check it is found on suffix """
        mock_http_params.return_value = [
            [
                "prettyxml",
                "Pretty XML",
                "convert/xml2txt",
                [
                    "text/xml"
                ],
                "text/plain",
                'http://biodiversity.eionet.europa.eu/schemas/'
                'dir9243eec/generalreport.xsd',
                [],
                "",
                "xml"
            ]
        ]
        server = mock_xmlrpclib.ServerProxy.return_value
        server.ConversionService.listConversions.return_value = []

        converters = getattr(self.app, CONVERTERS_ID)
        # Lookup on content-type alone, not supposed to work as content-type
        # must also match
        local_converters, remote_converters = converters.displayPossibleConversions(  # noqa
            'text/xml')
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
                                                                                    "http://localhost/schemas/dir5243eec/schema.xsd", "generalreport.xml")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))
        # Lookup on suffix, using a non-existing schema. Must not work
        local_converters, remote_converters = converters.displayPossibleConversions('text/xml',
                                                                                    "http://localhost/schemas/dir5243eec/schema.xsd", "generalreport.xml")
        self.assertEquals(0, len(local_converters))
        self.assertEquals(0, len(remote_converters))

    @patch.object(Converters, '_http_params')
    @patch('Products.Reportek.Converters.xmlrpclib')
    def test_gmlConverter(self, mock_xmlrpclib, mock_http_params):
        """ GML files ends by .gml """
        mock_http_params.return_value = [
            [
                "gmlaspng",
                "GML as image",
                "convert/gml2png",
                [
                    "text/xml"
                ],
                "image/png",
                'http://biodiversity.eionet.europa.eu/schemas/'
                'dir9243eec/gml_art17.xsd',
                [],
                "",
                "gml"
            ]
        ]

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
        (local_converters, remote_converters) = \
            converters.displayPossibleConversions(
            'text/xml',
            "http://biodiversity.eionet.europa.eu/schemas/"
            "dir9243eec/gml_art17.xsd", "map-dist.gml"
        )
        self.assertEquals(1, len(local_converters))
        mock_http_params.return_value = [
            [
                "gmlaspng",
                "GML as image",
                "convert/gml2png",
                [
                    "text/xml"
                ],
                "image/png",
                'http://biodiversity.eionet.europa.eu/schemas/'
                'dir9243eec/gml_art17.xsd',
                [],
                "",
                "gml"
            ],
            [
                "gmlaswobgr",
                "GML as image without background",
                "convert/gml2png",
                [
                    "text/xml"
                ],
                "image/png",
                "http://biodiversity.eionet.europa.eu/schemas/"
                "dir9243eec/gml_art17.xsd",
                [],
                "",
                "gml"
            ]
        ]
        # Create a converter without suffix
        (local_converters, remote_converters) = \
            converters.displayPossibleConversions(
                'text/xml',
                "http://biodiversity.eionet.europa.eu/schemas/"
                "dir9243eec/gml_art17.xsd", "map-dist.gml")
        self.assertEquals(2, len(local_converters))

    @patch.object(Converters, '_http_params')
    def test_xml_converters_without_schema_accepted(self, mock_http_params):
        """Test that matching converters (based on mime/type or suffix) without a
        schema are detected when trying to convert an xml type document that
        has a schema"""
        mock_http_params.return_value = [
            [
                "gmlaspng",
                "GML as image",
                "convert/gml2png",
                [
                    "text/xml"
                ],
                "image/png",
                '',  # empty schema
                [],
                "",
                "gml"
            ]
        ]
        converters = getattr(self.app, CONVERTERS_ID)
        (local_converters, remote_converters) = \
            converters.displayPossibleConversions(
            'text/xml',
            "http://biodiversity.eionet.europa.eu/schemas/"
            "dir9243eec/gml_art17.xsd", "map-dist.gml"
        )
        self.assertEquals(1, len(local_converters))

    @patch.object(Converters, '_http_params')
    def test_xml_converters_with_bad_schema_rejected(self, mock_http_params):
        """Test that matching converters (based on mime/type or suffix) with a
        schema are not detected if their schema is different than document's
        schema"""
        mock_http_params.return_value = [
            [
                "gmlaspng",
                "GML as image",
                "convert/gml2png",
                [
                    "text/xml"
                ],
                "image/png",
                'bad_schema',
                [],
                "",
                "gml"
            ]
        ]
        converters = getattr(self.app, CONVERTERS_ID)
        (local_converters, remote_converters) = \
            converters.displayPossibleConversions(
            'text/xml',
            "good_schema",
            "map-dist.gml"
        )
        self.assertEquals(0, len(local_converters))

    def testDefaultIdException(self):
        converters = getattr(self.app, CONVERTERS_ID)
        self.create_text_document()
        with self.assertRaises(Redirect):
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
        with self.assertRaises(Redirect):
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
        with self.assertRaises(Redirect):
            converters.run_conversion(self.document.absolute_url(1),
                                      converter_id='reversetxt',
                                      source='xyz',
                                      REQUEST=self.app.REQUEST)
