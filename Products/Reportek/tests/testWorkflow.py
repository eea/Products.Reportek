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


def create_envelope(obj):
    col = obj.app.collection
    #obj.login() # Login as test_user_1_
    #user = getSecurityManager().getUser()
    #obj.app.REQUEST.AUTHENTICATED_USER = user
    #reportek = obj.app.manage_addProduct['Reportek']
    result = obj.app.collection.manage_addEnvelope('', '', '2003', '2004', '',
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
