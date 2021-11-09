import unittest
import zipfile
from StringIO import StringIO

from common import BaseTest, BaseUnitTest, ConfigureReportek
from DateTime import DateTime
from mock import Mock, patch
from Products.Reportek import Converters, constants
from Products.Reportek.Envelope import Envelope
from Products.Reportek.ReportekEngine import ReportekEngine
from utils import (add_document, create_envelope, create_fake_root,
                   create_upload_file)


class ReportekEngineTest(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(ReportekEngineTest, self).afterSetUp()
        self.createStandardCatalog()

        self.engine.localities_dict = Mock(return_value={
            'http://rod.eionet.eu.int/spatial/2': {'name': 'Albania'},
            'http://rod.eionet.eu.int/spatial/3': {'name': 'Austria'}
        })
        self.engine.ZopeTime = Mock(return_value=DateTime())

    def test_searchfeedbacks_on_disk(self):
        self.createStandardDependencies()
        self.createStandardCollection()
        self.createStandardEnvelope()
        try:
            zpt = ReportekEngine.searchfeedbacks
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsfeedbacks_on_disk(self):
        try:
            zpt = ReportekEngine.resultsfeedbacks
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_recent_uploads_on_disk(self):
        try:
            zpt = ReportekEngine.recent
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_searchdataflow_on_disk(self):
        try:
            zpt = ReportekEngine._searchdataflow
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_searchxml_on_disk(self):
        try:
            zpt = ReportekEngine.searchxml
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsxml_on_disk(self):
        try:
            zpt = ReportekEngine.resultsxml
            zpt.read()
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
                                  partofyear='JANUARY',
                                  country='http://example.com/country/1',
                                  locality='TestLocality',
                                  descr='TestDescription')
        first_envelope._content_registry_ping = Mock()
        first_envelope.id = 'first_envelope'
        self.root._setObject(first_envelope.id, first_envelope)
        self.root[first_envelope.id].manage_changeEnvelope(
            dataflow_uris='http://example.com/dataflow/1'
        )
        results = self.engine.getUniqueValuesFor('dataflow_uris')
        self.assertEqual(results, ('http://example.com/dataflow/1',))

    @unittest.expectedFailure
    def test_manage_editEngine_GET(self):
        """
        This tests simulates a GET to ReportekEngine/manage_editEngine
        and checks that engine's attributes are not changed
        """
        from copy import copy
        self.engine.ZopeTime = Mock(return_value=DateTime())
        before_values = copy(self.engine.__dict__)
        # FIXME
        self.login()
        assert self.engine.manage_properties()
        self.assertEqual(before_values, self.engine.__dict__)

    @unittest.expectedFailure
    def test_manage_editEngine_no_REQUEST(self):
        """
        This tests simulates a programmatic call to
        ReportekEngine.manage_editEngine and checks that engine's attributes
        are changed accordingly
        """
        # FIXME
        self.engine.ZopeTime = Mock(return_value=DateTime())
        self.engine.title = 'Before Title'
        self.engine.manage_editEngine(title='After Title', REQUEST=None)
        self.assertEqual('After Title', self.engine.title)

    @unittest.expectedFailure
    def test_manage_editEngine_POST(self):
        """
        This tests simulates a POST to ReportekEngine.manage_editEngine
        and checks that engine's attributes are changed accordingly
        """
        # FIXME
        self.root.REQUEST['REQUEST_METHOD'] = 'POST'
        self.engine.ZopeTime = Mock(return_value=DateTime())
        self.engine.title = 'Before Title'
        self.engine.manage_editEngine(
            title='After Title', REQUEST=self.root.REQUEST)
        self.assertEqual('After Title', self.engine.title)


class SearchResultsTest(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(SearchResultsTest, self).afterSetUp()
        self.createStandardCatalog()
        from Products.Reportek.Envelope import Envelope
        process = Mock()
        process.absolute_url = Mock(return_value='/ProcessURL')
        first_envelope = Envelope(process=process,
                                  title='FirstEnvelope',
                                  authUser='TestUser',
                                  year=2012,
                                  endyear=2013,
                                  partofyear='JANUARY',
                                  country='http://example.com/country/1',
                                  locality='TestLocality',
                                  descr='TestDescription')
        first_envelope._content_registry_ping = Mock()
        first_envelope.id = 'first_envelope'
        self.root._setObject(first_envelope.id, first_envelope)
        self.root[first_envelope.id].manage_changeEnvelope(
            dataflow_uris='http://example.com/dataflow/1')
        self.root['first_envelope'].getEngine = Mock()
        setattr(
            self.root.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(return_value=Mock(text='feedbacktext')))
        getattr(self.root.getPhysicalRoot(),
                constants.CONVERTERS_ID).__getitem__ = Mock(
            return_value=safe_html)
        self.root['first_envelope'].manage_addFeedback(
            'feedbackid', 'Title',
            'Feedback text', '', 'WorkflowEngine/begin_end', 1)
        self.root['first_envelope'].manage_addFeedback(
            'feedback5', 'Title',
            'Feedback text', '', 'WorkflowEngine/begin_end', 1)
        self.root['first_envelope'].manage_addFeedback(
            'feedback10', 'Title',
            'Feedback text', '', 'WorkflowEngine/begin_end', 1)

        second_envelope = Envelope(process=process,
                                   title='SecondEnvelope',
                                   authUser='TestUser',
                                   year=2012,
                                   endyear=2013,
                                   partofyear='JUNE',
                                   country='http://example.com/country/2',
                                   locality='TestLocality',
                                   descr='TestDescription')
        second_envelope._content_registry_ping = Mock()
        second_envelope.id = 'second_envelope'
        self.root._setObject(second_envelope.id, second_envelope)
        self.root[second_envelope.id].manage_changeEnvelope(
            dataflow_uris='http://example.com/dataflow/2')

    def test_returns_all(self):
        results = self.engine.getSearchResults()
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [
            self.root.first_envelope['feedbackid'],
            self.root.first_envelope['feedback5'],
            self.root.first_envelope['feedback10'],
            self.root.first_envelope,
            self.root.second_envelope])

    def test_filter_by_meta_type(self):
        results = self.engine.getSearchResults(meta_type='Report Feedback')
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope['feedbackid'],
                                self.root.first_envelope['feedback5'],
                                self.root.first_envelope['feedback10']])

    def test_filter_by_dataflow_uris(self):
        results = self.engine.getSearchResults(
            dataflow_uris='http://example.com/dataflow/2')
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.second_envelope])

    def test_filter_by_country(self):
        results = self.engine.getSearchResults(
            country='http://example.com/country/1')
        res = [el.getObject() for el in results]
        self.assertEqual(res, [self.root.first_envelope])

    def test_filter_by_id(self):
        results = self.engine.getSearchResults(id={'range': 'min:max',
                                                   'query': ['feedback0',
                                                             'feedback9']})
        feedbacks = [el.getObject() for el in results]
        self.assertEqual(feedbacks, [self.root.first_envelope['feedback5'],
                                     self.root.first_envelope['feedback10']])

    def test_filter_by_reportingdate(self):
        self.root['first_envelope'].manage_changeEnvelope(
            reportingdate=DateTime("2010/07/02 00:00:00 GMT+2"))
        results = self.engine.getSearchResults(
            reportingdate={'range': 'min:max',
                           'query': [DateTime("2010/07/01 00:00:00 GMT+2"),
                                     DateTime("2010/07/03 00:00:00 GMT+2")]
                           })
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope])


class ReportekEngineZipTest(BaseUnitTest):

    def test_zip_download(self):
        content = 'test content for our document'
        root = create_fake_root()
        engine = BaseTest.create_reportek_engine(root)

        envelope = create_envelope(root)
        add_document(envelope, create_upload_file(content, 'foo.txt'))
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
