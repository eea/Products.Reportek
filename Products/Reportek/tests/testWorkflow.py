import unittest
from StringIO import StringIO
from Products.Reportek import RepUtils
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
from configurereportek import ConfigureReportek
from Products.Reportek.constants import CONVERTERS_ID
from Products.Reportek.exceptions import CannotPickProcess, NoProcessAvailable


def create_process(obj, p_id, dataflows=None, countries=None):
    """Creates a process with explicit dataflows and countries by default"""

    obj.wf.manage_addProcess(p_id, BeginEnd=1)
    p_dataflows = ['http://rod.eionet.eu.int/obligations/8']
    p_countries = ['http://rod.eionet.eu.int/spatial/2']
    if dataflows:
        p_dataflows = dataflows
    if countries:
        p_countries = countries
    obj.wf.setProcessMappings(p_id, '', '',
                               p_dataflows,
                               p_countries)
    return obj.wf._getOb(p_id).absolute_url(1)


def create_envelope(obj, **kwargs):
    col = obj.app.collection
    #obj.login() # Login as test_user_1_
    #user = getSecurityManager().getUser()
    #obj.app.REQUEST.AUTHENTICATED_USER = user
    #reportek = obj.app.manage_addProduct['Reportek']
    if 'year' in kwargs.keys():
        year = kwargs['year']
    else:
        year = '2003'
    if 'endyear' in kwargs.keys():
        endyear = kwargs['endyear']
    else:
        endyear = '2004'
    result = obj.app.collection.manage_addEnvelope('', '', year, endyear, '',
         'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
    envelope = col.unrestrictedTraverse(result.split('/')[-1], None)
    return envelope


def create_mock_request():
    from mock import Mock
    request = Mock()
    request.physicalPathToVirtualPath = lambda x: x
    request.physicalPathToURL = lambda x: x
    response = request.RESPONSE
    response._data = StringIO()
    response.write = response._data.write
    request._headers = {}
    request.get_header = request._headers.get
    return request


def createStandardCollection(app):
    # title, descr,year, endyear, partofyear, country, locality,
    # dataflow_uris,allow_collections=0, allow_envelopes=0, id='', REQUEST=None
    app.manage_addProduct['Reportek'].manage_addCollection('TestTitle', 'Desc',
        '2003', '2004', '', 'http://rod.eionet.eu.int/spatial/2', '', ['http://rod.eionet.eu.int/obligations/8'],
        allow_collections=1, allow_envelopes=1, id='collection')

class _BaseTest(unittest.TestCase):

    def setUp(self):
        from mock import Mock
        from utils import create_fake_root, makerequest
        from OFS.Folder import Folder
        from Globals import DTMLFile
        from Products.Reportek.Collection import Collection
        from Products.Reportek.OpenFlowEngine import OpenFlowEngine

        self.app = create_fake_root()
        name = 'mock'
        new_environ = {
            'PATH_INFO': '/' + name,
            '_stdout': StringIO(),
        }
        self.app.REQUEST = makerequest(self.app, new_environ['_stdout'], new_environ).REQUEST
        self.app.REQUEST.AUTHENTICATED_USER = Mock()
        self.app.REQUEST.AUTHENTICATED_USER.getUserName.return_value = 'gigel'
        ofe = OpenFlowEngine('WorkflowEngine', 'title')
        self.app._setObject('WorkflowEngine', ofe)
        self.wf = self.app.WorkflowEngine
        args = {'id': 'collection',
                'title': 'mock_collection',
                'year': '2011',
                'endyear': '2012',
                'partofyear': 'wholeyear',
                'country': 'http://rod.eionet.eu.int/spatial/2',
                'locality': '',
                'descr': '',
                'dataflow_uris': ['http://rod.eionet.eu.int/obligations/8'],
                'allow_collections': True,
                'allow_envelopes': True}
        col = Collection(**args)
        self.app._setObject('collection', col)
        self.app._setObject('Templates', Folder('Templates'))
        self.app.Templates.StartActivity = DTMLFile('dtml/testEnvelopeIndex',globals())
        self.app.Templates.StartActivity.title_or_id = Mock(return_value='Start Activity Template')
        create_process(self, 'process')
        self.wf.addApplication('StartActivity', 'Templates/StartActivity')
        self.wf.process.addActivity('AutoBegin',
                            split_mode='xor',
                            join_mode='xor',
                            start_mode=1,
                            application='StartActivity')
        self.wf.process.begin = 'AutoBegin'
        self.wf.setProcessMappings('process', '1', '1')


class EnvelopeRenderingTestCase(_BaseTest):

    def setUp(self):
        super(EnvelopeRenderingTestCase, self).setUp()
        envelope = create_envelope(self)
        envelope.standard_html_header = ""
        envelope.standard_html_footer = ""
        self.envelope = envelope

    def test_overview_without_rights(self):
        from utils import publish_view
        self.assertIn('This envelope is not yet available for public view.\nWork is still in progress.',
                       publish_view(self.envelope).body)

    def test_overview_with_rights(self):
        from utils import chase_response, load_json
        from mock import Mock
        from AccessControl.User import User
        self.envelope.canViewContent = Mock(return_value=1)
        self.wf.canPullActivity = Mock(return_value=True)
        localities_table = load_json('localities_table.json')
        self.envelope.localities_table = Mock(return_value=localities_table)
        w_item_0 = getattr(self.envelope,'0')
        w_item_0.status = 'active'
        w_item_0.actor = 'gigel'
        user = User('gigel', 'gigel', ['manager'], '')
        self.assertEqual('Envelope Test Template', chase_response(self.envelope, user=user).body.strip())


class FindProcessTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    messages = {
      CannotPickProcess: 'More than one process associated with this envelope',
      NoProcessAvailable: 'No process associated with this envelope'
    }


    def assertCreateEnvelopeRaises(self, exception,
                                   dataflow=None, country=None):
        if not dataflow:
            dataflow = 'http://rod.eionet.eu.int/obligations/8'
        if not country:
            country = 'http://rod.eionet.eu.int/spatial/2'
        with self.assertRaisesRegexp(exception, self.messages.get(exception)):
            create_envelope(self)

    def afterSetUp(self):
        self.createStandardCollection()
        self.wf = self.app.WorkflowEngine
        from mock import Mock
        self.app.REQUEST.AUTHENTICATED_USER = Mock()
        self.app.REQUEST.AUTHENTICATED_USER.getUserName.return_value = 'gigel'

    def test_NoProcessAvailable_exception(self):
        self.assertCreateEnvelopeRaises(NoProcessAvailable)

    def test_only_one_available(self):
        process_path = create_process(self, 'p1')
        self.assertEqual(create_envelope(self).process_path, process_path)

    def test_explicitly_vs_wild_dataflow(self):
        p_path1 = create_process(self, 'p1', dataflows=['*'])
        p_path2 = create_process(self, 'p2')
        self.assertEqual(create_envelope(self).process_path, p_path2)

    def test_explicitly_vs_wild_country(self):
        p_path1 = create_process(self, 'p1', countries=['*'])
        p_path2 = create_process(self, 'p2')
        self.assertEqual(create_envelope(self).process_path, p_path2)

    def test_wild_dataflow_vs_wild_country(self):
        create_process(self, 'p1', dataflows=['*'])
        create_process(self, 'p2', countries=['*'])
        self.assertCreateEnvelopeRaises(CannotPickProcess)

    def test_both_wild(self):
        create_process(self, 'p1', dataflows=['*'], countries=['*'])
        create_process(self, 'p2', dataflows=['*'], countries=['*'])
        self.assertCreateEnvelopeRaises(CannotPickProcess)

    def test_both_explicitly_specified(self):
        create_process(self, 'p1')
        create_process(self, 'p2')
        self.assertCreateEnvelopeRaises(CannotPickProcess)


class EnvelopePeriodValidationTestCase(_BaseTest):

    def test_year_before_1000_redirection(self):
        from DateTime.interfaces import SyntaxError
        self.app.standard_html_header = ""
        self.app.standard_html_footer = ""
        self.assertRaises(SyntaxError,
                          lambda : create_envelope(self, year='206', endyear='2008'))

    def test_year_not_integer(self):
        envelope = create_envelope(self, year='abc', endyear='2008')
        self.assertEqual(envelope.year, 2008)
        self.assertEqual(envelope.endyear, 2008)

    def test_endyear_not_integer(self):
        envelope = create_envelope(self, year='abc', endyear='abc')
        self.assertEqual(envelope.year, '')
        self.assertEqual(envelope.endyear, '')
