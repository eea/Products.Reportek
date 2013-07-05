import unittest
from mock import Mock, patch

from Products.Reportek.RemoteRESTApplication import RemoteRESTApplication

class RemoteRESTAppTestCase(unittest.TestCase):

    def test_init(self):
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url', 'name')
        self.assertEqual('restapp', restapp.id)
        self.assertEqual('title', restapp.title)
        self.assertEqual('http://submit.url', restapp.ServiceSubmitURL)
        self.assertEqual('http://check.url', restapp.ServiceCheckURL)
        self.assertEqual('http://check.url', restapp.ServiceCheckURL)
        # asser defaults
        self.assertEqual(5, restapp.nRetries)
        self.assertEqual(300, restapp.retryFrequency)
        self.assertEqual(60, restapp.nTimeBetweenCalls)

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_for_new_job_success(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSubmitted'})
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url', 'name')
        restapp('http://envelope.url')
        mock_requests.get.assert_called_once_with(
            'http://submit.url',
            params={'EnvelopeURL': 'http://envelope.url',
                    'f': 'pjson'}
        )

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_for_new_job_invalid_status_code(self, mock_requests):
        mock_requests.get.return_value = Mock(status_code=201);
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url', 'name')
        with self.assertRaisesRegexp(Exception, 'invalid status code'):
            restapp('http://envelope.url')

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_for_new_job_response_is_not_json(self, mock_requests):
        def bad_json():
            raise ValueError
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=bad_json
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url', 'name')
        with self.assertRaisesRegexp(Exception, 'response is not json'):
            restapp('http://envelope.url')

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_for_new_job_invalid_json_response(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={})
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url', 'name')
        with self.assertRaisesRegexp(Exception, 'invalid response'):
            restapp('http://envelope.url')

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_request_job_output_params(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSucceeded',
                                    'messages': []})
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url/', 'name')
        restapp.get('1')
        mock_requests.get.assert_called_once_with(
            'http://check.url/1',
            params={'f': 'pjson'}
        )

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_invalid_status_code(self, mock_requests):
        mock_requests.get.return_value = Mock(status_code=201);
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url/', 'name')
        with self.assertRaisesRegexp(Exception, 'invalid status code'):
            restapp.get('1')

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_invalid_json(self, mock_requests):
        def bad_json():
            raise ValueError
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=bad_json
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url/', 'name')
        with self.assertRaisesRegexp(Exception, 'response is not json'):
            restapp.get('1')

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_succeeded(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobSucceeded',
                                    'messages': 'result messages'})
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url/', 'name')
        self.assertEqual('result messages', restapp.get('1'))

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_failed(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobFailed'})
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url/', 'name')
        with self.assertRaisesRegexp(Exception, 'job failed'):
            restapp.get('1')

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_not_done(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'esriJobExecuting'})
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url/', 'name')
        with self.assertRaisesRegexp(Exception, 'job not done'):
            restapp.get('1')

    @patch('Products.Reportek.RemoteRESTApplication.requests')
    def test_job_unknown_status(self, mock_requests):
        mock_requests.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'jobId': 1, 'jobStatus': 'unknown status'})
        );
        restapp = RemoteRESTApplication('restapp', 'title', 'http://submit.url',
                                        'http://check.url/', 'name')
        with self.assertRaisesRegexp(Exception, 'unknown status'):
            restapp.get('1')
