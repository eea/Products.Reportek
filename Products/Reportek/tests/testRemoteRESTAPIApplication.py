from mock import Mock, patch
import json
from OFS.Folder import Folder
from DateTime import DateTime

from common import WorkflowTestCase
from Products.Reportek.Collection import Collection
from Products.Reportek.Envelope import Envelope
from Products.Reportek import constants
from Products.Reportek.RemoteRESTAPIApplication import RemoteRESTAPIApplication
from Products.Reportek.RemoteRESTAPIApplication import manage_addRemoteRESTAPIApplication


class RemoteRESTAPIApplicationProduct(WorkflowTestCase):

    def setUp(self):
        super(RemoteRESTAPIApplicationProduct, self).setUp()
        self.app._setOb(
            constants.APPLICATIONS_FOLDER_ID,
            Folder(constants.APPLICATIONS_FOLDER_ID))
        self.apps_folder = getattr(self.app, constants.APPLICATIONS_FOLDER_ID)
        self.apps_folder._setOb(
            'Common',
            Folder('Common'))

    def create_cepaa_set(self, idx):
        col_id = "col%s" % idx
        env_id = "env%s" % idx
        proc_id = "proc%s" % idx
        act_id = "act%s" % idx
        app_id = "act%s" % idx
        country = 'http://spatial/%s' % idx
        dataflow_uris = 'http://obligation/%idx' % idx
        col = Collection(col_id, country=country, dataflow_uris=dataflow_uris)
        self.app._setOb(col_id, col)

        self.app.Templates.StartActivity = Mock(return_value='Test Application')
        self.app.Templates.StartActivity.title_or_id = Mock(return_value='Start Activity Template')
        self.create_process(self, proc_id)
        self.wf.addApplication(app_id, 'SomeFolder/%s' % app_id)

        self.app.Applications._setOb(proc_id, Folder(proc_id))
        proc = getattr(self.app.Applications, proc_id)

        manage_addRemoteRESTAPIApplication(
            proc,
            app_id, 'title',
            'http://submit.url/rest', 'http://submit.url/rest/async',
            '/jobs', '/batch', '/qascripts',
            'restapp'
        )
        getattr(self.wf, proc_id).addActivity(act_id,
                                              split_mode='xor',
                                              join_mode='xor',
                                              start_mode=1,
                                              finish_mode=1,
                                              complete_automatically=0)
        self.wf[proc_id].addTransition('to_end', act_id, 'End')
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
        env._content_registry_ping = Mock()
        env.id = env_id
        getattr(self.app, col_id)._setOb(env_id, env)
        setattr(self, col_id, getattr(self.app, col_id))
        setattr(self, env_id, getattr(getattr(self.app, col_id), env_id))
        getattr(self, env_id).startInstance(self.app.REQUEST)

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_request_async_batch_job(self, mock_requests):
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobs': [
                {
                    'jobId': 123,
                    'fileUrl': 'http://some.file.url.1'
                }, {
                    'jobId': 456,
                    'fileUrl': 'http://some.file.url.2'
                }
            ]}))
        mock_requests.codes.ok = 200
        self.create_cepaa_set(1)
        data = {'envelopeUrl': 'http://nohost/col1/env1'}
        mock_requests.post.assert_called_once_with(
            'http://submit.url/rest/async/jobs/batch',
            data=json.dumps(data),
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json'},
            timeout=20)

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_workitem_initialization(self, mock_requests):
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobs': [
                {
                    'jobId': 123,
                    'fileUrl': 'http://some.file.url.1'
                }, {
                    'jobId': 456,
                    'fileUrl': 'http://some.file.url.2'
                }
            ]}))
        mock_requests.codes.ok = 200
        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        analysis = prop['analysis']
        assert analysis['last_error'] is None
        assert isinstance(analysis['next_run'], DateTime)
