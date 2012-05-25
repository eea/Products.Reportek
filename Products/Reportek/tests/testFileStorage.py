import unittest
from StringIO import StringIO
from mock import Mock
from utils import create_fake_root


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


def create_upload_file(data='', filename='testfile.txt'):
    f = StringIO(data)
    f.filename = filename
    return f


def setUpModule():
    global Document
    from Products.Reportek import Document


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
