import unittest
from mock import Mock

from StringIO import StringIO
from utils import simple_addEnvelope

from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Products.Reportek.Collection import Collection
from Products.Reportek.Envelope import Envelope
from Products.Reportek.process import process
from Products.Reportek import exceptions


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
        template = SimpleItem()
        template.id = 'StartActivity'
        template.__call__ = Mock(return_value='Envelope Test Template')
        self.app.Templates._setOb('StartActivity', template)
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

class _WorkflowTestCase(_BaseTest):

    def create_cepaa_set(self, idx):
        col_id = "col%s" %idx
        env_id = "env%s" %idx
        proc_id = "proc%s" %idx
        act_id = "act%s" %idx
        app_id = "act%s" %idx
        country = 'http://spatial/%s' %idx
        dataflow_uris = 'http://obligation/%idx' %idx
        "create collection, envelope, process, activity, application"
        col = Collection(col_id, country=country, dataflow_uris=dataflow_uris)
        self.app._setOb(col_id, col)

        self.app.Templates.StartActivity = Mock(return_value='Test Application')
        self.app.Templates.StartActivity.title_or_id = Mock(return_value='Start Activity Template')
        create_process(self, proc_id)
        self.wf.addApplication(app_id, 'SomeFolder/%s' %app_id)

        self.app.Applications._setOb(proc_id, Folder(proc_id))
        proc = getattr(self.app.Applications, proc_id)

        app = SimpleItem(app_id)
        app.id = app_id
        app.__call__ = Mock(return_value='Test Application')
        proc._setOb(app_id, app)
        getattr(proc, app_id).id = app_id
        getattr(self.wf, proc_id).addActivity(act_id,
                            split_mode='xor',
                            join_mode='xor',
                            start_mode=1)
        getattr(self.wf, proc_id).begin = act_id
        self.wf.setProcessMappings(proc_id, '1', '1')

        env = Envelope(process=getattr(self.wf, proc_id),
                       title='FirstEnvelope',
                       authUser='TestUser',
                       year=2012,
                       endyear=2013,
                       partofyear='January',
                       country='http://spatial/1',
                       locality='TestLocality',
                       descr='TestDescription')
        env.id = env_id
        getattr(self.app, col_id)._setOb(env_id, env)
        setattr(self, col_id, getattr(self.app, col_id))
        setattr(self, env_id, getattr(getattr(self.app, col_id), env_id))
        getattr(self, env_id).startInstance(self.app.REQUEST)
