import json
import logging
import requests
import tempfile
from requests.exceptions import RequestException
from DateTime import DateTime

from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile as ptf
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from OFS.SimpleItem import SimpleItem
from ZODB.PersistentMapping import PersistentMapping

FEEDBACKTEXT_LIMIT = 1024 * 16 # 16KB

logger = logging.getLogger("Reportek")

manage_addRemoteRESTAPIApplicationForm = ptf('zpt/remote/restapi_app_add',
                                             globals())


def manage_addRemoteRESTAPIApplication(self, id='', title='', base_url='',
                                       async_base_url='', jobs_endpoint='',
                                       batch_endpoint='', app_name='',
                                       REQUEST=None):
    """Generic base application that calls a remote service."""

    ob = RemoteRESTAPIApplication(id, title, base_url, async_base_url,
                                  jobs_endpoint, batch_endpoint, app_name)
    self._setObject(id, ob)

    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class RemoteRESTAPIApplication(SimpleItem):
    """RemoteRESTAPIApplication Class."""
    security = ClassSecurityInfo()
    meta_type = 'Remote REST API Application'
    manage_options = (
        ({'label': 'Settings', 'action': 'manage_settings_html'},) +
        SimpleItem.manage_options
    )

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = ptf('zpt/remote/restapi_app_edit', globals())

    def __init__(self, id, title, base_url, async_base_url, jobs_endpoint,
                 batch_endpoint, app_name, timeout=20, retries=5,
                 r_frequency=300):
        """Initialize a new instance of RemoteRESTAPIApplication."""
        self.id = id
        self.title = title
        self.base_url = base_url
        self.async_base_url = async_base_url
        self.jobs_endpoint = jobs_endpoint
        self.batch_endpoint = batch_endpoint
        self.app_name = app_name
        self.retries = int(retries)
        self.timeout = int(timeout)
        self.r_frequency = int(r_frequency)

    def manage_settings(self, title, base_url, async_base_url, jobs_endpoint,
                        batch_endpoint, app_name, retries, timeout,
                        r_frequency, REQUEST):
        """Change the settings of the RemoteRESTAPIApplication."""
        self.title = title
        self.base_url = base_url
        self.async_base_url = async_base_url
        self.jobs_endpoint = jobs_endpoint
        self.batch_endpoint = batch_endpoint
        self.app_name = app_name
        self.retries = int(retries)
        self.timeout = int(timeout)
        self.r_frequency = int(r_frequency)

        if REQUEST is not None:
            return self.manage_settings_html(
                manage_tabs_message='Saved changes.'
            )

    def do_feedback_cleanup(self, envelope):
        """Deletes all previous feedbacks created by this application."""
        for l_item in envelope.objectValues('Report Feedback'):
            if l_item.activity_id == self.app_name:
                envelope.manage_delObjects(l_item.id)

    def log_event(self, evt_type, evt_msg, workitem=None):
        """Logs events. If workitem is provided addEvent on workitem too."""
        evt_types = ["debug, info, warning, error, exception, critical, log"]
        if evt_type in evt_types:
            getattr(logger, evt_type)(evt_msg)
        if workitem:
            workitem.addEvent(evt_msg)

    def add_async_batch_qajob(self, workitem, env_url):
        """Submit envelope level batch job for analysis."""
        foo = 'http://converters-api.devel1.eionet.europa.eu/restapi1'
        async_batch_url = '/'.join([foo,
                                    # self.async_base_url,
                                    self.jobs_endpoint.strip('/'),
                                    self.batch_endpoint.strip('/')])
        data = {
            "envelopeUrl": env_url
        }
        data = json.dumps(data)
        ctype = "application/json"
        headers = {"Accept": ctype,
                   "Content-Type": ctype}
        result = None
        err = None
        try:
            result = requests.post(async_batch_url, data=data,
                                   headers=headers, timeout=self.timeout)
        except RequestException as e:
            err = str(e)
        if result:
            jsondata = result.json()
            if result.status_code == 200:
                return jsondata
            else:
                err = '{} {}'.format(result.status_code,
                                     jsondata.get('errorMessage'))
        elif hasattr(result, 'status_code'):
            err = 'A {} HTTP error occured.'.format(result.status_code)
        else:
            err = 'Envelope analysis query returned no result.'

        if err:
            err_msg = 'Envelope analysis job for {}'\
                      ' failed: ({})'.format(env_url, err)
            analysis = self.get_analysis_meta(workitem)
            analysis['last_error'] = err_msg
            self.update_retries(workitem)
            if analysis.get('retries') == 0:
                err_msg = '{} - Giving up on envelope analysis, '\
                          'due to: {}'.format(self.app_name, err_msg)
                self.log_event('error', err_msg, workitem)

    def get_analysis_meta(self, workitem):
        """Return analysis metadata."""
        qa_data = getattr(workitem, self.app_name, {})
        return qa_data.get('analysis')

    def get_job_meta(self, workitem, jobid):
        """Return job metadata."""
        qa_data = getattr(workitem, self.app_name)
        jobs_meta = qa_data.get('jobs', {})
        return jobs_meta.get(jobid)

    def init_wk(self, workitem):
        """Adds QA-specific extra properties to the workitem."""
        default_meta = {
            'last_error': None,
        }
        qa_data = PersistentMapping()
        qa_data['analysis'] = default_meta
        qa_data['jobs'] = {}
        setattr(workitem, self.app_name, qa_data)

    security.declareProtected('Use OpenFlow', '__call__')
    def __call__(self, workitem_id, REQUEST=None):
        """ Runs the Remote Aplication for the first time """
        workitem = getattr(self, workitem_id)
        envelope = workitem.getMySelf()
        self.do_feedback_cleanup(envelope)
        self.init_wk(workitem)
        self.update_retries(workitem)
        self.callApplication(workitem_id, REQUEST)

    def get_running_jobs(self, workitem):
        """Return true if this QA is done."""
        qa_data = getattr(workitem, self.app_name)
        jobs = qa_data.get('jobs')
        still_running = [job for job in jobs.keys()
                         if jobs[job].get('retries') != 0 and
                         jobs[job].get('status') != 'Ready']
        return still_running

    security.declareProtected('Use OpenFlow', 'callApplication')
    def callApplication(self, workitem_id, REQUEST=None):
        """Called on a regular basis"""
        workitem = getattr(self, workitem_id)
        result = self.do_analysis(workitem, REQUEST)
        self.manage_analysis(workitem, result, REQUEST)
        self.manage_jobs(workitem, REQUEST)
        analysis = self.get_analysis_meta(workitem)
        analysis_done = analysis['last_error'] == None or analysis['retries'] == 0
        if not self.get_running_jobs(workitem) and analysis_done:
            self.finish(workitem.id, REQUEST)

    def do_analysis(self, workitem, REQUEST=None):
        """Analyse the envelope."""
        qa_data = getattr(workitem, self.app_name)
        t_threshold = DateTime() >= DateTime(int(qa_data['analysis']['next_run']))
        if not qa_data.get('jobs') and t_threshold:
            envelope = workitem.getMySelf()
            env_url = envelope.absolute_url(0)
            batch_res = self.add_async_batch_qajob(workitem, env_url)
            if not batch_res:
                self.update_retries(workitem, REQUEST)
            return batch_res

    def update_retries(self, workitem, jobid=None, REQUEST=None):
        """Update the retries and next_run metadata."""
        data = self.get_analysis_meta(workitem)
        if jobid:
            data = self.get_job_meta(workitem, jobid)
        if data:
            if not data.get('retries'):
                data['retries'] = self.retries
            else:
                data['retries'] -= 1
            if not data.get('next_run'):
                data['next_run'] = DateTime()
            else:
                next_run = int(data['next_run'])
                next_run = DateTime(next_run + int(self.r_frequency))
                data['next_run'] = next_run

    def manage_analysis(self, workitem, analysis, REQUEST=None):
        """Handle analysis results."""
        if analysis:
            jobs = analysis.get('jobs')
            for job in jobs:
                self.add_job(workitem, job)

    def add_job(self, workitem, job):
        """Add a new job in the automatic property mapping."""
        qa_data = getattr(workitem, self.app_name)
        qa_data['jobs'][job.get('jobId')] = job
        qa_data['jobs'][job.get('jobId')]['retries'] = self.retries
        file = job.get('fileUrl').split('/')[-1]
        msg = '{} - job in progress: #{} for file: {}'.format(self.app_name,
                                                            job.get('jobId'),
                                                            file)
        self.log_event('info', msg, workitem)

    def update_job(self, workitem, job):
        """Update the job in the automatic property mapping."""
        qa_data = getattr(workitem, self.app_name)
        qa_data['jobs'][job.get('jobId')].update(job)

    def manage_jobs(self, workitem, REQUEST=None):
        """Manage the remote jobs."""
        qa_data = getattr(workitem, self.app_name)
        jobs = qa_data.get('jobs', [])
        for jobid, job in jobs.iteritems():
            t_threshold = True
            if job.get('next_run'):
                t_threshold = DateTime() >= DateTime(int(job['next_run']))
            skip = job.get('status') == 'Ready' or job.get('retries') == 0
            if t_threshold and not skip:
                result = self.get_job_result(workitem, job)
                self.manage_results(workitem, job, result, REQUEST)

    def get_job_result(self, workitem, job):
        """Get the remote result for the current jobid."""
        jobid = job.get('jobId')
        file = job.get('fileUrl').split('/')[-1]
        # foo = 'http://converters-api.devel1.eionet.europa.eu/restapi1'
        job_url = '/'.join([self.async_base_url,
                            self.jobs_endpoint.strip('/'),
                            jobid])
        headers = {"Accept": "application/json"}
        result = None
        err = None

        try:
            result = requests.get(job_url, headers=headers,
                                  timeout=self.timeout)
        except RequestException as e:
            err = str(e)
        if result:
            jsondata = result.json()
            if result.status_code == 200:
                return jsondata
            else:
                err = '{} {}'.format(result.status_code,
                                     jsondata.get('errorMessage'))
        elif hasattr(result, 'status_code'):
            err = 'A {} HTTP error occured.'.format(result.status_code)
        else:
            err = 'Job query returned no result.'

        if err:
            err_msg = 'Job: #{} for file {},'\
                      ' failed: ({})'.format(jobid, file, err)
            job['last_error'] = err_msg
            self.update_retries(workitem, jobid=jobid)
            if job.get('retries') == 0:
                err_msg = '{} - Giving up on job: #{}, '\
                          'due to: {}'.format(self.app_name, jobid, err_msg)
                self.log_event('error', err_msg, workitem)

    def manage_results(self, workitem, job, result, REQUEST=None):
        """Manage a QA job result."""
        if result:
            status = result.get('executionStatus')
            status_id = status.get('statusId')
            jobid = job.get('jobId')
            job['status'] = status.get('statusName')
            job['last_error'] = None
            if status_id == '0':
                env = workitem.getMySelf()
                fb_id = '{0}_{1}'.format(self.app_name, jobid)
                filename = job.get('fileUrl').split('/')[-1]
                script_title = result.get('scriptTitle')
                fb_title = '{} result for: {} - {}'.format(self.app_name,
                                                           filename,
                                                           script_title)
                data = {
                    'jobid': jobid,
                    'fb_content': result.get('feedbackContent'),
                    'fb_content_type': result.get('feedbackContentType'),
                    'fb_message': result.get('feedbackMessage'),
                }

                fb_attrs = {
                    'id': fb_id,
                    'title': fb_title,
                    'activity_id': workitem.activity_id,
                    'automatic': 1,
                    'document_id': filename,
                    'feedback_status': result.get('feedbackStatus', '')
                }
                data['fb_attrs'] = fb_attrs

                self.add_feedback(env, data)

                if result['feedbackStatus'] == 'BLOCKER':
                    workitem.blocker = True
                    info = '{} - job completed: #{} - {}'.format(self.app_name,
                                                                 jobid,
                                                                 script_title)
                self.log_event('info', info, workitem)
            else:
                job['last_error'] = result.get('feedbackMessage')
                self.update_retries(workitem, jobid=jobid)

            self.update_job(workitem, job)

    def add_feedback(self, env, data):
        """Add an AutomaticQA feedback."""
        fb_attrs = data.get('fb_attrs')
        env.manage_addFeedback(**fb_attrs)
        fb_ob = env.restrictedTraverse(fb_attrs.get('id'))

        fb_content = data.get('fb_content')
        fb_content_type = data.get('fb_content_type')
        fb_message = data.get('fb_message')
        if len(fb_content) > FEEDBACKTEXT_LIMIT:
            with tempfile.TemporaryFile() as tmp:
                tmp.write(fb_content.encode('utf-8'))
                tmp.seek(0)
                fb_ob.manage_uploadFeedback(tmp, filename='qa-output')
            fb_attach = fb_ob.objectValues()[0]
            fb_attach.data_file.content_type = fb_content_type
            fb_ob.feedbacktext = (
                'Feedback too large for inline display; '
                '<a href="qa-output/view">see attachment</a>.')
            fb_ob.content_type = 'text/html'

        else:
            fb_ob.feedbacktext = fb_content
            fb_ob.content_type = fb_content_type

        fb_ob.message = fb_message

    def finish(self, workitem_id, REQUEST=None):
        self.activateWorkitem(workitem_id, actor='openflow_engine')
        self.completeWorkitem(workitem_id, actor='openflow_engine', REQUEST=REQUEST)


InitializeClass(RemoteRESTAPIApplication)
