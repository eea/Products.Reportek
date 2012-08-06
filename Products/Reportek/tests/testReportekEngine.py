import unittest
from StringIO import StringIO
import zipfile
from mock import Mock, patch
from utils import (create_fake_root, create_temp_reposit, create_upload_file,
                  create_envelope, add_document, makerequest)
from Products.Reportek.ReportekEngine import ReportekEngine

def setUpModule(self):
    self._cleanup_temp_reposit = create_temp_reposit()

def tearDownModule(self):
    self._cleanup_temp_reposit()


def create_reportek_engine(parent):
    ob = ReportekEngine()
    parent._setObject(ob.id, ob)
    return parent[ob.id]


class ReportekEngineTest(unittest.TestCase):

    def setUp(self):
        from Products.ZCatalog.ZCatalog import ZCatalog
        from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
        from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex
        from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
        from Products.PluginIndexes.PathIndex.PathIndex import PathIndex
        from Products.Reportek import create_reportek_indexes
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

    def test_getUniqueValuesFor(self):
        from Products.Reportek.Envelope import Envelope
        engine = create_reportek_engine(self.root)
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
        results = engine.getUniqueValuesFor('dataflow_uris')
        self.assertEqual(results, ('http://example.com/dataflow/1',))


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
