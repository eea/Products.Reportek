import unittest
from StringIO import StringIO
from utils import simple_addEnvelope


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
    result = simple_addEnvelope(obj.app.collection, '', '', year, endyear, '',
         'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
    envelope = col.unrestrictedTraverse(result.split('/')[-1], None)
    return envelope


def createStandardCollection(app):
    # title, descr,year, endyear, partofyear, country, locality,
    # dataflow_uris,allow_collections=0, allow_envelopes=0, id='', REQUEST=None
    app.manage_addProduct['Reportek'].manage_addCollection('TestTitle', 'Desc',
        '2003', '2004', '', 'http://rod.eionet.eu.int/spatial/2', '', ['http://rod.eionet.eu.int/obligations/8'],
        allow_collections=1, allow_envelopes=1, id='collection')


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
