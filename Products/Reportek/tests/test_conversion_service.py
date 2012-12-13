import unittest
import requests
from path import path
from utils import create_fake_root
from common import create_mock_request
from mock import patch, Mock
from Products.Reportek.Converters import Converters
from Products.Reportek.Converter import Converter, LocalHttpConverter
from Products.Reportek import conversion_registry


def CONVERTER_PARAMS():
    return dict(
    {
        'id': 'http_rar2list',
        'title': 'List contents',
        'convert_url': 'convert/rar2list',
        'ct_input': '',
        'ct_output': '',
        'ct_schema': '',
        'ct_extraparams': '',
        'description': '',
        'suffix': ''
    })


class ConversionServiceTest(unittest.TestCase):

    def setUp(self):
        self.app = create_fake_root()
        self.app._setObject('Converters', Converters())
        self.prefix = 'http_'
        from ZPublisher.BaseRequest import RequestContainer
        self.app = self.app.__of__(RequestContainer(REQUEST=create_mock_request()))

    @patch.object(Converters, '_get_local_converters')
    def test_only_http_converters(self, mock_local_converters):
        """no local converters, only http"""
        converters = [LocalHttpConverter(**CONVERTER_PARAMS()) \
                          .__of__(self.app.Converters)]
        params = CONVERTER_PARAMS()
        params.update({'id': 'http_list_7zip'})
        converters.append(LocalHttpConverter(**params) \
                              .__of__(self.app.Converters))
        mock_local_converters.return_value = converters
        local_converters = self.app.Converters._get_local_converters()
        self.assertEqual(['%srar2list' %self.prefix, '%slist_7zip' %self.prefix],
                         [conv.id for conv in local_converters]
        )

    @patch.object(Converters, '_get_local_converters')
    @patch('Products.Reportek.Converter.requests')
    def test_http_converter(self, mock_requests, mock_local_converters):
        from fileuploadmock import FileUploadMock
        from Products.Reportek.Document import Document

        document = Document('testfile', '', content_type= "application/x-rar-compressed")
        self.app._setObject( 'testfile', document)
        with self.app.testfile.data_file.open('wb') as datafile:
            tests = path(__file__).parent.abspath()
            datafile.write((tests / 'onefile.rar').bytes())

        mock_local_converters.return_value = [LocalHttpConverter(**CONVERTER_PARAMS()) \
                                                  .__of__(self.app.Converters)]
        local_converters = self.app.Converters._get_local_converters()

        #assert Anonymous is unauthorized to see this file
        import zExceptions
        with self.assertRaises(zExceptions.Unauthorized):
            local_converters[0](
                file_url=self.app.testfile.absolute_url(),
                converter_id='http_rar2list')

        #override normal behaviour
        #allow current user (Anonymous) to see this file
        self.app.testfile._View_Permission = ('Anonymous', )

        #no exception should be raised now
        mock_requests.post.return_value = Mock(content='fisier.txt')
        result = local_converters[0](
                    file_url=self.app.testfile.absolute_url(),
                    converter_id='http_rar2list')
        self.assertIn('fisier.txt', result)

    @patch.object(Converters, '_get_local_converters')
    @patch('Products.Reportek.Converter.requests')
    def test_run_conversion_http(self, mock_requests, mock_local_converters):
        from fileuploadmock import FileUploadMock
        from Products.Reportek.Document import Document
        mock_local_converters.return_value = [LocalHttpConverter(**CONVERTER_PARAMS()) \
                                                  .__of__(self.app.Converters)]
        document = Document('testfile', '', content_type= "application/x-rar-compressed")
        self.app._setObject( 'testfile', document)
        with self.app.testfile.data_file.open('wb') as datafile:
            tests = path(__file__).parent.abspath()
            datafile.write((tests / 'onefile.rar').bytes())

        from zExceptions import Redirect
        from Products.Reportek.constants import CONVERTERS_ID
        converters = getattr(self.app, CONVERTERS_ID)

        #override normal behaviour
        #allow current user (Anonymous) to see this file
        self.app.testfile._View_Permission = ('Anonymous', )
        mock_requests.post.return_value = Mock(content='mock conversion')
        result = converters.run_conversion(self.app.testfile.absolute_url(),
                                   converter_id='%srar2list' %self.prefix,
                                   source = 'local')
        self.assertEqual('mock conversion', result)

    @patch('Products.Reportek.Converter.xmlrpclib')
    def test_run_conversion_remote(self, mock_xmlrpclib):

        from Products.Reportek.Document import Document
        document = Document('testfile', '', content_type= "application/x-rar-compressed")
        self.app.Converters._setObject( 'testfile', document)

        with self.app.Converters.testfile.data_file.open('wb') as datafile:
            datafile.write('test file')

        server = mock_xmlrpclib.ServerProxy.return_value
        expected = {}
        expected['content'] = Mock(data='txtesrever')
        expected['content-type'] = 'mock/content-type'
        expected['filename'] = 'testfile'
        server.ConversionService.convert.return_value = expected
        self.app.REQUEST = Mock(SESSION='')

        params = {'file_url': 'Converters/testfile',
                  'converter_id': '',
                  'source': 'remote',
                  'REQUEST': {'source': 'remote', 'file_url': 'Converters/testfile', 'conv': ''}}
        #assert Anonymous is unauthorized to see this file
        import zExceptions
        with self.assertRaises(zExceptions.Unauthorized):
            self.app.Converters.run_conversion(**params)

        #override normal behaviour
        #allow current user (Anonymous) to see this file
        self.app.Converters.testfile._View_Permission = ('Anonymous', )
        self.app.Converters.note = Mock(return_value='')
        result = self.app.Converters.run_conversion(**params)
        self.assertEqual('txtesrever', result)

    @patch.object(Converters, '_http_params')
    def test_converter_ct_extraparams_attribute(self, mock_http_params):
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
              ['country_code'],
              "",
              "xml"
            ]
        ]
        [conv] = self.app.Converters._get_local_converters()
        self.assertEqual(['country_code'], conv.ct_extraparams)

    @patch.object(conversion_registry, 'get_country_code')
    @patch.object(Converters, '_http_params')
    def test_conversion_registry_with_good_key(self, mock_http_params,
                                              mock_get_country_code):
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
              ['country_code'],
              "",
              "xml"
            ]
        ]

        mock_get_country_code.return_value = 'AT'
        [conv] = self.app.Converters._get_local_converters()
        self.assertEqual(
                ['AT'],
                conversion_registry.request_params(conv.ct_extraparams))

    @patch.object(conversion_registry, 'get_country_code')
    @patch.object(Converters, '_http_params')
    def test_conversion_registry_with_non_existing_key(self, mock_http_params,
                                              mock_get_country_code):
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
              ['bad_key'],
              "",
              "xml"
            ]
        ]

        [conv] = self.app.Converters._get_local_converters()
        self.assertRaises(
            NotImplementedError,
            conversion_registry.request_params,
            conv.ct_extraparams
        )

    @patch.object(conversion_registry, 'get_country_code')
    @patch.object(Converters, '_http_params')
    @patch('Products.Reportek.Converter.requests')
    def test_conversion_output_with_extraparams( self,
            mock_requests, mock_http_params, mock_get_country_code):
        mock_http_params.return_value = [
            [
              "rar2list",
              "Pretty XML",
              "convert/xml2txt",
              [
                "text/plain"
              ],
              "text/plain",
              "",
              ['country_code'],
              "",
              "xml"
            ]
        ]

        mock_get_country_code.return_value = 'AT'
        [conv] = self.app.Converters._get_local_converters()
        from Products.Reportek.Document import Document
        document = Document('testfile', '', content_type= "application/x-rar-compressed")
        self.app.Converters._setObject( 'testfile', document)

        with self.app.Converters.testfile.data_file.open('wb') as datafile:
            datafile.write('test file')

        self.app.Converters.testfile._View_Permission = ('Anonymous', )
        file_url = '/Converters/testfile'
        converter_id = conv.id
        conv(file_url, converter_id)
        files = mock_requests.mock_calls[0][2]['files']
        data = mock_requests.mock_calls[0][2]['data']
        assert files['file']
        self.assertEqual({'extraparams': ['AT']}, data)

class ConversionRegistryTest(unittest.TestCase):

    def setUp(self):
        self.app = create_fake_root()
        self.app._setObject('Converters', Converters())
        #self.prefix = 'http_'
        #from ZPublisher.BaseRequest import RequestContainer
        #self.app = self.app.__of__(RequestContainer(REQUEST=create_mock_request()))

    @patch.object(Converters, '_http_params')
    def test_get_country_code(self, mock_http_params):
        mock_http_params.return_value = [
            [
              "rar2list",
              "Pretty XML",
              "convert/xml2txt",
              [
                "text/plain"
              ],
              "text/plain",
              "",
              ['country_code'],
              "",
              "xml"
            ]
        ]
        [conv] = self.app.Converters._get_local_converters()
        envelope = Mock()
        envelope.getCountryCode = Mock(return_value='AT')
        self.assertEqual(
                ['AT'],
                conversion_registry.request_params(['country_code'], obj=envelope)
        )
