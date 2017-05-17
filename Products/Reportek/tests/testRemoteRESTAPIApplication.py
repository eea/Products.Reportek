from mock import Mock, patch
import json
import requests_mock
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

    def create_cepaa_set(self, idx, security=False, retries=5):
        col_id = "col%s" % idx
        env_id = "env%s" % idx
        proc_id = "proc%s" % idx
        act_id = "act%s" % idx
        app_id = "act%s" % idx
        country = 'http://spatial/%s' % idx
        dataflow_uris = ['http://obligation/%idx' % idx,]
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
        if retries != 5:
            act = proc.restrictedTraverse(app_id)
            act.retries = retries
        getattr(self.wf, proc_id).addActivity(act_id,
                                              split_mode='xor',
                                              join_mode='xor',
                                              start_mode=1,
                                              finish_mode=1,
                                              complete_automatically=0)
        self.wf[proc_id].addTransition('to_end', act_id, 'End')
        getattr(self.wf, proc_id).begin = act_id
        self.wf.setProcessMappings(proc_id, '1', '1')

        mock_dm_container = Mock(getSchemasForDataflows=Mock(return_value=[]))
        col.getDataflowMappingsContainer = Mock(return_value=mock_dm_container)

        env = Envelope(process=getattr(self.wf, proc_id),
                       title='FirstEnvelope',
                       authUser='TestUser',
                       year=2012,
                       endyear=2013,
                       partofyear='January',
                       country='http://spatial/1',
                       locality='TestLocality',
                       descr='TestDescription',
                       dataflow_uris=dataflow_uris)
        env._content_registry_ping = Mock()
        env.id = env_id
        getattr(self.app, col_id)._setOb(env_id, env)
        setattr(self, col_id, getattr(self.app, col_id))
        setattr(self, env_id, getattr(getattr(self.app, col_id), env_id))
        getattr(self, env_id).startInstance(self.app.REQUEST)

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_analysis(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            reason='OK',
            json=Mock(return_value=[
                {
                    "id": "7",
                    "type": "xquery 1.0",
                    "outputType": "HTML",
                    "url": "test.test",
                    "name": "Test 1",
                    "description": "This is a test",
                    "isActive": "1",
                    "runOnDemandMaxFileSizeMB": "200",
                    "schemaUrl": "http://local.test/test"
                },
                {
                    "id": "2",
                    "type": "xquery 1.0",
                    "outputType": "HTML",
                    "url": "test.test1",
                    "name": "Test 2",
                    "description": "This is another test",
                    "isActive": "1",
                    "runOnDemandMaxFileSizeMB": "200",
                    "schemaUrl": "http://local.test/test2"
                }
            ]))
        mock_requests.codes.ok = 200
        self.create_cepaa_set(1)

        params = {'schema': 'http://obligation/1dx'}
        mock_requests.get.assert_called_once_with(
            'http://submit.url/rest/qascripts',
            cookies=None,
            verify=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json'},
            params=params,
            timeout=20,
            data=None)

        @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
        def test_analysis_auth(self, mock_requests):
            mock_requests.get.return_value = Mock(
                status_code=200,
                reason='OK',
                json=Mock(return_value=[
                    {
                        "id": "7",
                        "type": "xquery 1.0",
                        "outputType": "HTML",
                        "url": "test.test",
                        "name": "Test 1",
                        "description": "This is a test",
                        "isActive": "1",
                        "runOnDemandMaxFileSizeMB": "200",
                        "schemaUrl": "http://local.test/test"
                    },
                    {
                        "id": "2",
                        "type": "xquery 1.0",
                        "outputType": "HTML",
                        "url": "test.test1",
                        "name": "Test 2",
                        "description": "This is another test",
                        "isActive": "1",
                        "runOnDemandMaxFileSizeMB": "200",
                        "schemaUrl": "http://local.test/test2"
                    }
                ]))
            mock_requests.codes.ok = 200
            self.create_cepaa_set(1, security=True)

            params = {'schema': 'http://obligation/1dx'}
            mock_requests.get.assert_called_once_with(
                'http://submit.url/rest/qascripts',
                cookies=None,
                verify=False,
                headers={'Content-Type': 'application/json',
                         'Accept': 'application/json',
                         'Authorization': 'token'},
                params=params,
                timeout=20,
                data=None)

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_workitem_initialization(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            reason='OK',
            json=Mock(return_value=[
                {
                    "id": "7",
                    "type": "xquery 1.0",
                    "outputType": "HTML",
                    "url": "test.test",
                    "name": "Test 1",
                    "description": "This is a test",
                    "isActive": "1",
                    "runOnDemandMaxFileSizeMB": "200",
                    "schemaUrl": "http://local.test/test"
                },
                {
                    "id": "2",
                    "type": "xquery 1.0",
                    "outputType": "HTML",
                    "url": "test.test1",
                    "name": "Test 2",
                    "description": "This is another test",
                    "isActive": "1",
                    "runOnDemandMaxFileSizeMB": "200",
                    "schemaUrl": "http://local.test/test2"
                }
            ]))
        mock_requests.codes.ok = 200
        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        analysis = prop['analysis']
        assert analysis['last_error'] is None
        assert isinstance(analysis['next_run'], DateTime)
        assert 'http://obligation/1dx' in analysis['jobs']

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_app_writes_success_in_event_log(self, mock_requests):
        script_id = '123'
        job_id = '1234'
        file_url = 'http://nohost/col1/env1/xml'
        mock_requests.get.side_effect = [
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value=[{
                        "id": script_id,
                        "type": "xquery 1.0",
                        "outputType": "HTML",
                        "url": "test.test",
                        "name": "Test 1",
                        "description": "This is a test",
                        "isActive": "1",
                        "runOnDemandMaxFileSizeMB": "200",
                        "schemaUrl": "http://local.test/test"
                 }])),
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value={
                        "scriptTitle": "Test 1",
                        "executionStatus": {
                            "statusId": "1",
                            "statusName": "Pending"
                        }
                 }))
        ]
        mock_requests.codes.ok = 200
        mock_requests.post.return_value = Mock(
            status_code=200,
            reason='OK',
            json=Mock(return_value={
                "jobId": job_id
            }))

        self.create_cepaa_set(1)

        evtlog = self.app.col1.env1['0'].event_log
        self.assertEqual(evtlog[1]['event'], 'restapp - job in progress: #{}'
                         ' for file: {}'.format(job_id,
                                                file_url.split('/')[-1]))

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_create_job_fb(self, mock_requests):
        script_id = '123'
        script_title = 'Test 1'
        job_id = '1234'
        mock_requests.get.side_effect = [
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value=[{
                        "id": script_id,
                        "type": "xquery 1.0",
                        "outputType": "HTML",
                        "url": "test.test",
                        "name": script_title,
                        "description": "This is a test",
                        "isActive": "1",
                        "runOnDemandMaxFileSizeMB": "200",
                        "schemaUrl": "http://local.test/test"
                 }])),
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value={
                        "scriptTitle": script_title,
                        "executionStatus": {
                            "statusId": "0",
                            "statusName": "Ready"
                        },
                        "feedbackStatus": "ERROR",
                        "feedbackMessage": "Some message",
                        "feedbackContentType": "text/html",
                        "feedbackContent": "<div>...</div>" 
                 }))
        ]
        mock_requests.codes.ok = 200
        mock_requests.post.return_value = Mock(
            status_code=200,
            reason='OK',
            json=Mock(return_value={
                "jobId": job_id
            }))

        self.create_cepaa_set(1)

        mock_requests.codes.ok = 200

        prop = self.app.col1.env1['0'].restapp
        evtlog = self.app.col1.env1['0'].event_log
        self.assertEqual(evtlog[2]['event'], 'restapp - job completed: #{}'
                         ' - {}'.format(job_id, script_title))
        self.assertEqual(prop['jobs'][job_id]['status'], 'Ready')
        fb_id = 'restapp_1234'
        assert fb_id in self.app.col1.env1.objectIds()
        fb = self.app.col1.env1.restrictedTraverse(fb_id)
        self.assertEqual(fb.feedback_status, 'ERROR')

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_job_not_done(self, mock_requests):
        script_id = '123'
        job_id = '1234'
        mock_requests.get.side_effect = [
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value=[{
                        "id": script_id,
                        "type": "xquery 1.0",
                        "outputType": "HTML",
                        "url": "test.test",
                        "name": "Test 1",
                        "description": "This is a test",
                        "isActive": "1",
                        "runOnDemandMaxFileSizeMB": "200",
                        "schemaUrl": "http://local.test/test"
                 }])),
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value={
                        "scriptTitle": "Test 1",
                        "executionStatus": {
                            "statusId": "1",
                            "statusName": "Pending"
                        }
                 })),
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value={
                        "scriptTitle": "Test 1",
                        "executionStatus": {
                            "statusId": "2",
                            "statusName": "Failed"
                        }
                 }))
        ]
        mock_requests.codes.ok = 200
        mock_requests.post.return_value = Mock(
            status_code=200,
            reason='OK',
            json=Mock(return_value={
                "jobId": job_id
            }))
        mock_requests.codes.ok = 200

        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        self.assertEqual(prop['jobs'][job_id]['status'], 'Pending')
        self.assertEqual(4, prop['jobs'][job_id]['retries'])
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0',
                                                           self.app.REQUEST)
        self.assertEqual(3, prop['jobs'][job_id]['retries'])

    @patch('Products.Reportek.RemoteRESTAPIApplication.requests')
    def test_job_pending_no_retries(self, mock_requests):
        script_id = '123'
        job_id = '1234'
        mock_requests.get.side_effect = [
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value=[{
                        "id": script_id,
                        "type": "xquery 1.0",
                        "outputType": "HTML",
                        "url": "test.test",
                        "name": "Test 1",
                        "description": "This is a test",
                        "isActive": "1",
                        "runOnDemandMaxFileSizeMB": "200",
                        "schemaUrl": "http://local.test/test"
                 }])),
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value={
                        "scriptTitle": "Test 1",
                        "executionStatus": {
                            "statusId": "1",
                            "statusName": "Pending"
                        }
                 })),
            Mock(status_code=200,
                 reason='OK',
                 json=Mock(return_value={
                        "scriptTitle": "Test 1",
                        "executionStatus": {
                            "statusId": "2",
                            "statusName": "Failed"
                        }
                 }))
        ]
        mock_requests.codes.ok = 200
        mock_requests.post.return_value = Mock(
            status_code=200,
            reason='OK',
            json=Mock(return_value={
                "jobId": job_id
            }))
        mock_requests.codes.ok = 200
        self.create_cepaa_set(1, retries=2)
        prop = self.app.col1.env1['0'].restapp
        evtlog = self.app.col1.env1['0'].event_log
        self.assertEqual(prop['jobs'][job_id]['status'], 'Pending')
        self.assertEqual(1, prop['jobs'][job_id]['retries'])

        restapp = self.app.Applications.proc1.act1
        # Setting the retry frequency to 0
        restapp.r_frequency = 0
        for retry in range(2):
            restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)

        self.assertEqual(0, prop['jobs'][job_id]['retries'])
        self.assertEqual(evtlog[-1].get('event'), 'forwarded to End')
