import unittest
import mimetypes
from StringIO import StringIO
from mock import Mock, patch, call
from utils import create_fake_root, create_upload_file
from utils import create_envelope, add_document
from Products.Reportek.QAScript import QAScript


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

    def test_local_script_attributes_initialisation(self):
        doc_content = 'test content for our document'
        root = create_fake_root()
        envelope = create_envelope(root)
        envelope.dataflow_uris = ['dataflow_uri']
        qa_repository = create_qa_repository(root)
        qascript = QAScript(
            id = 'myscript',
            title = None,
            description = None,
            xml_schema = None,
            workflow = 'dataflow_uri',
            content_type_in = mimetypes.types_map['.mdb'],
            content_type_out = 'text/plain',
            script_url = 'url',
            qa_extraparams = None
        ).__of__(qa_repository)
        qa_repository._setObject('myscript', qascript)
        self.assertEqual('dataflow_uri', qascript.workflow)
        self.assertEqual(
            'application/msaccess',
            qascript.content_type_in)

    def test_local_script_found_by_workflow(self):
        doc_content = 'test content for our document'
        root = create_fake_root()
        envelope = create_envelope(root)
        envelope.dataflow_uris = ['dataflow_uri']
        doc = add_document(envelope, create_upload_file(doc_content, 'foo.txt'))
        qa_repository = create_qa_repository(root)
        from Products.Reportek.QAScript import QAScript
        qascript = QAScript(
            id = 'myscript',
            title = None,
            description = None,
            xml_schema = None,
            workflow = 'dataflow_uri',
            content_type_in = mimetypes.types_map['.mdb'],
            content_type_out = 'text/plain',
            script_url = 'url',
            qa_extraparams = None
        ).__of__(qa_repository)
        from datetime import datetime
        qascript.bobobase_modification_time = Mock(return_value=datetime.now())
        qa_repository._setObject('myscript', qascript)
        self.assertEqual('dataflow_uri', qascript.workflow)

        local_scripts = qa_repository._get_local_qa_scripts(dataflow_uris=envelope.dataflow_uris)
        self.assertEqual([qa_repository.myscript], local_scripts)

        # assert prior workflow attribute behaviour
        local_scripts = qa_repository._get_local_qa_scripts()
        self.assertEqual([qa_repository.myscript], local_scripts)
        mock_dm_container = Mock(getXMLSchemasForDataflows=Mock(return_value=[]))
        qa_repository.getDataflowMappingsContainer = Mock(return_value=mock_dm_container)
        result = qa_repository.canRunQAOnFiles([doc])
        self.assertEqual(('foo.txt', 'loc_myscript'),
            (result.keys()[0], result.values()[0][0][0])
        )

    def test_get_local_qa_scripts(self):
        doc_content = 'test content for our document'
        root = create_fake_root()
        envelope = create_envelope(root)
        envelope.dataflow_uris = ['dataflow_uri']
        doc = add_document(envelope, create_upload_file(doc_content, 'foo.txt'))
        qa_repository = create_qa_repository(root)
        from Products.Reportek.QAScript import QAScript
        schema_qascript = QAScript(
            id = 'schema_qascript',
            title = None,
            description = None,
            xml_schema = 'xml.schema',
            workflow = None,
            content_type_in = mimetypes.types_map['.mdb'],
            content_type_out = 'text/plain',
            script_url = 'url',
            qa_extraparams = None
        ).__of__(qa_repository)
        workflow_qascript = QAScript(
            id = 'workflow_qascript',
            title = None,
            description = None,
            xml_schema = '',
            workflow = 'dataflow/uri',
            content_type_in = mimetypes.types_map['.mdb'],
            content_type_out = 'text/plain',
            script_url = 'url',
            qa_extraparams = None
        ).__of__(qa_repository)
        stalling_qascript = QAScript(
            id = 'stalling_qascript',
            title = None,
            description = None,
            xml_schema = '',
            workflow = None,
            content_type_in = mimetypes.types_map['.mdb'],
            content_type_out = 'text/plain',
            script_url = 'url',
            qa_extraparams = None
        ).__of__(qa_repository)
        from datetime import datetime
        schema_qascript.bobobase_modification_time = Mock(return_value=datetime.now())
        workflow_qascript.bobobase_modification_time = Mock(return_value=datetime.now())
        qa_repository._setObject('schema_qascript', schema_qascript)
        qa_repository._setObject('workflow_qascript', workflow_qascript)
        qa_repository._setObject('stalling_qascript', stalling_qascript)

        #assert scripts are found by schema
        local_scripts = qa_repository._get_local_qa_scripts(p_schema='xml.schema')
        self.assertEqual([qa_repository.schema_qascript], local_scripts)

        #assert scripts are found by workflow
        local_scripts = qa_repository._get_local_qa_scripts(dataflow_uris=['dataflow/uri'])
        self.assertEqual([qa_repository.workflow_qascript], local_scripts)

        #assert scripts are found either by schema or workflow
        local_scripts = qa_repository._get_local_qa_scripts(
                p_schema='xml.schema', dataflow_uris=['dataflow/uri'])
        self.assertEqual([schema_qascript, workflow_qascript], local_scripts)

        #assert all scripts are found
        local_scripts = qa_repository._get_local_qa_scripts()
        self.assertEqual([schema_qascript, workflow_qascript, stalling_qascript], local_scripts)
