import datetime
import json
import logging
import requests
import tempfile
from requests.exceptions import RequestException
from DateTime import DateTime

from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile as ptf
from Products.Reportek.RepUtils import RemoteApplicationException
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from OFS.SimpleItem import SimpleItem
from ZODB.PersistentMapping import PersistentMapping

FEEDBACKTEXT_LIMIT = 1024 * 16  # 16KB

logger = logging.getLogger("Reportek")

manage_addRemoteRESTAPIApplicationForm = ptf('zpt/remote/restapi_app_add',
                                             globals())


def manage_addRemoteRESTAPIApplication(self, id='', title='', base_url='',
                                       async_base_url='', jobs_endpoint='',
                                       batch_endpoint='',
                                       qascripts_endpoint='', app_name='',
                                       token='', REQUEST=None):
    """Generic base application that calls a remote service."""

    ob = RemoteRESTAPIApplication(id, title, base_url, async_base_url,
                                  jobs_endpoint, batch_endpoint,
                                  qascripts_endpoint, app_name, token)
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
                 batch_endpoint, qascripts_endpoint, app_name, token='',
                 timeout=20, retries=5, r_frequency=300):
        """Initialize a new instance of RemoteRESTAPIApplication."""
        self.id = id
        self.title = title
        self.base_url = base_url
        self.async_base_url = async_base_url
        self.jobs_endpoint = jobs_endpoint
        self.batch_endpoint = batch_endpoint
        self.qascripts_endpoint = qascripts_endpoint
        self.app_name = app_name
        self.token = token
        self.retries = int(retries)
        self.timeout = int(timeout)
        self.r_frequency = int(r_frequency)

    def manage_settings(self, title, base_url, async_base_url, jobs_endpoint,
                        batch_endpoint, qascripts_endpoint, app_name, token,
                        retries, timeout, r_frequency, REQUEST):
        """Change the settings of the RemoteRESTAPIApplication."""
        self.title = title
        self.base_url = base_url
        self.async_base_url = async_base_url
        self.jobs_endpoint = jobs_endpoint
        self.batch_endpoint = batch_endpoint
        self.qascripts_endpoint = qascripts_endpoint
        self.app_name = app_name
        self.token = token
        self.retries = int(retries)
        self.timeout = int(timeout)
        self.r_frequency = int(r_frequency)

        if REQUEST is not None:
            return self.manage_settings_html(
                manage_tabs_message='Saved changes.'
            )

    def do_feedback_cleanup(self, envelope, s_title=None):
        """Deletes all previous feedbacks created by this application."""
        for l_item in envelope.objectValues('Report Feedback'):
            do_delete = not s_title or (s_title and
                                        s_title in getattr(l_item, 'title', ''))
            if l_item.activity_id == self.app_name and do_delete:
                envelope.manage_delObjects(l_item.id)

    def log_event(self, evt_type, evt_msg, workitem=None):
        """Logs events. If workitem is provided addEvent on workitem too."""
        evt_types = ["debug", "info", "warning", "error", "exception",
                     "critical", "log"]
        if evt_type in evt_types:
            getattr(logger, evt_type)(evt_msg)
        if workitem:
            workitem.addEvent(evt_msg)

    def do_api_request(self, url, method='get', data=None, cookies=None,
                       headers=None, params=None):
        """Call requests methods and return a dictionary with data and error
           keys.
        """
        api_req = requests.get
        jsondata = None
        error = None
        if method == 'post':
            api_req = requests.post

        if self.token:
            headers['Authorization'] = self.token
        try:
            response = api_req(url, data=data, cookies=cookies,
                               headers=headers, params=params, verify=False,
                               timeout=self.timeout)
        except RequestException as e:
            error = str(e)

        if not error:
            try:
                jsondata = response.json()
            except ValueError as e:
                error = "Unable to convert QA Service response"\
                        " to JSON: {}. HTTP Code:"\
                        " {} ({})".format(str(e), response.status_code,
                                          response.reason)

            if jsondata:
                if isinstance(jsondata, dict):
                    error = jsondata.get('errorMessage')
                if response.status_code != requests.codes.ok or error:
                    error = 'HTTP Code: {} ({}) - {}'.format(response.status_code,
                                                             response.reason,
                                                             error)

        return dict(data=jsondata, error=error)

    def add_async_qajob(self, workitem, failed_job):
        """Submit asynchronous qa job"""
        async_qa_url = '/'.join([self.async_base_url,
                                 self.jobs_endpoint.strip('/')])
        file_src = failed_job.get('fileUrl')
        script_id = failed_job.get('scriptId')
        jobid = failed_job.get('jobId')
        data = {
            "sourceUrl": file_src,
            "scriptId": script_id
        }
        data = json.dumps(data)
        ctype = "application/json"
        headers = {"Accept": ctype,
                   "Content-Type": ctype}

        result = self.do_api_request(async_qa_url, method='post', data=data,
                                     headers=headers)
        err = result.get('error')
        jsondata = result.get('data')

        if err:
            err_msg = 'Script ID: {} for file {},'\
                      ' failed: ({})'.format(script_id, file_src, err)
            failed_job['last_error'] = err_msg
            self.update_retries(workitem, jobid=jobid)
            if failed_job.get('retries') == 0:
                self.mark_failed(workitem, job)
                self.update_job(workitem, failed_job)
        else:
            return jsondata

    def add_async_batch_qajob(self, workitem, env_url):
        """Submit envelope level batch job for analysis."""
        async_batch_url = '/'.join([self.async_base_url,
                                    self.jobs_endpoint.strip('/'),
                                    self.batch_endpoint.strip('/')])
        data = {
            "envelopeUrl": env_url
        }
        data = json.dumps(data)
        ctype = "application/json"
        headers = {"Accept": ctype,
                   "Content-Type": ctype}

        result = self.do_api_request(async_batch_url, method='post', data=data,
                                     headers=headers)
        err = result.get('error')
        jsondata = result.get('data')

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
                workitem.failure = True
        else:
            return jsondata

    def get_analysis_meta(self, workitem):
        """Return analysis metadata."""
        qa_data = getattr(workitem, self.app_name, {})
        return qa_data.get('analysis')

    def get_job_meta(self, workitem, jobid):
        """Return job metadata."""
        qa_data = getattr(workitem, self.app_name)
        jobs_meta = qa_data.get('jobs', {})
        return jobs_meta.get(jobid)

    def persist_meta(self, workitem):
        """Persist the changes to the metadata."""
        qa_data = getattr(workitem, self.app_name)
        qa_data._p_changed = 1

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
        self.init_wk(workitem)
        if not REQUEST or REQUEST and not getattr(REQUEST, 'failed_qa_only', None):
            self.do_feedback_cleanup(envelope)
        else:
            self.manage_previously_failed_jobs(workitem, envelope)
            self.check_if_blocked(workitem, envelope)
        self.update_retries(workitem)
        self.callApplication(workitem_id, REQUEST)

    def check_if_blocked(self, workitem, envelope):
        """Checks if remaining feedbacks are blockers"""
        fbs = envelope.objectValues('Report Feedback')
        for fb in fbs:
            if getattr(fb, 'feedback_status', '') == 'BLOCKER' and not workitem.blocker:
                workitem.blocker = True

    def manage_previously_failed_jobs(self, workitem, envelope):
        """Adds previously failed QA jobs in the wk prop."""
        failed_jobs = self.get_failed_jobs(envelope)
        if failed_jobs:
            for job in failed_jobs:
                self.do_feedback_cleanup(envelope,
                                         s_title=job.get('scriptTitle'))
                job_id = '_'.join(['', job.get('scriptId'), job.get('fileUrl')])
                job['jobId'] = job_id
                self.add_job(workitem, job)

    def handle_failed_job(self, workitem, job):
        result = self.add_async_qajob(workitem, job)
        if result:
            l_wk_prop = getattr(workitem, self.app_name)
            del l_wk_prop['jobs'][job.get('jobId')]
            msg = '{} - Previously failed job submitted: {}'\
                  ' for file: {}'.format(self.app_name, job.get('scriptTitle'),
                                         job.get('fileUrl'))
            self.log_event('info', msg, workitem)
            job['jobId'] = result.get('jobId')
            job['status'] = 'Pending'

            self.add_job(workitem, job)

    def update_scripts_data(self, workitem, file_id, script_title, status):
        """Updates the status of the script with script_title."""
        l_wk_prop = getattr(workitem, self.app_name)
        envelope = workitem.getMySelf()
        schemas = []

        if file_id == 'xml':
            schemas = envelope.dataflow_uris
        else:
            file = envelope.restrictedTraverse(str(file_id))
            schemas = [getattr(file, 'xml_schema_location')]

        for schema in schemas:
            script_data = l_wk_prop['scripts'][schema]
            for script_id in script_data:
                if script_data[script_id].get('script_title') == script_title:
                    script_data[script_id]['status'] = status

    def file_has_been_modified(self, envelope, qa_wk_id, fileurl):
        """Returns True if the file has been modified since last Automatic QA"""
        filename = fileurl.split('/')[-1]
        filename = filename.encode('utf-8')
        log = getattr(envelope, 'activation_log', [])
        qa_end = envelope.reportingdate
        try:
            qa_log = log[int(qa_wk_id)]
            qa_end = DateTime(datetime.datetime.fromtimestamp(qa_log.get('end')))
        except Exception:
            pass

        if filename != 'xml':
            file = envelope.restrictedTraverse(filename, None)
            if file:
                if file.upload_time() < qa_end:
                    return False
        return True

    def get_failed_jobs(self, envelope):
        """Return a list of failed QA jobs."""
        QA_workitems = envelope.get_qa_workitems()
        failed_jobs = []
        if QA_workitems:
            qa = QA_workitems[-2]
            last_qa_wk_prop = getattr(qa, self.app_name)
            jobs = last_qa_wk_prop.get('jobs', [])
            for jobid, job in jobs.iteritems():
                if job.get('status') == 'Failed' or self.file_has_been_modified(envelope, qa.id, job.get('fileUrl')):
                    failed_jobs.append({
                        'fileUrl': job.get('fileUrl'),
                        'scriptId': job.get('scriptId'),
                        'scriptTitle': job.get('scriptTitle'),
                        'retries': self.retries
                    })

        return failed_jobs

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
            else:
                qa_data['analysis']['last_error'] = None

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
            self.persist_meta(workitem)

    def manage_analysis(self, workitem, analysis, REQUEST=None):
        """Handle analysis results."""
        if analysis:
            jobs = analysis.get('jobs')
            for job in jobs:
                self.add_job(workitem, job)

    def mark_failed(self, workitem, job):
        jobid = job.get('jobId')
        err_msg = '{} - Giving up on job: #{}, '\
                  'due to: {}'.format(self.app_name,
                                      jobid, job.get('last_error'))
        self.log_event('error', err_msg, workitem)
        job['status'] = 'Failed'
        workitem.failure = True

    def add_job(self, workitem, job):
        """Add a new job in the automatic property mapping."""
        qa_data = getattr(workitem, self.app_name)
        qa_data['jobs'][job.get('jobId')] = job
        qa_data['jobs'][job.get('jobId')]['retries'] = self.retries
        file = job.get('fileUrl').split('/')[-1]
        msg = '{} - job in progress: #{} for file: {}'.format(self.app_name,
                                                              job.get('jobId'),
                                                              file)
        self.persist_meta(workitem)
        if job.get('jobId', '').startswith('_'):
            msg = '{} - Previously failed job in progress: {}'\
                  ' for file: {}'.format(self.app_name,
                                         job.get('scriptTitle'),
                                         file)
        self.log_event('info', msg, workitem)

    def update_job(self, workitem, job):
        """Update the job in the automatic property mapping."""
        qa_data = getattr(workitem, self.app_name)
        qa_data['jobs'][job.get('jobId')].update(job)
        self.persist_meta(workitem)

    def manage_jobs(self, workitem, REQUEST=None):
        """Manage the remote jobs."""
        qa_data = getattr(workitem, self.app_name)
        jobs = qa_data.get('jobs', [])
        for jobid, job in jobs.iteritems():
            t_threshold = True
            if job.get('next_run'):
                t_threshold = DateTime() >= DateTime(int(job['next_run']))
            submitted = not job.get('jobId', '').startswith('_')
            skip = job.get('status') == 'Ready' or job.get('retries') == 0
            if t_threshold and not skip:
                if submitted:
                    result = self.get_job_result(workitem, job)
                    self.manage_results(workitem, job, result, REQUEST)
                else:
                    self.handle_failed_job(workitem, job)

    def get_job_result(self, workitem, job):
        """Get the remote result for the current jobid."""
        jobid = job.get('jobId')
        file = job.get('fileUrl').split('/')[-1]
        job_url = '/'.join([self.async_base_url,
                            self.jobs_endpoint.strip('/'),
                            str(jobid)])
        ctype = "application/json"
        headers = {"Accept": ctype,
                   "Content-Type": ctype}

        result = self.do_api_request(job_url, method='get', headers=headers)
        err = result.get('error')
        jsondata = result.get('data')

        if err:
            err_msg = 'Job: #{} for file {},'\
                      ' failed: ({})'.format(jobid, file, err)
            job['last_error'] = err_msg
            self.update_retries(workitem, jobid=jobid)
            if job.get('retries') == 0:
                self.mark_failed(workitem, job)
                self.update_job(workitem, job)
        else:
            return jsondata

    def manage_results(self, workitem, job, result, REQUEST=None):
        """Manage a QA job result."""
        if result:
            status = result.get('executionStatus')
            status_id = status.get('statusId')
            jobid = job.get('jobId')
            job['status'] = status.get('statusName')
            job['last_error'] = None
            filename = job.get('fileUrl').split('/')[-1]
            if status_id == '0':
                env = workitem.getMySelf()
                fb_id = '{0}_{1}'.format(self.app_name, jobid)
                script_title = result.get('scriptTitle')
                fb_title = '{} result for: {} - {}'.format(self.app_name,
                                                           filename,
                                                           script_title)
                data = {
                    'jobid': jobid,
                    'fb_content': result.get('feedbackContent'),
                    'fb_content_type': result.get('feedbackContentType'),
                    'fb_message': result.get('feedbackMessage'),
                    'fb_status': result.get('feedbackStatus')
                }

                fb_attrs = {
                    'id': fb_id,
                    'title': fb_title,
                    'activity_id': workitem.activity_id,
                    'automatic': 1,
                    'document_id': filename,
                }
                data['fb_attrs'] = fb_attrs

                self.add_feedback(env, data, workitem)

                if result['feedbackStatus'] == 'BLOCKER':
                    workitem.blocker = True

                info = '{} - job completed: #{} - {}'.format(self.app_name,
                                                             jobid,
                                                             script_title)
                self.log_event('info', info, workitem)
            else:
                job['last_error'] = result.get('feedbackMessage')
                self.update_retries(workitem, jobid=jobid)
                if job.get('retries') == 0:
                    err_msg = 'Job: #{} for file {},'\
                      ' failed: ({})'.format(jobid, filename, job['last_error'])
                    job['last_error'] = err_msg
                    self.mark_failed(workitem, job)
            self.update_job(workitem, job)

    def add_feedback(self, env, data, workitem):
        """Add an AutomaticQA feedback."""
        fb_attrs = data.get('fb_attrs')
        try:
            env.manage_addFeedback(**fb_attrs)
        except Exception as e:
            err_msg = 'Unable to create feedback: {}'.format(str(e))
            self.log_event('error', err_msg, workitem)
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
        fb_ob.feedback_status = data.get('fb_status', '')

    def finish(self, workitem_id, REQUEST=None):
        self.activateWorkitem(workitem_id, actor='openflow_engine')
        self.completeWorkitem(workitem_id, actor='openflow_engine', REQUEST=REQUEST)

    def get_schema_qa_scripts(self, schema):
        """Returns the list of QA script ids available for a schema."""
        qascripts_url = '/'.join([self.base_url,
                            self.qascripts_endpoint.strip('/')])
        ctype = "application/json"
        headers = {"Accept": ctype,
                   "Content-Type": ctype}
        params = None
        if schema:
            params = {
                'schema': schema
            }
        result = self.do_api_request(qascripts_url, method='get',
                                     headers=headers, params=params)
        err = result.get('error')
        jsondata = result.get('data')

        if err:
            err_msg = 'Unable to retrieve QAScripts for schema: {}'\
                      ' due to: {}'.format(schema, err)
            self.log_event('error', err_msg)
            return []
        else:
            return jsondata

    def get_qa_scripts_short(self, schema):
        """Return a list of script ids for the specified schema."""
        scripts = self.get_schema_qa_scripts(schema)
        if scripts:
            scripts = [[script.get('id'),
                        script.get('name'), '',
                        script.get('runOnDemandMaxFileSizeMB')
                        ]for script in scripts]

        return scripts

    def get_qa_scripts(self, schema):
        """Return a list of script ids for the specified schema."""
        scripts = self.get_schema_qa_scripts(schema)
        result = []
        for script in scripts:
            result.append({
                'description': script.get('description'),
                'xml_schema': script.get('schemaUrl'),
                'content_type_out': script.get('outputType')
            })

        return result

    def run_remote_qascript(self, file_url, script_id):
        """Run remote synchronous QA Script."""
        jobs_url = '/'.join([self.base_url,
                             self.jobs_endpoint.strip('/')])
        data = {
            "sourceUrl": file_url,
            "scriptId": script_id
        }
        data = json.dumps(data)
        ctype = "application/json"
        headers = {"Accept": ctype,
                   "Content-Type": ctype}

        result = self.do_api_request(jobs_url, method='post', headers=headers,
                                     data=data)
        err = result.get('error')
        jsondata = result.get('data')

        if err:
            err_msg = 'QA script {} for {}'\
                      ' failed: ({})'.format(file_url, script_id, err)
            self.log_event('error', err_msg)
            raise RemoteApplicationException(err_msg)
        else:
            return jsondata


InitializeClass(RemoteRESTAPIApplication)
