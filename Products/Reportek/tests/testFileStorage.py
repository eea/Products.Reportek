import time
import unittest
from StringIO import StringIO
import zipfile
from mock import Mock, patch, call
import transaction
from utils import (create_fake_root, makerequest,
                   create_upload_file, create_envelope,
                   MockDatabase, break_document_data_file)
from Products.Reportek import constants
from Products.Reportek.Converters import Converters
from Products.Reportek import Document
from Products.Reportek import blob
from common import BaseTest, ConfigureReportek


def create_document_with_data(data, compression='no'):
    doc = Document.Document('testdoc', "Document for Test")
    doc.data_file._toCompress = compression
    with patch.object(doc, 'getWorkitemsActiveForMe',
                      Mock(return_value=[]), create=True):
        doc.manage_file_upload(create_upload_file(data))
    return doc


def doc_data(doc):
    with doc.data_file.open() as data_file_handle:
        return data_file_handle.read()


class FileStorageTest(BaseTest):

    def test_manage_file_upload(self):
        data = 'hello world, file for test!'
        doc = Document.Document('testdoc', "Document for Test")
        doc.getWorkitemsActiveForMe = Mock(return_value=[])
        doc.manage_file_upload(create_upload_file(data))
        self.assertEqual(doc_data(doc), data)

    def test_manage_file_upload_as_string(self):
        data = 'hello world, file for test!'
        doc = Document.Document('testdoc', "Document for Test")
        doc.getWorkitemsActiveForMe = Mock(return_value=[])
        doc.manage_file_upload(data)
        self.assertEqual(doc_data(doc), data)

    def test_upload_new_version(self):
        data_1 = 'the data, version one'
        data_2 = 'the data, version two'
        doc = Document.Document('testdoc', "Document for Test")
        doc.getWorkitemsActiveForMe = Mock(return_value=[])
        doc.manage_file_upload(data_1)
        doc.manage_file_upload(data_2)
        self.assertEqual(doc_data(doc), data_2)

    def test_upload_during_create(self):
        data = 'hello world, file for test!'

        root = create_fake_root()
        root.getWorkitemsActiveForMe = Mock(return_value=[])
        root.REQUEST = BaseTest.create_mock_request()
        root.REQUEST.physicalPathToVirtualPath = lambda x: x

        doc_id = Document.manage_addDocument(
            root, file=create_upload_file(data))
        self.assertEqual(doc_id, 'testfile.txt')
        doc = root[doc_id]

        request = BaseTest.create_mock_request()
        request.RESPONSE.setHeader = Mock()
        doc.index_html(request, request.RESPONSE)
        self.assertEqual(request.RESPONSE._data.getvalue(), data)
        self.assertNotIn(call('content-encoding', 'gzip'),
                         request.RESPONSE.setHeader.call_args_list)

    def test_get_AE_gzip(self):
        data = 'hello world, file for test!'

        root = create_fake_root()
        root.getWorkitemsActiveForMe = Mock(return_value=[])
        root.REQUEST = BaseTest.create_mock_request()
        root.REQUEST.physicalPathToVirtualPath = lambda x: x

        doc_id = Document.manage_addDocument(
            root, file=create_upload_file(data))
        self.assertEqual(doc_id, 'testfile.txt')
        doc = root[doc_id]
        compressed_size = doc.compressed_size()[0]

        request = BaseTest.create_mock_request()
        request.getHeader = Mock(return_value='gzip,bla')
        request.RESPONSE.setHeader = Mock()
        doc.index_html(request, request.RESPONSE)
        self.assertEqual(
            len(request.RESPONSE._data.getvalue()), compressed_size)
        self.assertTrue(request.RESPONSE.setHeader.called)
        self.assertIn(call('content-encoding', 'gzip'),
                      request.RESPONSE.setHeader.call_args_list)

    def test_get_zip_info(self):
        root = create_fake_root()
        root.REQUEST = BaseTest.create_mock_request()
        envelope = create_envelope(root)

        zip_data = StringIO()
        mock_zip = zipfile.ZipFile(zip_data, 'w')
        mock_zip.writestr('f1.txt', 'hello one')
        mock_zip.writestr('f2.txt', 'hello two file')
        mock_zip.close()

        upload_file = create_upload_file(zip_data.getvalue(), 'f.zip')

        doc_id = Document.manage_addDocument(envelope, file=upload_file)
        doc = envelope[doc_id]

        self.assertEqual(envelope.getZipInfo(doc), ['f1.txt', 'f2.txt'])

    def test_get_size(self):
        # rawsize and get_size are used in some old dtml
        data = 'hello world, file for test!'
        doc = create_document_with_data(data)
        self.assertEqual(doc.get_size(), len(data))
        self.assertEqual(doc.rawsize(), len(data))

    def test_compress_auto(self):
        data = 'hello world, file for test!'
        doc = create_document_with_data(data, compression='auto')
        # rawsize must be the uncompressed size.
        self.assertEqual(doc.rawsize(), len(data))
        self.assertTrue(doc.is_compressed())
        compressed_size = doc.compressed_size()[0]
        self.assertTrue(compressed_size > 0)
        # being such a small file the compressed version will be bigger. don't compare sizes.
        self.assertTrue(compressed_size != doc.rawsize())
        # test fetching the data back
        read_data = doc.data_file.open('rb').read()
        self.assertTrue(read_data == data)

    def test_compress_auto_not(self):
        from Products.Reportek.blob import FileContainer
        data = 'hello world, file for test!'
        FileContainer.COMPRESSIBLE_TYPES.discard('text/plain')
        doc = create_document_with_data(data, compression='auto')
        FileContainer.COMPRESSIBLE_TYPES.add('text/plain')

        # rawsize must be the uncompressed size.
        self.assertEqual(doc.rawsize(), len(data))
        self.assertFalse(doc.is_compressed())

    def test_compress_yes(self):
        from Products.Reportek.blob import FileContainer
        data = 'hello world, file for test!'
        FileContainer.COMPRESSIBLE_TYPES.discard('text/plain')
        doc = create_document_with_data(data, compression='yes')
        FileContainer.COMPRESSIBLE_TYPES.add('text/plain')

        # rawsize must be the uncompressed size.
        self.assertEqual(doc.rawsize(), len(data))
        self.assertTrue(doc.is_compressed())
        compressed_size = doc.compressed_size()[0]
        self.assertTrue(compressed_size > 0)
        self.assertTrue(compressed_size != doc.rawsize())

    def test_compress_keep_compressed(self):
        data = 'hello world, file for test!'
        doc = create_document_with_data(data, compression='auto')
        # rawsize must be the uncompressed size.
        self.assertEqual(doc.rawsize(), len(data))
        self.assertTrue(doc.is_compressed())
        compressed_size = doc.compressed_size()[0]
        self.assertTrue(compressed_size > 0)
        # being such a small file the compressed version will be bigger. don't compare sizes.
        self.assertTrue(compressed_size != doc.rawsize())
        # test fetching the data back
        read_data = doc.data_file.open('rb', skip_decompress=True).read()
        self.assertTrue(len(read_data) == compressed_size)


class DataFileApiTest(unittest.TestCase):

    def tearDown(self):
        transaction.abort()

    def test_read_uncommitted_file_data_error(self):
        from Products.Reportek.Document import StorageError
        data = 'hello world, file for test!'

        doc = create_document_with_data(data)

        break_document_data_file(doc)
        self.assertRaises(StorageError, doc.data_file.open)

    def test_read_committed_file_data_error(self):
        from Products.Reportek.Document import StorageError
        data = 'hello world, file for test!'

        zodb = MockDatabase()
        self.addCleanup(zodb.cleanup)

        doc = create_document_with_data(data)
        zodb.root['root_ob'] = doc
        transaction.commit()

        break_document_data_file(doc)
        self.assertRaises(StorageError, doc.data_file.open)

    def test_read_file_data(self):
        data = 'hello world, file for test!'
        doc = create_document_with_data(data)

        data_file = doc.data_file.open()
        self.assertEqual(data_file.read(), data)

        # rewind the file, see if we can still read data
        data_file.seek(0)
        self.assertEqual(data_file.read(), data)

        # read in chunks
        data_file.seek(0)
        self.assertEqual(data_file.read(1), data[0])

        data_file.close()

    def test_read_file_data_as_context_manager(self):
        data = 'hello world, file for test!'
        doc = create_document_with_data(data)

        data_file = doc.data_file.open()
        with data_file:
            self.assertEqual(data_file.read(), data)

        # I/O operation on closed file
        self.assertRaises(ValueError, data_file.read)

    def test_default_file_metadata(self):
        t0 = time.time()
        doc = Document.Document('testdoc', "Document for Test")
        t1 = time.time()
        self.assertTrue(int(t0) <= int(doc.data_file.mtime) <= int(t1))
        self.assertEqual(doc.data_file.size, 0)

    def test_get_file_metadata(self):
        data = 'hello world, file for test!'
        t0 = time.time()
        doc = create_document_with_data(data)
        t1 = time.time()
        self.assertTrue(int(t0) <= int(doc.data_file.mtime) <= int(t1))
        self.assertEqual(doc.data_file.size, len(data))

    def test_save_file_data(self):
        doc = create_document_with_data('some data')
        with doc.data_file.open('wb') as data_file_handle:
            data_file_handle.write("the new ")
            data_file_handle.write("file version")
        self.assertEqual(doc_data(doc), "the new file version")

    def test_open_with_invalid_argument(self):
        doc = create_document_with_data('some data')
        self.assertRaises(ValueError, doc.data_file.open, 'x')


def download_envelope_zip(envelope):
    """ call Envelope.envelope_zip using patched security managers """
    envelope_patch = patch('Products.Reportek.Envelope.getSecurityManager')
    zip_patch = patch('Products.Reportek.zip_content.getSecurityManager')
    with envelope_patch as envelope_get_security:
        with zip_patch as zip_get_security:
            checkPermission = Mock(return_value=True)
            envelope_get_security.return_value = Mock(
                return_value=checkPermission)
            zip_get_security.return_value = Mock(return_value=checkPermission)
            REQUEST = envelope.REQUEST
            return envelope.envelope_zip(REQUEST, REQUEST.RESPONSE)


class ZipDownloadTest(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(ZipDownloadTest, self).afterSetUp()
        self.createStandardDependencies()
        self.app._setObject('Converters', Converters())
        self.createStandardCollection()
        self.envelope = self.createStandardEnvelope()
        safe_html = Mock(convert=Mock(text='feedbacktext'))
        getattr(self.app.Converters,
                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)

    def mock_request(self):
        request = BaseTest.create_mock_request()
        self.root = makerequest(self._plain_root, StringIO())
        request = self.root.REQUEST
        request.AUTHENTICATED_USER = Mock()
        response = request.RESPONSE
        response._data = StringIO()
        response.write = response._data.write
        return request

    def download_zip(self, envelope):
        envelope.REQUEST = BaseTest.create_mock_request()
        rv = download_envelope_zip(envelope)
        return zipfile.ZipFile(rv)

    @patch('Products.Reportek.Envelope.transaction.commit')
    def test_one_document(self, mock_commit):
        data = 'hello world, file for test!'
        file_1 = create_upload_file(data)
        Document.manage_addDocument(self.envelope, file=file_1)
        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('testfile.txt'), data)

    @patch('Products.Reportek.Envelope.ZIP_CACHE_THRESHOLD', -1)
    @patch('Products.Reportek.Envelope.transaction.commit')
    @patch('Products.Reportek.Envelope.ZipFile')
    def test_cache_hit_on_2nd_download(self, mock_ZipFile, mock_commit):
        import zipstream
        mock_ZipFile.side_effect = zipstream.ZipFile

        file_1 = create_upload_file('data one')
        Document.manage_addDocument(self.envelope, file=file_1)

        self.envelope.release_envelope()

        zip_download_1 = self.download_zip(self.envelope)
        self.assertEqual(zip_download_1.read('testfile.txt'), 'data one')
        self.assertEqual(mock_ZipFile.call_count, 1)

        zip_download_2 = self.download_zip(self.envelope)
        self.assertEqual(zip_download_2.read('testfile.txt'), 'data one')
        self.assertEqual(mock_ZipFile.call_count, 1)

    @patch('Products.Reportek.Envelope.ZIP_CACHE_THRESHOLD', -1)
    @patch('Products.Reportek.Envelope.transaction.commit')
    def test_cache_invalidation_on_release(self, mock_commit):
        # zip cache is invalidated when the envelope is released (in case the
        # envelope had previously been released, unreleased and modified).

        file_1 = create_upload_file('data one')
        doc_id = Document.manage_addDocument(self.envelope, file=file_1)
        doc = self.envelope[doc_id]
        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('testfile.txt'), 'data one')

        self.envelope.absolute_url = Mock(return_value='url')
        self.envelope.unrelease_envelope()
        doc.manage_file_upload(create_upload_file('data two'))
        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('testfile.txt'), 'data two')

    @patch('Products.Reportek.Envelope.ZIP_CACHE_THRESHOLD', -1)
    @patch('Products.Reportek.Envelope.transaction.commit')
    def test_cache_invalidation_on_feedback(self, mock_commit):
        self.root.getEngine = Mock()

        file_1 = create_upload_file('data one')
        Document.manage_addDocument(self.envelope, file=file_1)
        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)

        self.envelope.manage_addFeedback(title="good work")

        zip_download = self.download_zip(self.envelope)
        self.assertTrue("good work" in zip_download.read('feedbacks.html'))

    @patch('Products.Reportek.Envelope.transaction.commit')
    def test_feedback_content(self, mock_commit):
        self.root.getEngine = Mock()
        self.envelope.manage_addFeedback('feedback', title="good work")
        feedback = self.envelope['feedback']

        data = 'asdfqwer'
        feedback.manage_uploadFeedback(create_upload_file(data, 'opinion.txt'))

        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('opinion.txt'), data)

    @patch('Products.Reportek.Envelope.transaction.commit')
    def test_large_feedback_content(self, mock_commit):
        self.root.getEngine = Mock()
        self.envelope.manage_addFeedback('feedback', title="good work")
        feedback = self.envelope['feedback']

        data = ('asdfqwer1234567 ' * 64) * 1024  # 1MB
        feedback.manage_uploadFeedback(create_upload_file(data, 'opinion.txt'))

        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('opinion.txt'), data)

    @patch('Products.Reportek.Envelope.transaction.commit')
    def test_missing_document_datafile(self, mock_commit):
        file_1 = create_upload_file('asdf')
        doc_id = Document.manage_addDocument(self.envelope, file=file_1)
        doc = self.envelope[doc_id]
        self.envelope.release_envelope()
        break_document_data_file(doc)

        self.assertRaises(ValueError, download_envelope_zip, self.envelope)

    @patch('Products.Reportek.Envelope.transaction.commit')
    def test_unauthorized(self, mock_commit):
        from AccessControl import Unauthorized
        self.envelope.release_envelope()
        self.envelope.canViewContent = Mock(return_value=False)
        self.assertRaises(Unauthorized, download_envelope_zip, self.envelope)

    def test_zip_name_encoding(self):
        from Products.Reportek.zip_content import encode_zip_name
        data = [('a', 'x', 'a-x'),
                ('a/b/ccc.dd', 'x', 'a%2Fb%2Fccc.dd-x'),
                ('ab%cd', 'x', 'ab%25cd-x'),
                ('a', 'yz', 'a-yz')]

        for orig_path, flags, expected in data:
            self.assertEqual(encode_zip_name(orig_path, flags), expected)


class FileContainerTest(unittest.TestCase):

    def test_default_attributes(self):
        t0 = int(time.time())
        ob = blob.FileContainer()
        t1 = int(time.time())
        self.assertEqual(ob.size, 0)
        self.assertEqual(ob.content_type, 'application/octet-stream')
        self.assertTrue(t0 <= int(ob.mtime) <= t1)

    def test_default_content(self):
        ob = blob.FileContainer()
        with ob.open() as f:
            self.assertEqual(f.read(), '')

    def test_compression_ok(self):
        blob.FileContainer(compress='auto')


class OfsBlobFileTest(unittest.TestCase):

    def test_create_file(self):
        from OFS.Folder import Folder
        from Products.Reportek.blob import add_OfsBlobFile

        folder = Folder()
        myfile = add_OfsBlobFile(folder, 'myfile')

        self.assertEqual(myfile.getId(), 'myfile')
        self.assertEqual(myfile.__name__, 'myfile')

        self.assertEqual(list(folder), ['myfile'])
        self.assertEqual(folder.values(), [myfile])
        self.assertEqual(myfile.meta_type, "File (Blob)")

    def test_save_and_read_content(self):
        from Products.Reportek.blob import OfsBlobFile
        content = 'hello blobby world!\n'
        myfile = OfsBlobFile()

        with myfile.data_file.open('wb') as f:
            f.write(content)

        with myfile.data_file.open() as f:
            self.assertEqual(f.read(), content)

    def test_save_content_at_creation(self):
        from OFS.Folder import Folder
        from Products.Reportek.blob import add_OfsBlobFile
        content = 'hello blobby world!\n'

        folder = Folder()
        myfile = add_OfsBlobFile(folder, 'myfile', StringIO(content))

        with myfile.data_file.open() as f:
            self.assertEqual(f.read(), content)

    def test_download_content(self):
        from utils import publish_view
        from Products.Reportek.blob import OfsBlobFile

        content = 'hello blobby world!\n'
        myfile = OfsBlobFile('myfile')

        with myfile.data_file.open('wb') as f:
            f.write(content)
        myfile.data_file.content_type = 'image/jpeg'

        out = StringIO()
        publish_view(myfile, {'_stdout': out})
        (headers_str, body) = out.getvalue().split('\r\n\r\n', 1)
        headers = {}
        for line in headers_str.splitlines():
            k, v = line.split(':', 1)
            headers[k.strip()] = v.strip()
        self.assertEqual(body, content)
        self.assertEqual(headers['Content-Type'], 'image/jpeg')

    def test_update_content(self):
        from Products.Reportek.blob import OfsBlobFile

        content = 'hello blobby world!\n'
        myfile = OfsBlobFile('myfile')

        upload_file = StringIO(content)
        upload_file.headers = {'Content-Type': 'text/plain'}
        myfile.manage_edit(Mock(form={'file': upload_file}), Mock())

        with myfile.data_file.open() as f:
            self.assertEqual(f.read(), content)
        self.assertEqual(myfile.data_file.content_type, 'text/plain')

    def test_update_content_type(self):
        from Products.Reportek.blob import OfsBlobFile

        myfile = OfsBlobFile('myfile')

        myfile.manage_edit(Mock(form={'content_type': 'image/png'}), Mock())

        self.assertEqual(myfile.data_file.content_type, 'image/png')

    # TODO test download content type header
