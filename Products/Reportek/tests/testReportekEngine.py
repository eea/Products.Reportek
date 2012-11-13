import unittest
from StringIO import StringIO
import zipfile
from mock import Mock, patch
from utils import (create_fake_root, create_temp_reposit, create_upload_file,
                  create_envelope, add_document, makerequest)
from Products.Reportek.ReportekEngine import ReportekEngine
from Products.Reportek.Envelope import Envelope
from Products.Reportek.Collection import Collection

def setUpModule(self):
    self._cleanup_temp_reposit = create_temp_reposit()

def tearDownModule(self):
    self._cleanup_temp_reposit()


def create_reportek_engine(parent):
    ob = ReportekEngine()
    parent._setObject(ob.id, ob)
    return parent[ob.id]

class _BaseTest(unittest.TestCase):

    def setUp(self):
        from Products.ZCatalog.ZCatalog import ZCatalog
        from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
        from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex
        from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
        from Products.PluginIndexes.PathIndex.PathIndex import PathIndex
        from Products.Reportek import create_reportek_indexes
        self.root = makerequest(create_fake_root())

        catalog = ZCatalog('Catalog', 'Default Catalog for Reportek')
        self.root._setObject('Catalog', catalog)
        self.root.Catalog.meta_types = [
            {'name': 'FieldIndex', 'instance': FieldIndex},
            {'name': 'KeywordIndex', 'instance': KeywordIndex},
            {'name': 'DateIndex', 'instance': DateIndex},
            {'name': 'PathIndex', 'instance': PathIndex},]
        create_reportek_indexes(self.root.Catalog)


class ReportekEngineTest(_BaseTest):

    def setUp(self):
        super(ReportekEngineTest, self).setUp()
        self.engine = create_reportek_engine(self.root)


    def test_searchfeedbacks_on_disk(self):
        try:
            dtml = ReportekEngine.searchfeedbacks
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsfeedbacks_on_disk(self):
        try:
            dtml = ReportekEngine.resultsfeedbacks
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_recent_uploads_on_disk(self):
        try:
            dtml = ReportekEngine.recent
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_searchdataflow_on_disk(self):
        try:
            dtml = ReportekEngine.searchdataflow
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsdataflow_on_disk(self):
        try:
            dtml = ReportekEngine.resultsdataflow
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_searchxml_on_disk(self):
        try:
            dtml = ReportekEngine.searchxml
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsxml_on_disk(self):
        try:
            dtml = ReportekEngine.resultsxml
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_countryreporters_on_disk(self):
        try:
            dtml = ReportekEngine.countryreporters
            dtml.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_getUniqueValuesFor(self):
        process = Mock()
        process.absolute_url = Mock(return_value='/ProcessURL')
        first_envelope = Envelope(process=process,
                            title='FirstEnvelope',
                            authUser='TestUser',
                            year=2012,
                            endyear=2013,
                            partofyear='January',
                            country='http://example.com/country/1',
                            locality='TestLocality',
                            descr='TestDescription')
        first_envelope.id = 'first_envelope'
        self.root._setObject(first_envelope.id, first_envelope)
        self.root[first_envelope.id].manage_changeEnvelope(dataflow_uris='http://example.com/dataflow/1')
        results = self.engine.getUniqueValuesFor('dataflow_uris')
        self.assertEqual(results, ('http://example.com/dataflow/1',))

    def test_assign_role_with_Assign_client(self):
        self.root._setObject( 'col', Collection('col',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root.col.getCountryCode = Mock(return_value = 'AT')
        kwargs = {
            'ccountries': ['at'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual(('Reporter',), self.root.col.get_local_roles_for_userid('testuser'))

    def test_assign_multiple_roles_with_Assign_client(self):
        self.root._setObject( 'col', Collection('col',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root.col.getCountryCode = Mock(return_value = 'AT')
        kwargs = {
            'ccountries': ['at'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        kwargs.update({'crole': 'Auditor'})
        self.engine.Assign_client(**kwargs)
        self.assertEqual(('Reporter', 'Auditor'), self.root.col.get_local_roles_for_userid('testuser'))

    def test_remove_role_with_Remove_client(self):
        self.root._setObject( 'col', Collection('col',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root.col.getCountryCode = Mock(return_value = 'AT')
        kwargs = {
            'ccountries': ['at'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        self.engine.Remove_client(**kwargs)
        self.assertEqual((), self.root.col.get_local_roles_for_userid('testuser'))


    def test_remove_specified_role_only_with_Remove_client(self):
        self.root._setObject( 'col', Collection('col',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root.col.getCountryCode = Mock(return_value = 'AT')
        kwargs = {
            'ccountries': ['at'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        kwargs.update({'crole': 'Auditor'})
        self.engine.Assign_client(**kwargs)
        kwargs.update({'crole': 'Reporter'})
        self.engine.Remove_client(**kwargs)
        self.assertEqual(('Auditor',), self.root.col.get_local_roles_for_userid('testuser'))


    def test_assign_role_to_multiple_collections(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root.col1.getCountryCode = Mock(return_value = 'AT')

        self.root._setObject( 'col2', Collection('col2',
            'EU, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/2',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root.col2.getCountryCode = Mock(return_value = 'AL')
        self.assertEqual((), self.root.col1.get_local_roles_for_userid('testuser'))
        self.assertEqual((), self.root.col2.get_local_roles_for_userid('testuser'))
        kwargs = {
            'ccountries': ['al', 'at'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual(('Reporter', ), self.root.col1.get_local_roles_for_userid('testuser'))
        self.assertEqual(('Reporter', ), self.root.col2.get_local_roles_for_userid('testuser'))


    def test_remove_role_from_multiple_collections(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root.col1.getCountryCode = Mock(return_value = 'AT')

        self.root._setObject( 'col2', Collection('col2',
            'EU, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/2',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        self.root.col2.getCountryCode = Mock(return_value = 'AL')
        kwargs = {
            'ccountries': ['al', 'at'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.engine.Assign_client(**kwargs)
        self.assertEqual(('Reporter', ), self.root.col1.get_local_roles_for_userid('testuser'))
        self.assertEqual(('Reporter', ), self.root.col2.get_local_roles_for_userid('testuser'))
        self.engine.Remove_client(**kwargs)
        self.assertEqual((), self.root.col1.get_local_roles_for_userid('testuser'))
        self.assertEqual((), self.root.col2.get_local_roles_for_userid('testuser'))

    def test_remove_not_existing_role(self):
        self.root._setObject( 'col1', Collection('col1',
            'EEA, requests', '', '', '', 'http://rod.eionet.eu.int/spatial/3',
            '', 'European Environment Agency',
            ['http://example.com/dataflow/1'], allow_collections=0,
            allow_envelopes=1))
        kwargs = {
            'ccountries': ['at'],
            'crole': 'Reporter',
            'cobligation': 'http://example.com/dataflow/1',
            'dns': ['testuser']
        }
        self.root.col1.getCountryCode = Mock(return_value = 'AT')
        self.engine.Remove_client(**kwargs)
        self.assertEqual((), self.root.col1.get_local_roles_for_userid('testuser'))



class SearchResultsTest(_BaseTest):

    def setUp(self):
        super(SearchResultsTest, self).setUp()
        from Products.Reportek.Envelope import Envelope
        self.engine = create_reportek_engine(self.root)
        process = Mock()
        process.absolute_url = Mock(return_value='/ProcessURL')
        first_envelope = Envelope(process=process,
                            title='FirstEnvelope',
                            authUser='TestUser',
                            year=2012,
                            endyear=2013,
                            partofyear='January',
                            country='http://example.com/country/1',
                            locality='TestLocality',
                            descr='TestDescription')
        first_envelope.id = 'first_envelope'
        self.root._setObject(first_envelope.id, first_envelope)
        self.root[first_envelope.id].manage_changeEnvelope(dataflow_uris='http://example.com/dataflow/1')
        self.root['first_envelope'].getEngine = Mock()
        self.root['first_envelope'] .manage_addFeedback('feedbackid', 'Title',
                                                       'Feedback text', '','WorkflowEngine/begin_end', 1)
        self.root['first_envelope'] .manage_addFeedback('feedback5', 'Title',
                                                       'Feedback text', '','WorkflowEngine/begin_end', 1)
        self.root['first_envelope'] .manage_addFeedback('feedback10', 'Title',
                                                       'Feedback text', '','WorkflowEngine/begin_end', 1)

        second_envelope = Envelope(process=process,
                            title='SecondEnvelope',
                            authUser='TestUser',
                            year=2012,
                            endyear=2013,
                            partofyear='June',
                            country='http://example.com/country/2',
                            locality='TestLocality',
                            descr='TestDescription')
        second_envelope.id = 'second_envelope'
        self.root._setObject(second_envelope.id, second_envelope)
        self.root[second_envelope.id].manage_changeEnvelope(dataflow_uris='http://example.com/dataflow/2')

    def test_returns_all(self):
        results = self.engine.getSearchResults()
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope,
                                self.root.first_envelope['feedbackid'],
                                self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10'],
                                self.root.second_envelope])

    def test_filter_by_meta_type(self):
        results = self.engine.getSearchResults(meta_type='Report Feedback')
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope['feedbackid'],
                                self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10']])

    def test_filter_by_dataflow_uris(self):
        results = self.engine.getSearchResults(dataflow_uris='http://example.com/dataflow/2')
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.second_envelope])

    def test_filter_by_country(self):
        results = self.engine.getSearchResults(country='http://example.com/country/1')
        res = [el.getObject() for el in results]
        self.assertEqual(res, [self.root.first_envelope,
                                self.root.first_envelope['feedbackid'],
                                self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10']])

    def test_filter_by_id(self):
        results = self.engine.getSearchResults(id={'range': 'min:max',
                                                   'query': ['feedback0','feedback9']})
        feedbacks = [el.getObject() for el in results]
        self.assertEqual(feedbacks, [self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10']])

    def test_filter_by_reportingdate(self):
        from DateTime import DateTime
        self.root['first_envelope'].manage_changeEnvelope(
                                reportingdate=DateTime("2010/07/02 00:00:00 GMT+2"))
        results = self.engine.getSearchResults(
                    reportingdate={'range': 'min:max',
                                   'query': [DateTime("2010/07/01 00:00:00 GMT+2"),
                                             DateTime("2010/07/03 00:00:00 GMT+2")]
                                  })
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope])


class ReportekEngineZipTest(unittest.TestCase):

    def test_zip_download(self):
        content = 'test content for our document'
        root = create_fake_root()
        engine = create_reportek_engine(root)

        envelope = create_envelope(root)
        doc = add_document(envelope, create_upload_file(content, 'foo.txt'))
        envelope.released = True
        envelope.title = "TestedEnvelope"

        response_body = StringIO()
        mock_response = Mock(write=response_body.write)

        with patch('Products.Reportek.ReportekEngine.getSecurityManager'):
            engine.zipEnvelopes(['/envelope'], Mock(), mock_response)

        response_body.seek(0)
        response_zip = zipfile.ZipFile(response_body)
        self.assertEqual(response_zip.namelist(), [
            'TestedEnvelope/foo.txt', 'TestedEnvelope/metadata.txt',
            'TestedEnvelope/README.txt', 'TestedEnvelope/history.txt'])
        self.assertEqual(response_zip.read('TestedEnvelope/foo.txt'), content)
