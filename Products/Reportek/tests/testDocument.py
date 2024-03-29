from utils import publish_view
import os
import transaction
from mock import Mock, patch
from utils import (create_temp_reposit, HtmlPage, MockDatabase,
                   break_document_data_file)
from fileuploadmock import FileUploadMock
from common import BaseTest, BaseUnitTest, ConfigureReportek
from zExceptions import Redirect
from StringIO import StringIO
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')


class DocumentTestCase(BaseTest, ConfigureReportek):

    # Currently the physical document is not renamed if the object in ZODB
    # is moved
    # That makes it difficult to work in the file system
    # This variable can be set to true when we start to fix this problem
    physpath_must_track_zodb = False

    def afterSetUp(self):
        super(DocumentTestCase, self).afterSetUp()
        self._cleanup_temp_reposit = create_temp_reposit()

        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),
                        'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        self.envelope = self.createStandardEnvelope()

    def beforeTearDown(self):
        self._cleanup_temp_reposit()

    def create_file(self, path, id, title):
        file = FileUploadMock(path, 'content here')
        add_doc = self.envelope.manage_addProduct[
            'Reportek'].manage_addDocument
        return add_doc(id, title, file)

    def test_upload_nothing_without_id(self):
        r = self.create_file('', '', '')
        self.assertEqual(r, '')

    def test_upload_nothing_with_id_without_ext(self):
        r = self.create_file('', 'id', '')
        self.assertEqual(r, '')

    def test_upload_nothing_with_id_with_ext(self):
        r = self.create_file('', 'f.txt', '')
        self.assertEqual(r, '')

    def test_upload_file_without_id(self):
        self.create_file('C:\\TEMP\\testfile.txt', '', '')
        self.assertEqual(hasattr(self.envelope, 'testfile.txt'), True)

    def test_upload_file_with_id_without_extension(self):
        self.create_file('/TEMP/testfile.txt', 'file', '')
        self.assertEqual(hasattr(self.envelope, 'file.txt'), True)

    def test_upload_file_with_id_with_extension(self):
        self.create_file('C:\\TEMP\\testfile.txt', 'file.xls', '')
        self.assertEqual(hasattr(self.envelope, 'file.xls'), True)

    def test_upload_raw_content_without_id(self):
        add_doc = self.envelope.manage_addProduct[
            'Reportek'].manage_addDocument
        r = add_doc('', 'Title', 'Some content')
        self.assertEqual(r, '')

    def test_upload_raw_content_with_id(self):
        add_doc = self.envelope.manage_addProduct[
            'Reportek'].manage_addDocument
        r = add_doc('file', 'Title', 'Some content')
        self.assertEqual(r, 'file')

    def test_upload_empty_content_with_id(self):
        add_doc = self.envelope.manage_addProduct[
            'Reportek'].manage_addDocument
        r = add_doc('file', 'Title', '')
        self.assertEqual(r, '')

    def test_upload_empty_content_without_id(self):
        add_doc = self.envelope.manage_addProduct[
            'Reportek'].manage_addDocument
        r = add_doc('', 'Title', '')
        self.assertEqual(r, '')

    def create_text_document(self, id='documentid.txt'):
        """ Supporting method
            Create a text document in the envelope
            Verify the content_type is text/plain
        """
        self.create_file('C:\\TEMP\\testfile.txt', id, 'Title')
        self.document = getattr(self.envelope, id)
        self.assertEquals('text/plain', self.document.content_type)

    def test_create_xml_document(self):
        """ Create a simple XML document, and then verify the schema got
            sniffed correctly
        """
        myfile = FileUploadMock('C:\\TEMP\\testfile.xml',
                                '''<?xml version="1.0" encoding="UTF-8"?>
        <report xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xml:lang="de"
        xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd">
         </report>''')
        self.envelope.manage_addProduct[
            'Reportek'].manage_addDocument('documentid',
                                           'Title', myfile)
        self.assertTrue(hasattr(self.envelope, 'documentid.xml'),
                        'Document did not get created')
        document = getattr(self.envelope, 'documentid.xml')
        self.assertEquals('text/xml', document.content_type)
        self.assertEquals(
            'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/generalreport.xsd',  # noqa
            document.xml_schema_location)

    def test_create_gml_document(self):
        """ Verify the application discovers a GML document
        """
        self.create_gml_document('C:\\TEMP\\testfile.gml')

    def test_create_GML_document(self):
        """ Verify the application discovers a GML document even though the
            suffix is capitalised
        """
        self.create_gml_document('C:\\My Documents\\testfile.GML')

    def create_gml_document(self, filename):
        """ Create a GML file in the envelope
            Verify the content_type is text/xml
        """
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<gml:FeatureCollection
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd"
xmlns:gml="http://www.opengis.net/gml"
xmlns:met="http://biodiversity.eionet.europa.eu/schemas/dir9243eec">
</gml:FeatureCollection>'''

        myfile = FileUploadMock(filename, content)
        self.envelope.manage_addProduct[
            'Reportek'].manage_addDocument('documentid',
                                           'Title', myfile)
        _, ext = os.path.splitext(filename)
        document = getattr(self.envelope, 'documentid' + ext)
        self.assertEquals('text/xml', document.content_type)
        self.assertEquals(
            'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd',  # noqa
            document.xml_schema_location)

    def test_restrict_document(self):
        self.create_text_document()
        self.document.manage_restrictDocument()
        assert self.document.acquiredRolesAreUsedBy('View') == ''

        self.document.manage_unrestrictDocument()
        assert self.document.acquiredRolesAreUsedBy('View') == 'CHECKED'

    def test_documents_section(self):
        self.create_text_document()

        page = HtmlPage(self.document.documents_section())
        self.assertEqual(page.select('.filessection legend').text(),
                         'Files in this envelope')
        self.assertEqual(page.select('.filessection table tr td a').text(),
                         'documentid.txt')

    def test_view_image_or_file_exception(self):
        self.create_text_document()
        with self.assertRaises(Redirect):
            self.document.view_image_or_file()


class HttpRequestTest(BaseUnitTest):

    file_data = 'hello world'

    def setUp(self):
        from Products.Reportek.Document import Document

        self._cleanup_temp_reposit = create_temp_reposit()

        self.zodb = MockDatabase()
        self.doc = Document('testdoc', "Document for Test")
        upload_file = FileUploadMock('file.txt', self.file_data)
        self.doc.data_file._toCompress = 'no'
        with patch.object(self.doc, 'getWorkitemsActiveForMe',
                          Mock(return_value=[]), create=True):
            self.doc.manage_file_upload(upload_file)
        self.zodb.root['root_ob'] = self.doc
        transaction.commit()

    def tearDown(self):
        self.zodb.cleanup()
        self._cleanup_temp_reposit()

    def test_head_headers(self):
        from webdav.common import rfc1123_date
        mtime = self.doc.data_file.mtime

        resp = publish_view(self.doc, {'REQUEST_METHOD': 'HEAD'})

        self.assertEqual(resp.getHeader('Content-Length'),
                         str(len(self.file_data)))
        self.assertEqual(resp.getHeader('Content-Type'), 'text/plain')
        self.assertEqual(resp.getHeader('Last-Modified'), rfc1123_date(mtime))

    def test_get_headers(self):
        from webdav.common import rfc1123_date
        mtime = self.doc.data_file.mtime

        resp = publish_view(self.doc)

        self.assertEqual(resp.getHeader('Content-Length'),
                         str(len(self.file_data)))
        self.assertEqual(resp.getHeader('Content-Type'), 'text/plain')
        self.assertEqual(resp.getHeader('Last-Modified'), rfc1123_date(mtime))

    def test_get_file_not_modified_returns_304(self):
        from webdav.common import rfc1123_date
        mtime = self.doc.data_file.mtime

        resp = publish_view(self.doc, {
            'HTTP_IF_MODIFIED_SINCE': rfc1123_date(mtime),
        })

        self.assertEqual(resp.status, 304)
        self.assertEqual(resp.getHeader('Last-Modified'), rfc1123_date(mtime))

    def test_get_file_modified_returns_200(self):
        from webdav.common import rfc1123_date
        mtime = self.doc.data_file.mtime

        resp = publish_view(self.doc, {
            'HTTP_IF_MODIFIED_SINCE': rfc1123_date(mtime - 50),
        })

        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getHeader('Last-Modified'), rfc1123_date(mtime))

    def test_get_missing_file(self):
        from Products.Reportek.Document import StorageError
        break_document_data_file(self.doc)

        self.assertRaises(StorageError, publish_view, self.doc)

    def test_get_icon_from_specialized_view(self):
        out = StringIO()
        resp = publish_view(self.doc, {
            'PATH_INFO': '/testdoc/icon_gif',
            '_stdout': out,
        })
        body = out.getvalue().split('\r\n\r\n', 1)[1]
        self.assertEqual(body[:6], 'GIF89a')
        self.assertEqual(resp.getHeader('Content-Type'), 'image/gif')

    def test_get_icon_from_index_view(self):
        out = StringIO()
        resp = publish_view(self.doc, {
            'QUERY_STRING': 'icon=1',
            '_stdout': out,
        })
        body = out.getvalue().split('\r\n\r\n', 1)[1]
        self.assertEqual(body[:6], 'GIF89a')
        self.assertEqual(resp.getHeader('Content-Type'), 'image/gif')
