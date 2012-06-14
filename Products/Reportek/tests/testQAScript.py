import unittest
from StringIO import StringIO
from mock import Mock, patch, call
from utils import create_fake_root, create_upload_file
from utils import create_envelope, add_document


def create_qa_repository(parent, id='qa_repository'):
    from Products.Reportek.QARepository import QARepository
    ob = QARepository()
    parent._setObject(ob.id, ob)
    return parent[ob.id]


class QAScriptTest(unittest.TestCase):

    def test_invoke_local_script(self):
        doc_content = 'test content for our document'
        root = create_fake_root()
        envelope = create_envelope(root)
        doc = add_document(envelope, create_upload_file(doc_content, 'foo.txt'))
        qa_repository = create_qa_repository(root)
        qa_repository.myscript = Mock(qa_extraparams=[], script_url='ls -l %s')

        file_data = []
        mock_popen_output = 'the script output'
        def mock_popen(command):
            # the qa script should have access to a file containing the data
            self.assertTrue(command.startswith('ls -l '))
            file_path = command[6:]
            with open(file_path, 'rb') as f:
                data = f.read()
            file_data.append(data)
            return StringIO(mock_popen_output)

        with patch.object(qa_repository, 'REQUEST', create=True) as request:
            request.SERVER_URL = 'http://example.com'
            file_url = 'http://example.com/envelope/foo.txt'
            with patch('Products.Reportek.QARepository.os') as mock_os:
                mock_os.popen.side_effect = mock_popen
                ret = qa_repository._runQAScript(file_url, 'loc_myscript')
            (file_id, [content_type, result]) = ret
            self.assertEqual(len(mock_os.popen.mock_calls), 1)

        self.assertEqual(result.data, mock_popen_output)
        self.assertEqual(file_data, [doc_content])
