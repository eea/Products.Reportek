import unittest
from StringIO import StringIO
import zipfile
from mock import Mock, patch
from utils import create_fake_root, create_temp_reposit, create_upload_file
from utils import create_envelope, add_document
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
