import unittest
from datetime import datetime
from mock import Mock, patch
from utils import create_fake_root, create_upload_file
from utils import create_envelope, add_document
from Products.Reportek.QAScript import QAScript


def create_qa_repository(parent, id='qa_repository'):
    from Products.Reportek.QARepository import QARepository
    ob = QARepository()
    parent._setObject(ob.id, ob)
    return parent[ob.id]


class QAScriptTest(unittest.TestCase):

    def setUp(self):
        self.doc_content = 'test content for our document'
        self.root = create_fake_root()
        self.envelope = create_envelope(self.root)
        self.envelope.dataflow_uris = ['dataflow/uri']
        self.doc = add_document(
            self.envelope, create_upload_file(self.doc_content, 'foo.txt'))
        self.qa_repository = create_qa_repository(self.root)
        schema_qascript = QAScript(
            id='schema_qascript',
            title=None,
            description=None,
            xml_schema='xml.schema',
            workflow=None,
            content_type_in='application/msaccess',
            content_type_out='text/plain',
            script_url='url',
            max_size='10',
            qa_extraparams=None
        ).__of__(self.qa_repository)
        mdb_workflow_qascript = QAScript(
            id='mdb_workflow_qascript',
            title=None,
            description=None,
            xml_schema='',
            workflow='dataflow/uri',
            content_type_in='application/msaccess',
            content_type_out='text/plain',
            script_url='url',
            max_size='10',
            qa_extraparams=None
        ).__of__(self.qa_repository)
        doc_workflow_qascript = QAScript(
            id='doc_workflow_qascript',
            title=None,
            description=None,
            xml_schema='',
            workflow='dataflow/uri',
            content_type_in='application/msword',
            content_type_out='text/plain',
            script_url='url',
            max_size='10',
            qa_extraparams=None
        ).__of__(self.qa_repository)
        stalling_qascript = QAScript(
            id='stalling_qascript',
            title=None,
            description=None,
            xml_schema='',
            workflow=None,
            content_type_in='application/msaccess',
            content_type_out='text/plain',
            script_url='url',
            max_size='10',
            qa_extraparams=None
        ).__of__(self.qa_repository)
        schema_qascript.bobobase_modification_time = Mock(
            return_value=datetime.now())
        mdb_workflow_qascript.bobobase_modification_time = Mock(
            return_value=datetime.now())
        doc_workflow_qascript.bobobase_modification_time = Mock(
            return_value=datetime.now())
        stalling_qascript.bobobase_modification_time = Mock(
            return_value=datetime.now())

        self.qa_repository._setObject('schema_qascript', schema_qascript)
        self.qa_repository._setObject(
            'mdb_workflow_qascript', mdb_workflow_qascript)
        self.qa_repository._setObject(
            'doc_workflow_qascript', doc_workflow_qascript)
        self.qa_repository._setObject('stalling_qascript', stalling_qascript)

    def test_invoke_local_script(self):
        self.qa_repository.myscript = Mock(
            qa_extraparams=[], script_url='ls -l %s')
        self.qa_repository.myscript.content_type_out = 'text/plain'
        from StringIO import StringIO
        mock_file = StringIO(self.doc_content)
        mock_file.name = 'test_file'
        mock_file.__exit__ = Mock()
        mock_file.__enter__ = Mock()
        file_data = Mock(data_file=Mock(open=Mock(return_value=mock_file)))
        self.qa_repository.unrestrictedTraverse = Mock(return_value=file_data)
        with patch('Products.Reportek.QARepository.RepUtils',
                   Mock(temporary_named_copy=Mock(return_value=mock_file))):
            with patch.object(self.qa_repository, 'REQUEST', create=True) as\
                 request:
                request.SERVER_URL = 'http://example.com'
                file_url = 'http://example.com/envelope/foo.txt'
                with patch('Products.Reportek.QARepository.subprocess') as\
                     mock_sp:
                    mock_proc = Mock(stdout=StringIO('test output'))
                    mock_sp.Popen.return_value = mock_proc
                    ret = self.qa_repository._runQAScript(
                        file_url, 'loc_myscript')
                (file_id, [content_type, result]) = ret
                self.assertEqual(len(mock_sp.Popen.mock_calls), 1)

        self.assertEqual('test output', result.data)
        self.assertEqual(
            ['ls', '-l', 'test_file'],
            mock_sp.Popen.mock_calls[0][1][0])

        self.assertEqual(
            False,
            mock_sp.Popen.mock_calls[0][2]['shell'])

    def test_local_script_attributes_initialisation(self):
        qascript = QAScript(
            id='myscript',
            title=None,
            description=None,
            xml_schema=None,
            workflow='dataflow_uri',
            content_type_in='application/msaccess',
            content_type_out='text/plain',
            script_url='url',
            max_size=99,
            qa_extraparams=None
        ).__of__(self.qa_repository)
        self.qa_repository._setObject('myscript', qascript)
        self.assertEqual('dataflow_uri', qascript.workflow)
        self.assertEqual(99, qascript.max_size)
        self.assertEqual(
            'application/msaccess',
            qascript.content_type_in)

    def test_local_script_found_by_workflow(self):
        qa_repository = self.qa_repository
        local_scripts = qa_repository._get_local_qa_scripts(
            dataflow_uris=self.envelope.dataflow_uris)
        self.assertEqual(
            [qa_repository.mdb_workflow_qascript,
             qa_repository.doc_workflow_qascript],
            local_scripts)

        # assert prior workflow attribute behaviour
        local_scripts = qa_repository._get_local_qa_scripts()
        self.assertEqual(4, len(local_scripts))

        mock_dm_container = Mock(getSchemasForDataflows=Mock(return_value=[]))
        qa_repository.getDataflowMappingsContainer = Mock(
            return_value=mock_dm_container)

        self.doc.content_type = 'application/msaccess'
        result = qa_repository.canRunQAOnFiles([self.doc])

        self.assertEqual(('foo.txt', 'loc_mdb_workflow_qascript'),
                         (result.keys()[0], result.values()[0][0][0])
                         )

    def test_scripts_are_found_by_schema(self):
        qa_repository = self.qa_repository

        # assert scripts are found by schema
        local_scripts = qa_repository._get_local_qa_scripts(
            p_schema='xml.schema')
        self.assertEqual([qa_repository.schema_qascript], local_scripts)

    def test_scripts_are_found_by_workflow(self):
        qa_repository = self.qa_repository

        # assert scripts are found by workflow
        local_scripts = qa_repository._get_local_qa_scripts(
            dataflow_uris=['dataflow/uri'])
        self.assertEqual(
            [qa_repository.mdb_workflow_qascript,
             qa_repository.doc_workflow_qascript],
            local_scripts)

    def test_scripts_are_found_by_schema_or_workflow(self):
        qa_repository = self.qa_repository

        # assert scripts are found either by schema or workflow
        local_scripts = qa_repository._get_local_qa_scripts(
            p_schema='xml.schema', dataflow_uris=['dataflow/uri'])
        self.assertEqual(
            [qa_repository.schema_qascript,
             qa_repository.mdb_workflow_qascript,
             qa_repository.doc_workflow_qascript],
            local_scripts)

    def test_all_scripts_are_found(self):
        qa_repository = self.qa_repository

        # assert all scripts are found
        local_scripts = qa_repository._get_local_qa_scripts()
        self.assertEqual(
            [qa_repository.schema_qascript,
             qa_repository.mdb_workflow_qascript,
             qa_repository.doc_workflow_qascript,
             qa_repository.stalling_qascript],
            local_scripts)

    def test_workflow_scripts_are_filtered_by_content_type(self):
        qa_repository = self.qa_repository

        # assert filtered by workflow and content type
        local_scripts = qa_repository._get_local_qa_scripts(
            dataflow_uris=['dataflow/uri'],
            content_type_in='application/msaccess')
        self.assertEqual(
            [qa_repository.mdb_workflow_qascript],
            local_scripts)

        # assert filtered by workflow and content type
        local_scripts = qa_repository._get_local_qa_scripts(
            p_schema='xml.schema',
            dataflow_uris=[None],
            content_type_in='application/msaccess')
        self.assertEqual(
            [qa_repository.schema_qascript],
            local_scripts)

    def test_workflow_scripts_are_found_by_content_type(self):
        qa_repository = self.qa_repository

        # assert filtered by workflow and content type
        local_scripts = qa_repository._get_local_qa_scripts(
            content_type_in='application/msword')
        self.assertEqual(
            [qa_repository.doc_workflow_qascript],
            local_scripts)

    def test_workflow_scripts_are_filtered_by_doc_content_type(self):
        qa_repository = self.qa_repository

        # assert filtered by workflow and content type
        local_scripts = qa_repository._get_local_qa_scripts(
            dataflow_uris=['dataflow/uri'],
            content_type_in='application/msaccess')
        self.assertEqual(
            [qa_repository.mdb_workflow_qascript],
            local_scripts)

        # assert filtered by schema, workflow and content type
        local_scripts = qa_repository._get_local_qa_scripts(
            p_schema='xml.schema',
            dataflow_uris=[None],
            content_type_in='application/msaccess')
        self.assertEqual(
            [qa_repository.schema_qascript],
            local_scripts)

        mock_dm_container = Mock(getSchemasForDataflows=Mock(return_value=[]))
        qa_repository.getDataflowMappingsContainer = Mock(
            return_value=mock_dm_container)

        self.doc.content_type = 'application/msword'
        result = qa_repository.canRunQAOnFiles([self.doc])
        self.assertEqual(
            map(lambda item: item[0], result['foo.txt']),
            ['loc_doc_workflow_qascript']
        )
