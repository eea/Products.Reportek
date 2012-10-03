import unittest
import requests
from utils import create_fake_root
from Products.Reportek.Converters import Converters
from Products.Reportek.Converter import Converter


class ConversionServiceTest(unittest.TestCase):

    def setUp(self):
        self.app = create_fake_root()
        self.app._setObject('Converters', Converters())
        resp =  requests.get('http://127.0.0.1:5000/params')
        self.prefix = resp.json.get('prefix', '')

    def test_only_http_converters(self):
        """no local converters defined"""
        local_converters = self.app.Converters._get_local_converters()
        self.assertEqual(['%srar2list' %self.prefix, '%slist_7zip' %self.prefix],
                         [conv.id for conv in local_converters]
        )

    def test_with_local_converters(self):
        converter = Converter('list_7zip', title='Reverse',
                              convert_url='rev %s', ct_input='text/plain',
                              ct_output='text/plain', ct_schema='',
                              ct_extraparams=[], description='', suffix='')
        self.app.Converters._setObject('list_7zip', converter)
        local_converters = self.app.Converters._get_local_converters()
        if not self.prefix:
            self.assertEqual(['list_7zip', 'rar2list'],
                             [conv.id for conv in local_converters]
            )
            #assert it's a local converter
            self.assertEqual('Converters/list_7zip', local_converters[0].absolute_url())

            #asert it's a http converter
            self.assertEqual('/convert/rar2list', local_converters[1].convert_url)
        else:
            self.assertEqual([#one local converter
                              'list_7zip',
                              #two http converters with prefix
                              '%srar2list' %self.prefix,
                              '%slist_7zip' %self.prefix],
                             [conv.id for conv in local_converters]
            )

    def test_http_converter(self):
        from fileuploadmock import FileUploadMock
        from Products.Reportek.Document import Document
        document = Document('testfile', '', content_type= "application/x-rar-compressed")
        self.app._setObject( 'testfile', document)
        with self.app.testfile.data_file.open('wb') as datafile:
            datafile.write(open('tests/onefile.rar').read())

        local_converters = self.app.Converters._get_local_converters()

        #assert Anonymous is unauthorized to see this file
        import zExceptions
        with self.assertRaises(zExceptions.Unauthorized):
            local_converters[0](
                file_url=self.app.testfile.absolute_url(),
                converter_id='loc_http_rar2list')

        #override normal behaviour
        #allow current user (Anonymous) to see this file
        self.app.testfile._View_Permission = ('Anonymous', )

        #no exception should be raised now
        result = local_converters[0](
                    file_url=self.app.testfile.absolute_url(),
                    converter_id='loc_http_rar2list')
        self.assertIn('fisier.txt', result)

    def test_run_conversion(self):
        from fileuploadmock import FileUploadMock
        from Products.Reportek.Document import Document
        document = Document('testfile', '', content_type= "application/x-rar-compressed")
        self.app._setObject( 'testfile', document)
        with self.app.testfile.data_file.open('wb') as datafile:
            datafile.write(open('tests/onefile.rar').read())

        from zExceptions import Redirect
        from Products.Reportek.constants import CONVERTERS_ID
        converters = getattr(self.app, CONVERTERS_ID)

        #override normal behaviour
        #allow current user (Anonymous) to see this file
        self.app.testfile._View_Permission = ('Anonymous', )

        result = converters.run_conversion(self.app.testfile.absolute_url(),
                                   converter_id='%srar2list' %self.prefix,
                                   source = 'local')
