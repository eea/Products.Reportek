import os
import unittest
from StringIO import StringIO
import zipfile
from mock import Mock, patch
from utils import (create_fake_root, makerequest, create_temp_reposit,
                   create_upload_file)


def create_mock_request():
    request = Mock()
    request.physicalPathToVirtualPath = lambda x: x
    request.physicalPathToURL = lambda x: x
    response = request.RESPONSE
    response._data = StringIO()
    response.write = response._data.write
    request._headers = {}
    request.get_header = request._headers.get
    return request


def setUpModule(self):
    from Products.Reportek import Document; self.Document = Document
    from Products.Reportek import Envelope; self.Envelope = Envelope
    self._cleanup_temp_reposit = create_temp_reposit()


def tearDownModule(self):
    self._cleanup_temp_reposit()


def create_envelope(parent, id='envelope'):
    process = Mock()
    e = Envelope.Envelope(process, '', '', '', '', '', '', '', '')
    e.id = id
    parent._setObject(id, e)
    e.dataflow_uris = []
    return parent[id]


def create_document_with_data(data):
    doc = Document.Document('testdoc', "Document for Test")
    doc.getWorkitemsActiveForMe = Mock(return_value=[])
    doc.manage_file_upload(create_upload_file(data))
    return doc


class FileStorageTest(unittest.TestCase):

    def test_upload(self):
        data = 'hello world, file for test!'

        doc = Document.Document('testdoc', "Document for Test")
        doc.getWorkitemsActiveForMe = Mock(return_value=[])
        doc.manage_file_upload(create_upload_file(data))

        request = create_mock_request()
        doc.index_html(request, request.RESPONSE)
        self.assertEqual(request.RESPONSE._data.getvalue(), data)

    def test_upload_during_create(self):
        data = 'hello world, file for test!'

        root = create_fake_root()
        root.getWorkitemsActiveForMe = Mock(return_value=[])
        root.REQUEST = create_mock_request()
        root.REQUEST.physicalPathToVirtualPath = lambda x: x

        doc_id = Document.manage_addDocument(root, file=create_upload_file(data))
        self.assertEqual(doc_id, 'testfile.txt')
        doc = root[doc_id]

        request = create_mock_request()
        doc.index_html(request, request.RESPONSE)
        self.assertEqual(request.RESPONSE._data.getvalue(), data)

    def test_get_zip_info(self):
        root = create_fake_root()
        root.REQUEST = create_mock_request()
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

    def test_read_file_data_error(self):
        from Products.Reportek.Document import StorageError
        data = 'hello world, file for test!'
        doc = create_document_with_data(data)
        os.unlink(doc.physicalpath())
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

    def test_get_file_metadata(self):
        data = 'hello world, file for test!'
        doc = create_document_with_data(data)
        file_path = doc.physicalpath()
        self.assertEqual(doc.data_file.mtime, os.path.getmtime(file_path))
        self.assertEqual(doc.data_file.size, len(data))

    def test_get_file_metadata_error(self):
        from Products.Reportek.Document import StorageError
        data = 'hello world, file for test!'
        doc = create_document_with_data(data)
        file_path = doc.physicalpath()
        os.unlink(file_path)
        self.assertRaises(StorageError, lambda: doc.data_file.mtime)
        self.assertRaises(StorageError, lambda: doc.data_file.size)


def download_envelope_zip(envelope):
    """ call Envelope.envelope_zip using patched security managers """
    envelope_patch = patch('Products.Reportek.Envelope.getSecurityManager')
    zip_patch = patch('Products.Reportek.zip_content.getSecurityManager')
    with envelope_patch as envelope_get_security:
        with zip_patch as zip_get_security:
            checkPermission = Mock(return_value=True)
            envelope_get_security.return_value = Mock(return_value=checkPermission)
            zip_get_security.return_value = Mock(return_value=checkPermission)
            REQUEST = envelope.REQUEST
            envelope.envelope_zip(REQUEST, REQUEST.RESPONSE)


class ZipDownloadTest(unittest.TestCase):

    def setUp(self):
        self._plain_root = self.root = create_fake_root()
        self.root.getWorkitemsActiveForMe = Mock(return_value=[])
        self.mock_request()
        self.envelope = create_envelope(self.root)

    def mock_request(self):
        request = create_mock_request()
        self.root = makerequest(self._plain_root, StringIO())
        request = self.root.REQUEST
        request.AUTHENTICATED_USER = Mock()
        response = request.RESPONSE
        response._data = StringIO()
        response.write = response._data.write
        return request

    def download_zip(self, envelope):
        envelope.REQUEST = self.mock_request()
        download_envelope_zip(envelope)
        data = envelope.REQUEST.RESPONSE._data
        data.seek(0)
        return zipfile.ZipFile(data)

    def test_one_document(self):
        data = 'hello world, file for test!'
        file_1 = create_upload_file(data)
        doc_id = Document.manage_addDocument(self.envelope, file=file_1)
        doc = self.envelope[doc_id]
        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('testfile.txt'), data)

    @patch('Products.Reportek.Envelope.ZIP_CACHE_THRESHOLD', -1)
    @patch('Products.Reportek.Envelope.ZipFile')
    def test_cache_hit_on_2nd_download(self, mock_ZipFile):
        import zipfile
        mock_ZipFile.side_effect = zipfile.ZipFile

        file_1 = create_upload_file('data one')
        doc_id = Document.manage_addDocument(self.envelope, file=file_1)
        doc = self.envelope[doc_id]
        self.envelope.release_envelope()

        zip_download_1 = self.download_zip(self.envelope)
        self.assertEqual(zip_download_1.read('testfile.txt'), 'data one')
        self.assertEqual(mock_ZipFile.call_count, 1)

        zip_download_2 = self.download_zip(self.envelope)
        self.assertEqual(zip_download_2.read('testfile.txt'), 'data one')
        self.assertEqual(mock_ZipFile.call_count, 1)

    @patch('Products.Reportek.Envelope.ZIP_CACHE_THRESHOLD', -1)
    def test_cache_invalidation_on_release(self):
        # zip cache is invalidated when the envelope is released (in case the
        # envelope had previously been released, unreleased and modified).

        file_1 = create_upload_file('data one')
        doc_id = Document.manage_addDocument(self.envelope, file=file_1)
        doc = self.envelope[doc_id]
        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('testfile.txt'), 'data one')

        self.envelope.unrelease_envelope()
        doc.manage_file_upload(create_upload_file('data two'))
        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('testfile.txt'), 'data two')

    @patch('Products.Reportek.Envelope.ZIP_CACHE_THRESHOLD', -1)
    def test_cache_invalidation_on_feedback(self):
        self.root.getEngine = Mock()

        file_1 = create_upload_file('data one')
        doc_id = Document.manage_addDocument(self.envelope, file=file_1)
        doc = self.envelope[doc_id]
        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)

        self.envelope.manage_addFeedback(title="good work")

        zip_download = self.download_zip(self.envelope)
        self.assertTrue("good work" in zip_download.read('feedbacks.html'))

    def test_feedback_content(self):
        self.root.getEngine = Mock()
        self.envelope.manage_addFeedback('feedback', title="good work")
        feedback = self.envelope['feedback']

        data = 'asdfqwer'
        feedback.manage_uploadFeedback(create_upload_file(data, 'opinion.txt'))

        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('opinion.txt'), data)

    def test_large_feedback_content(self):
        self.root.getEngine = Mock()
        self.envelope.manage_addFeedback('feedback', title="good work")
        feedback = self.envelope['feedback']

        data = ('asdfqwer1234567 ' * 64) * 1024 # 1MB
        feedback.manage_uploadFeedback(create_upload_file(data, 'opinion.txt'))

        self.envelope.release_envelope()

        zip_download = self.download_zip(self.envelope)
        self.assertEqual(zip_download.read('opinion.txt'), data)

    def test_missing_document_datafile(self):
        file_1 = create_upload_file('asdf')
        doc_id = Document.manage_addDocument(self.envelope, file=file_1)
        doc = self.envelope[doc_id]
        self.envelope.release_envelope()
        os.unlink(doc.physicalpath())

        self.assertRaises(ValueError, download_envelope_zip, self.envelope)
