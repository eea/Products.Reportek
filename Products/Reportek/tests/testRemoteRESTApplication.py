import re
import unittest
from mock import Mock, MagicMock, patch, call
from utils import create_fake_root
from DateTime import DateTime
from path import path

from OFS.Folder import Folder
from Products.ZCatalog.ZCatalog import ZCatalog

from common import create_mock_request, _BaseTest, create_process
from Products.Reportek.Collection import Collection
from Products.Reportek.Converters import Converters
from Products.Reportek.Envelope import Envelope
from Products.Reportek.ReportekEngine import ReportekEngine
from Products.Reportek import constants
from Products.Reportek.RemoteRESTApplication import RemoteRESTApplication, manage_addRemoteRESTApplication


class RemoteRESTApplicationProduct(_BaseTest):

    def create_cepaa_set(self, idx):
        col_id = "col%s" %idx
        env_id = "env%s" %idx
        proc_id = "proc%s" %idx
        act_id = "act%s" %idx
        app_id = "act%s" %idx
        country = 'http://spatial/%s' %idx
        dataflow_uris = 'http://obligation/%idx' %idx
        col = Collection(col_id, country=country, dataflow_uris=dataflow_uris)
        self.app._setOb(col_id, col)

        self.app.Templates.StartActivity = Mock(return_value='Test Application')
        self.app.Templates.StartActivity.title_or_id = Mock(return_value='Start Activity Template')
        create_process(self, proc_id)
        self.wf.addApplication(app_id, 'SomeFolder/%s' %app_id)

        self.app.Applications._setOb(proc_id, Folder(proc_id))
        proc = getattr(self.app.Applications, proc_id)

        manage_addRemoteRESTApplication(
            proc,
            app_id, 'title',
            'http://submit.url/', 'http://check.url/',
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
        env.id = env_id
        getattr(self.app, col_id)._setOb(env_id, env)
        setattr(self, col_id, getattr(self.app, col_id))
        setattr(self, env_id, getattr(getattr(self.app, col_id), env_id))
        getattr(self, env_id).startInstance(self.app.REQUEST)

    def setUp(self):
        super(RemoteRESTApplicationProduct, self).setUp()
        self.app._setOb(
            constants.APPLICATIONS_FOLDER_ID,
            Folder(constants.APPLICATIONS_FOLDER_ID))
        self.apps_folder = getattr(self.app, constants.APPLICATIONS_FOLDER_ID)
        self.apps_folder._setOb(
            'Common',
            Folder('Common'))

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_for_new_job_success(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url/',
                                        'http://check.url/', 'name')
        self.create_cepaa_set(1)
        mock_requests.get.assert_called_once_with(
            'http://submit.url/',
            params={'EnvelopeURL': 'http://nohost/col1/env1',
                    'f': 'pjson'}
        )


    def test_add_application_to_zope_object(self):
        manage_addRemoteRESTApplication(
            self.apps_folder,
            'restapp', 'title',
            'http://submit.url/', 'http://check.url/',
            'restapp'
        )
        self.assertEqual('restapp', self.apps_folder.Common.restapp.id)
        self.assertEqual('title', self.apps_folder.Common.restapp.title)
        self.assertEqual('restapp', self.apps_folder.Common.restapp.app_name)
        self.assertEqual('http://submit.url/', self.apps_folder.Common.restapp.ServiceSubmitURL)
        self.assertEqual('http://check.url/', self.apps_folder.Common.restapp.ServiceCheckURL)
        # asser defaults
        self.assertEqual(5, self.apps_folder.Common.restapp.nRetries)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_app_writes_success_in_event_log(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        exp = re.compile('\w+ job request for http:\/\/[\w+\/]+ successfully submited.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[1]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_for_new_job_invalid_status_code(self, mock_requests):
        mock_requests.get.return_value = Mock(status_code=201);
        self.create_cepaa_set(1)
        exp = re.compile('\w+ job request for http:\/\/[\w+\/]+ returned invalid status code 201.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[1]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_for_new_job_response_is_not_json(self, mock_requests):
        def bad_json():
            raise ValueError
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=bad_json
        );
        self.create_cepaa_set(1)
        exp = re.compile('\w+ job request for http:\/\/[\w+\/]+ response is not json.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[1]['event'], exp)
        exp = re.compile('\w+ job request for http:\/\/[\w+\/]+ response is invalid.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[2]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_for_new_job_invalid_json_response(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={})
        );
        self.create_cepaa_set(1)
        exp = re.compile('\w+ job request for http:\/\/[\w+\/]+ response is invalid.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[1]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_workitem_initialization(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 999, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        prop = self.app.col1.env1['0'].restapp
        assert prop['jobid'] == 999, 'wrong job id'
        assert prop['last_error'] is None, 'error not expected'
        assert type(prop['next_run']) == type(DateTime()), 'should be a date'

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_invalid_status_code(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(status_code=201);
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        exp = re.compile('\w+ job id 1 for http:\/\/[\w+\/]+ returned invalid status code 201.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[-3]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_invalid_json(self, mock_requests):
        def bad_json():
            raise ValueError
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=bad_json
        );
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        exp = re.compile('\w+ job id 1 for http:\/\/[\w+\/]+ output is not json.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[-4]['event'], exp)
        exp = re.compile('\w+ job id 1 for http:\/\/[\w+\/]+ output is invalid.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[-3]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_succeeded(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'jobId': 1, 'jobStatus': 'esriJobSucceeded',
                'messages': 'result messages',
                'results': {
                    'ResultZip': {
                        "value" : 'results/ResultZip'
                    }
                }
            }),

            content=(path(__file__).parent.abspath() / 'result.zip').bytes()
        );
        restapp = self.app.Applications.proc1.act1
        self.col1.env1.manage_addFeedback = Mock()
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        exp = re.compile('\w+ job id 1 for http:\/\/[\w+\/]+ successfully finished.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[-3]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_success_finishes_application(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'jobId': 1, 'jobStatus': 'esriJobSucceeded',
                'messages': 'result messages',
                'results': {
                    'ResultZip': {
                        "value" : 'results/ResultZip'
                    }
                }
            }),

            content=(path(__file__).parent.abspath() / 'result.zip').bytes()
        );
        self.col1.env1.manage_addFeedback = Mock()
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual('complete', self.col1.env1['0'].status)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_success_posts_feedback(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'jobId': 1, 'jobStatus': 'esriJobSucceeded',
                'messages': 'result messages',
                'results': {
                    'ResultZip': {
                        "value" : 'http://results/ResultZip'
                    }
                }
            }),

            content=(path(__file__).parent.abspath() / 'result.zip').bytes()
        );
        restapp = self.app.Applications.proc1.act1
        self.col1.env1.manage_addFeedback = Mock()
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        assert self.col1.env1.manage_addFeedback.call_count == 1
        call_args = self.col1.env1.manage_addFeedback.call_args[1]
        self.assertEqual('act1', call_args['activity_id'])
        self.assertEqual(1, call_args['automatic'])
        self.assertEqual('restapp results', call_args['title'])
        self.assertEqual(
            'The results for this assessment are attached to this feedback.',
            call_args.get('feedbacktext'))

    @patch.object(Converters, '_get_local_converters')
    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_success_attaches_zipfile_to_feedback(self, mock_requests, mock_local_converters):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.side_effect = [
            Mock(
                status_code=200,
                json=Mock(return_value={
                    'jobId': 1, 'jobStatus': 'esriJobSucceeded',
                    'messages': 'result messages',
                    'results': {
                        'ResultZip': {
                            "paramUrl" : 'results/ResultZip'
                        }
                    }
                })
            ),
            Mock(
                status_code=200,
                json=Mock(return_value={
                        'paramName': 'ResultZip',
                        'dataType': 'GPString',
                        'value' : 'http://test/\\server\\job\\scratch/result.zip'
                    }
                )
            ),
            Mock(
                status_code=200,
                content=(path(__file__).parent.abspath() / 'result.zip').bytes()
            ),
        ]
        restapp = self.app.Applications.proc1.act1
        CONVERTER_PARAMS = {
            'id': 'save_html',
            'title': 'safe html',
            'convert_url': 'convert/safe_html',
            'ct_input': '',
            'ct_output': '',
            'ct_schema': '',
            'ct_extraparams': '',
            'description': '',
            'suffix': ''
        }

        from Products.Reportek.Converter import Converter, LocalHttpConverter
        self.app.Converters = Mock()
        self.app.Converters.__getitem__ = Mock(
                return_value=Mock(convert=Mock(
                    return_value=Mock(text='safe html'))))
        self.col1.getEngine = Mock(return_value=Mock())
        self.col1.env1._invalidate_zip_cache = Mock()
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual(
            call('http://check.url/1/results/ResultZip', params={'f': 'pjson'}),
            mock_requests.get.mock_calls[-2])
        self.assertEqual(
            'http://test/server/job/scratch/result.zip',
            mock_requests.get.mock_calls[-1][1][0])
        self.assertEqual(
            call('http://test/server/job/scratch/result.zip'),
            mock_requests.get.mock_calls[-1])
        [feedback] = [item for item in self.col1.env1.objectValues()
                           if item.meta_type == 'Report Feedback']
        [attach] = feedback.objectValues()
        self.assertEqual('env1_results.zip', attach.__name__)
        self.assertEqual(
            (path(__file__).parent.abspath() / 'result.zip').bytes(),
            attach.data_file.open().read())

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_failure_posts_feedback(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobFailed',
                                    'messages': 'result fail messages'})
        );
        restapp = self.app.Applications.proc1.act1
        self.col1.env1.manage_addFeedback = Mock()
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        assert self.col1.env1.manage_addFeedback.call_count == 1
        call_args = self.col1.env1.manage_addFeedback.call_args[1]
        self.assertEqual('act1', call_args['activity_id'])
        self.assertEqual(1, call_args['automatic'])
        self.assertEqual('restapp results', call_args['title'])
        self.assertEqual(
            "Your delivery didn't pass validation.\n\n"
            "result fail messages",
            call_args.get('feedbacktext'))

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_failed(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobFailed',
                                    'messages': 'result fail messages'})
        );
        restapp = self.app.Applications.proc1.act1
        self.col1.env1.manage_addFeedback = Mock()
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        exp = re.compile('\w+ job id 1 for http:\/\/[\w+\/]+ failed.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[-3]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_fail_finishes_application(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobFailed',
                                    'messages': 'result fail messages'})
        );
        restapp = self.app.Applications.proc1.act1
        self.col1.env1.manage_addFeedback = Mock()
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual('complete', self.col1.env1['0'].status)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_not_done(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobExecuting'})
        );
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        exp = re.compile('\w+ job id 1 for http:\/\/[\w+\/]+ is still running.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[-1]['event'], exp)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_not_done_decreases_retries_left(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        workitem = self.app.col1.env1['0']
        self.assertEqual(5, workitem.restapp['retries_left'])
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobExecuting'})
        );
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual(4, workitem.restapp['retries_left'])

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_finished_when_no_retries_left(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        workitem = self.app.col1.env1['0']
        self.assertEqual(5, workitem.restapp['retries_left'])
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobExecuting'})
        );
        restapp = self.app.Applications.proc1.act1
        for idx in xrange(0,4):
            restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual(1, workitem.restapp['retries_left'])
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual('complete', self.col1.env1['0'].status)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_decrease_finishes_job_when_reaches_0(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        workitem = self.app.col1.env1['0']
        workitem.restapp['retries_left'] = 1
        restapp = self.app.Applications.proc1.act1.__of__(self.app.col1.env1)
        restapp._RemoteRESTApplication__decrease_retries(workitem, self.app.REQUEST)
        self.assertEqual(0, workitem.restapp['retries_left'])
        self.assertEqual('complete', self.col1.env1['0'].status)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_activity_is_found_by_cron_job(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        self.ReportekEngine = ReportekEngine().__of__(self.app)
        workitem = self.app.col1.env1['0']
        self.assertEqual(5, workitem.restapp['retries_left'])
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobExecuting'})
        );
        self.app.Catalog = MagicMock(return_value=[Mock()], getobject=lambda x: workitem)
        self.assertEqual(5, workitem.restapp['retries_left'])
        self.ReportekEngine.runAutomaticApplications(p_applications='AutomaticQA||act1')
        self.assertEqual(4, workitem.restapp['retries_left'])

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_unknown_status(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'unknown status'})
        );
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        exp = re.compile('\w+ job id 1 for http:\/\/[\w+\/]+ has status [\w+\s]+.$')
        self.assertRegexpMatches(self.app.col1.env1['0'].event_log[-1]['event'], exp)
        workitem = self.app.col1.env1['0']
        self.assertEqual(4, workitem.restapp['retries_left'])

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_invalid_json_finishes_activity(self, mock_requests):
        def bad_json():
            raise ValueError
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=bad_json
        );
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual('complete', self.col1.env1['0'].status)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_invalid_status_code_finishes_activity(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        self.create_cepaa_set(1)
        mock_requests.get.return_value = Mock(status_code=201);
        restapp = self.app.Applications.proc1.act1
        restapp.__of__(self.app.col1.env1).callApplication('0', self.app.REQUEST)
        self.assertEqual('complete', self.col1.env1['0'].status)
