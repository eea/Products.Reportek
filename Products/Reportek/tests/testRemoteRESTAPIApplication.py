from mock import Mock, patch
import json
from OFS.Folder import Folder
from DateTime import DateTime

from common import WorkflowTestCase
from Products.Reportek.Collection import Collection
from Products.Reportek.Envelope import Envelope
from Products.Reportek import constants
from Products.Reportek import Converters
from Products.Reportek.RemoteRESTAPIApplication import RemoteRESTAPIApplication
from Products.Reportek.RemoteRESTAPIApplication import manage_addRemoteRESTAPIApplication


class RemoteRESTAPIApplicationProduct(WorkflowTestCase):

    def setUp(self):
        super(RemoteRESTAPIApplicationProduct, self).setUp()
        self.app._setOb(
            constants.APPLICATIONS_FOLDER_ID,
            Folder(constants.APPLICATIONS_FOLDER_ID))
        setattr(
            self.app.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(text='feedbacktext'))
        getattr(self.app.getPhysicalRoot(),
                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)
        self.apps_folder = getattr(self.app, constants.APPLICATIONS_FOLDER_ID)
        self.apps_folder._setOb(
            'Common',
            Folder('Common'))

    def create_cepaa_set(self, idx, security=False):
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
        token = ''
        if security:
            token = 'token'
        manage_addRemoteRESTAPIApplication(
            proc,
            app_id, 'title',
            'http://submit.url/rest', 'http://submit.url/rest/async',
            '/jobs', '/batch', '/qascripts',
            'restapp', token=token
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
    def test_request_async_batch_job_auth(self, mock_requests):
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
        self.create_cepaa_set(1, security=True)
        data = {'envelopeUrl': 'http://nohost/col1/env1'}
        mock_requests.post.assert_called_once_with(
            'http://submit.url/rest/async/jobs/batch',
            data=json.dumps(data),
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'X-Auth-Token': 'token'},
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

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_app_writes_success_in_event_log(self, mock_requests):
        job1id = 123
        job1fileurl = 'http://some.file.url.1'
        job2id = 456
        job2fileurl = 'http://some.file.url.2'
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobs': [
                {
                    'jobId': job1id,
                    'fileUrl': job1fileurl
                }, {
                    'jobId': job2id,
                    'fileUrl': job2fileurl
                }
            ]}))
        mock_requests.codes.ok = 200
        self.create_cepaa_set(1)
        evtlog = self.app.col1.env1['0'].event_log

        self.assertEqual(evtlog[1]['event'], 'restapp - job in progress: #{}'
                         ' for file: {}'.format(job1id,
                                                job1fileurl.split('/')[-1]))
        assert evtlog[2]['event'] == 'restapp - job in progress: #{} for file'\
                                     ': {}'.format(job2id,
                                                   job2fileurl.split('/')[-1])

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_create_job_fb(self, mock_requests):
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobs': [
                {
                    'jobId': 123,
                    'fileUrl': 'http://some.file.url.1'
                }
            ]}))
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'scriptTitle': 'Check obligation dependent QA/QC rules',
                'executionStatus': {
                    'statusId': '0',
                    'statusName': 'Ready'
                },
                'feedbackStatus': 'ERROR',
                'feedbackMessage': 'Some message',
                'feedbackContentType': 'text/html',
                'feedbackContent': '<div>Dummy</div>'
            }))
        mock_requests.codes.ok = 200

        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        evtlog = self.app.col1.env1['0'].event_log
        self.assertEqual(evtlog[2]['event'], 'restapp - job completed: #123'
                         ' - Check obligation dependent QA/QC rules')
        self.assertEqual(prop['jobs'][123]['status'], 'Ready')
        fb_id = 'restapp_123'
        assert fb_id in self.app.col1.env1.objectIds()
        fb = self.app.col1.env1.restrictedTraverse(fb_id)
        self.assertEqual(fb.feedback_status, 'ERROR')

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_job_not_done(self, mock_requests):
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobs': [
                {
                    'jobId': 123,
                    'fileUrl': 'http://some.file.url.1'
                }
            ]}))
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'scriptTitle': 'Check obligation dependent QA/QC rules',
                'executionStatus': {
                    'statusId': '1',
                    'statusName': 'Pending'
                }
            }))
        mock_requests.codes.ok = 200

        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        self.assertEqual(prop['jobs'][123]['status'], 'Pending')
        self.assertEqual(4, prop['jobs'][123]['retries'])
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual(3, prop['jobs'][123]['retries'])

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_job_pending_no_retries(self, mock_requests):
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobs': [
                {
                    'jobId': 123,
                    'fileUrl': 'http://some.file.url.1'
                }
            ]}))
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'scriptTitle': 'Check obligation dependent QA/QC rules',
                'executionStatus': {
                    'statusId': '1',
                    'statusName': 'Pending'
                }
            }))
        mock_requests.codes.ok = 200

        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        evtlog = self.app.col1.env1['0'].event_log
        self.assertEqual(prop['jobs'][123]['status'], 'Pending')
        self.assertEqual(4, prop['jobs'][123]['retries'])
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'scriptTitle': 'Check obligation dependent QA/QC rules',
                'executionStatus': {
                    'statusId': '1',
                    'statusName': 'Pending'
                }
            }))
        restapp = self.app.Applications.proc1.act1
        # Setting the retry frequency to 0
        restapp.r_frequency = 0
        for retry in range(4):
            restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)

        self.assertEqual(0, prop['jobs'][123]['retries'])
        self.assertEqual(evtlog[-1].get('event'), 'forwarded to End')

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_bad_batch_json(self, mock_requests):
        def bad_json():
            raise ValueError
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=bad_json)
        mock_requests.codes.ok = 200

        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        self.assertEqual(prop['analysis']['last_error'], 'Envelope analysis'
                         ' job for http://nohost/col1/env1 failed: (Unable to'
                         ' convert QA Service response to JSON: )')

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_batch_error(self, mock_requests):
        mock_requests.post.return_value = Mock(
            status_code=500,
            json=Mock(return_value={
                'httpStatusCode': 500,
                'errorMessage': 'QA Service Exception'
            })
        )
        mock_requests.codes.ok = 200

        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        self.assertEqual(prop['analysis']['last_error'], 'Envelope analysis'
                         ' job for http://nohost/col1/env1 failed: (HTTP Error'
                         ' 500 - QA Service Exception)')

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_bad_job_json(self, mock_requests):
        def bad_json():
            raise ValueError
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobs': [
                {
                    'jobId': 123,
                    'fileUrl': 'http://some.file.url.1'
                }
            ]}))
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=bad_json)
        mock_requests.codes.ok = 200

        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        self.assertEqual('Job: #123 for file some.file.url.1, failed: (Unable'
                         ' to convert QA Service response to JSON: )',
                         prop['jobs'][123]['last_error'])
