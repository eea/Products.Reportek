from path import path
from utils import create_fake_root
from common import BaseTest, BaseUnitTest
from mock import patch, Mock, MagicMock, call
from Products.Reportek.Converters import Converters
from Products.Reportek.Converter import LocalHttpConverter
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


class ConversionServiceTest(BaseUnitTest):

    def setUp(self):
        self.app = create_fake_root()
        self.app._setObject('Converters', Converters())
        self.prefix = 'http_'
        from ZPublisher.BaseRequest import RequestContainer
        self.app = self.app.__of__(RequestContainer(
            REQUEST=BaseTest.create_mock_request()))

    @patch.object(Converters, '_get_local_converters')
    def test_only_http_converters(self, mock_local_converters):
        """no local converters, only http"""
        converters = [LocalHttpConverter(**CONVERTER_PARAMS())
                      .__of__(self.app.Converters)]
        params = CONVERTER_PARAMS()
        params.update({'id': 'http_list_7zip'})
        converters.append(LocalHttpConverter(**params)
                          .__of__(self.app.Converters))
        mock_local_converters.return_value = converters
        local_converters = self.app.Converters._get_local_converters()
        self.assertEqual(
            ['%srar2list' % self.prefix, '%slist_7zip' % self.prefix],
            [conv.id for conv in local_converters]
                         )

    @patch.object(Converters, '_get_local_converters')
    @patch('Products.Reportek.Converter.requests')
    def test_http_converter(self, mock_requests, mock_local_converters):
        from Products.Reportek.Document import Document

        document = Document(
            'testfile', '', content_type="application/x-rar-compressed")
        self.app._setObject('testfile', document)
        with self.app.testfile.data_file.open('wb') as datafile:
            tests = path(__file__).parent.abspath()
            datafile.write((tests / 'onefile.rar').bytes())

        mock_local_converters.return_value = [
            LocalHttpConverter(**CONVERTER_PARAMS())
            .__of__(self.app.Converters)]
        local_converters = self.app.Converters._get_local_converters()

        # assert Anonymous is unauthorized to see this file
        import zExceptions
        with self.assertRaises(zExceptions.Unauthorized):
            local_converters[0](
                file_url=self.app.testfile.absolute_url(),
                converter_id='http_rar2list')

        # override normal behaviour
        # allow current user (Anonymous) to see this file
        self.app.testfile._View_Permission = ('Anonymous', )

        # no exception should be raised now
        mock_requests.post.return_value = Mock(content='fisier.txt', headers={
                                               'content-type': 'mock/type'})
        result = local_converters[0](
            file_url=self.app.testfile.absolute_url(),
            converter_id='http_rar2list').content
        self.assertIn('fisier.txt', result)

    @patch.object(Converters, '_get_local_converters')
    @patch('Products.Reportek.Converter.requests')
    def test_run_conversion_http(self, mock_requests, mock_local_converters):
        from Products.Reportek.Document import Document
        mock_local_converters.return_value = [
            LocalHttpConverter(**CONVERTER_PARAMS())
            .__of__(self.app.Converters)]
        document = Document(
            'testfile', '', content_type="application/x-rar-compressed")
        self.app._setObject('testfile', document)
        with self.app.testfile.data_file.open('wb') as datafile:
            tests = path(__file__).parent.abspath()
            datafile.write((tests / 'onefile.rar').bytes())

        from Products.Reportek.constants import CONVERTERS_ID
        converters = getattr(self.app, CONVERTERS_ID)

        # override normal behaviour
        # allow current user (Anonymous) to see this file
        self.app.testfile._View_Permission = ('Anonymous', )
        mock_requests.post.return_value = Mock(
            content='mock conversion', headers={'content-type': 'mock/type'})
        result = converters.run_conversion(
            self.app.testfile.absolute_url(),
            converter_id='%srar2list' % self.prefix,
            source='local')
        self.assertEqual('mock conversion', result)

    @patch('Products.Reportek.Converter.requests')
    def test_run_conversion_remote(self, mock_requests):

        from Products.Reportek.Document import Document
        document = Document(
            'testfile', '', content_type="application/x-rar-compressed")
        self.app.Converters._setObject('testfile', document)

        with self.app.Converters.testfile.data_file.open('wb') as datafile:
            datafile.write('test file')

        mock_resp = MagicMock()
        mock_resp.iter_content = Mock(return_value=['txtesrever'])
        mock_requests.configure_mock(**{'post.return_value': mock_resp})
        self.app.REQUEST = Mock(SESSION='')

        params = {'file_url': 'Converters/testfile',
                  'converter_id': '',
                  'source': 'remote',
                  'REQUEST': {'source': 'remote',
                              'file_url': 'Converters/testfile', 'conv': ''}}
        # assert Anonymous is unauthorized to see this file
        import zExceptions
        with self.assertRaises(zExceptions.Unauthorized):
            self.app.Converters.run_conversion(**params)

        # override normal behaviour
        # allow current user (Anonymous) to see this file
        self.app.Converters.testfile._View_Permission = ('Anonymous', )
        self.app.Converters.note = Mock(return_value='')
        self.app.Converters.run_conversion(**params)
        self.assertEqual(call('txtesrever'),
                         self.app.REQUEST.RESPONSE.write.mock_calls[0])

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
    def test_conversion_output_with_extraparams(self,
                                                mock_requests,
                                                mock_http_params,
                                                mock_get_country_code):
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
        document = Document(
            'testfile', '', content_type="application/x-rar-compressed")
        self.app.Converters._setObject('testfile', document)

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

    @patch.object(Converters, '_http_params')
    @patch('Products.Reportek.Converter.requests')
    def test_shp_conversionr(self, mock_requests, mock_http_params):
        mock_http_params.return_value = [
            [
                "shp2img",
                "Show shapefile as image",
                "convert/shp2img",
                [
                    "application/x-shp"
                ],
                "image/jpeg",
                "",
                [],
                ""
            ]
        ]

        [shp_conv] = self.app.Converters._get_local_converters()
        from Products.Reportek.Document import Document
        document = Document('test.shp', '', content_type="application/x-shp")
        self.app.Converters._setObject('test.shp', document)

        document = Document('test.shx', '', content_type="application/x-shx")
        self.app.Converters._setObject('test.shx', document)

        document = Document('test.dbf', '', content_type="application/dbf")
        self.app.Converters._setObject('test.dbf', document)
        for item in self.app.Converters.objectValues():
            item._View_Permission = ('Anonymous', )
            with item.data_file.open('wb') as datafile:
                datafile.write('test file')

        file_url = '/Converters/test.shp'
        shp_conv(file_url, shp_conv.id)
        files = mock_requests.mock_calls[0][2]['files']
        mock_requests.mock_calls[0][2]['data']
        for item in mock_requests.mock_calls[0][2]['files'].values():
            self.assertEqual('test file', item.read())
        self.assertEqual(set(['file', 'shx', 'dbf']), set(files.keys()))


class ConversionRegistryTest(BaseUnitTest):

    def setUp(self):
        self.app = create_fake_root()
        self.app._setObject('Converters', Converters())
        # self.prefix = 'http_'
        # from ZPublisher.BaseRequest import RequestContainer
        # self.app = self.app.__of__(
        # RequestContainer(REQUEST=create_mock_request()))

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
        file_obj = Mock()
        envelope = Mock()
        envelope.getCountryCode = Mock(return_value='AT')
        file_obj.getParentNode = Mock(return_value=envelope)
        self.assertEqual(
            ['AT'],
            conversion_registry.request_params(['country_code'], obj=file_obj)
        )
