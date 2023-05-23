# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is Reportek version 1.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel and Eau de Web are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Miruna Badescu, Eau de Web

# RemoteApplication
#

import json
import logging
import string
import tempfile
import urllib
import uuid

import requests
import requests.exceptions
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from DateTime import DateTime
from Document import Document
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.BaseRemoteApplication import BaseRemoteApplication
from Products.Reportek.interfaces import IQAApplication
from Products.Reportek.rabbitmq import send_message_nodqueue
from zope.interface import implements

feedback_log = logging.getLogger(__name__ + '.feedback')

FEEDBACKTEXT_LIMIT = 1024 * 16  # 16KB


manage_addRRMQQAApplicationForm = PageTemplateFile(
    'zpt/remote/application_add_rabbitmq_qa',
    globals())


def manage_addRRMQQAApplication(self, id='', title='', qarequests='',
                                qajobs='', qadeadletter='',
                                app_name='', qaserver='', token='',
                                REQUEST=None):
    """ Generic application that calls a remote service
    """

    ob = RemoteRabbitMQQAApplication(id, title, qarequests, qajobs,
                                     qadeadletter, qaserver, token, app_name)
    self._setObject(id, ob)

    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class RemoteRabbitMQQAApplication(BaseRemoteApplication):
    """ RabbitMQ QA Application
    """

    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()
    implements(IQAApplication)
    meta_type = 'Remote RabbitMQ QA Application'

    manage_options = (({'label': 'Settings',
                        'action': 'manage_settings_html'},) +
                      SimpleItem.manage_options
                      )

    def __init__(self, id, title, qarequests, qajobs,
                 qadeadletter, qaserver, token, app_name, requestTimeout=5):
        """ Initialize a new instance of Document """
        self.id = id
        self.title = title
        self.qarequests = qarequests
        self.qajobs = qajobs
        self.qadeadletter = qadeadletter
        self.qaserver = qaserver
        self.token = token
        self.app_name = app_name
        self.wf_state_type = 'hybrid'
        self.requestTimeout = requestTimeout

    def manage_settings(self, title, qarequests, qajobs,
                        qadeadletter, qaserver, token, app_name,
                        requestTimeout):
        """ Change properties of the QA Application """
        self.title = title
        self.qarequests = qarequests
        self.qajobs = qajobs
        self.qadeadletter = qadeadletter
        self.qaserver = qaserver
        self.token = token
        self.app_name = app_name
        self.requestTimeout = requestTimeout

    security.declareProtected('Use OpenFlow', '__call__')

    def __call__(self, workitem_id, REQUEST=None):
        """ Runs the Remote Aplication for the first time """
        # The workitem taken by aquisition
        wk = getattr(self, workitem_id)
        # delete all automatic feedbacks previously posted by this application
        l_envelope = wk.getMySelf()
        for l_item in l_envelope.objectValues('Report Feedback'):
            if l_item.activity_id == self.app_name:
                l_envelope.manage_delObjects(l_item.id)
        # Initialize the workitem QA specific extra properties
        self.__initializeWorkitem(workitem_id)
        no_of_files = len(l_envelope.objectValues('Report Document'))
        if not no_of_files:
            wk.addEvent('Operation completed: no files to analyze')
            if REQUEST is not None:
                REQUEST.set('RemoteApplicationSucceded', 1)
                REQUEST.set('actor', 'openflow_engine')
            self.__finishApplication(workitem_id, REQUEST)
        else:
            self.do_request(workitem_id)
        return 1

    def makeHTTPRequest(self, url, method='GET', data=None, params=None):
        headers = {
            'Authorization': self.token,
            'Content-type': 'application/json',
        }
        url = "/".join([self.qaserver, url])
        timeout = int(getattr(self, 'requestTimeout', 5))
        if method == 'GET':
            response = requests.get(url, headers=headers,
                                    data=json.dumps(data),
                                    params=params, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, headers=headers,
                                     data=json.dumps(data),
                                     timeout=timeout, params=params)
        return response

    def do_request(self, workitem_id):
        wk = getattr(self, workitem_id)
        # delete all automatic feedbacks previously posted by this application
        l_envelope = wk.getMySelf()
        l_wk_prop = getattr(wk, self.app_name)

        data = {
            "envelopeUrl": l_envelope.absolute_url(),
            "uuid": str(wk.UUID)
        }
        # queue_msg(json.dumps(data, indent=4), self.qarequests)
        send_message_nodqueue(json.dumps(data, indent=4), self.qarequests)
        l_wk_prop['requests']['published'] = DateTime()

    security.declareProtected('Use OpenFlow', 'callApplication')

    def check_uuid(self, workitem_id, uuid_str):
        wk = getattr(self, workitem_id)
        return str(wk.UUID) == str(uuid_str)

    def callApplication(self, workitem_id, REQUEST=None):
        """ Called on regular basis """
        wk = getattr(self, workitem_id)
        l_wk_prop = getattr(wk, self.app_name)
        payload = None
        if self.REQUEST and self.REQUEST.get('BODY'):
            try:
                payload = json.loads(self.REQUEST.get('BODY'))
            except Exception as e:
                feedback_log.error(
                    "Unable to parse payload: {}".format(str(e)))

        if payload and self.check_uuid(workitem_id, payload.get('uuid')):
            if 'numberOfJobs' in payload and 'jobIds' in payload:
                l_wk_prop['number_of_jobs'] = payload.get('numberOfJobs')
                if payload.get('numberOfJobs') == 0:
                    wk.addEvent(
                        'Operation completed: no QC scripts available to '
                        'analyze the files in the envelope')
                else:
                    for job_id in payload.get('jobIds'):
                        if job_id not in l_wk_prop['jobs_summary']:
                            l_wk_prop['jobs_summary'][job_id] = {
                                'completed': False
                            }
            elif payload.get('errorMessage'):
                wk.addEvent('{} process failed due to:{}'.format(
                            self.app_name, payload.get('errorMessage')))
                wk.failure = True
                self.__finishApplication(workitem_id, REQUEST)
            else:
                job_id = payload.get('jobId')
                l_file_id = urllib.unquote(
                    string.split(payload.get('documentURL'), '/')[-1])
                if not l_wk_prop['getResult'].get(job_id):
                    l_wk_prop['getResult'][job_id] = []
                    l_wk_prop['jobs_summary'][job_id] = {
                        'completed': False
                    }
                    wk.addEvent('{} job in progress: #{} for {}'.format(
                        self.app_name, job_id, l_file_id))
                l_wk_prop['getResult'][job_id].append(payload)
                l_wk_prop['jobs_summary'][job_id]['last_status'] = {
                    'status': payload.get('status'),
                    'date_time': DateTime(),
                }
                # handle results
                job_result = payload.get('jobResult')
                exec_status = payload.get('executionStatus', '')
                code = exec_status.get('statusId', '') if exec_status else ''
                if job_result:
                    envelope = self.aq_parent
                    r_files = job_result.get('remoteFiles')
                    if r_files:
                        # do we need to handle multiple files?
                        if not isinstance(r_files, list):
                            r_files = [r_files]
                        for r_file in r_files:
                            c_type = job_result.get('feedbackContentType')
                            c_type = c_type if c_type else 'text/html'
                            fb_status = job_result.get('feedbackStatus')
                            fb_status = fb_status if fb_status else 'UNKNOWN'
                            e_data = {
                                'SCRIPT_TITLE': payload.get('scriptTitle'),
                                'feedbackContentType': c_type,
                                'feedbackStatus': fb_status,
                                'feedbackMessage': job_result.get(
                                    'feedbackMessage')
                            }
                            self.handle_remote_file(
                                r_file, l_file_id, workitem_id, e_data, job_id,
                                restricted=self.get_restricted_status(
                                    envelope, l_file_id))
                    else:
                        if l_file_id == 'xml':
                            l_filename = ' result for: '
                        else:
                            l_filename = ' result for file %s: ' % l_file_id
                        feedback_id = '{0}_{1}'.format(self.app_name, job_id)
                        fb_title = ''.join([self.app_name,
                                            l_filename,
                                            payload.get('scriptTitle')])

                        envelope.manage_addFeedback(
                            id=feedback_id,
                            title=fb_title,
                            activity_id=wk.activity_id,
                            automatic=1,
                            document_id=l_file_id,
                            restricted=self.get_restricted_status(
                                envelope, l_file_id))
                        feedback_ob = envelope[feedback_id]

                        content = job_result.get('feedbackContent')
                        content = content if content else 'N/A'
                        content_type = job_result.get('feedbackContentType')
                        if not content_type:
                            content_type = 'text/html'

                        if content and len(content) > FEEDBACKTEXT_LIMIT:
                            with tempfile.TemporaryFile() as tmp:
                                tmp.write(content.encode('utf-8'))
                                tmp.seek(0)
                                feedback_ob.manage_uploadFeedback(
                                    tmp,
                                    filename='qa-output')
                            fb_attach = feedback_ob.objectValues()[0]
                            fb_attach.data_file.content_type = content_type
                            feedback_ob.feedbacktext = (
                                'Feedback too large for inline display; '
                                '<a href="qa-output/view">see attachment</a>.')
                            feedback_ob.content_type = 'text/html'
                        else:
                            feedback_ob.feedbacktext = content
                            feedback_ob.content_type = content_type

                        feedback_ob.message = job_result.get('feedbackMessage',
                                                             '')
                        fb_status = job_result.get('feedbackStatus')
                        fb_status = fb_status if fb_status else 'UNKNOWN'
                        feedback_ob.feedback_status = fb_status

                        if job_result['feedbackStatus'] == 'BLOCKER':
                            wk.blocker = True

                        feedback_ob._p_changed = 1
                        feedback_ob.reindex_object()
                    if code and code in ['0', '1']:
                        wk.addEvent('{} job completed: #{} for {}'.format(
                            self.app_name, job_id, l_file_id))
                        l_wk_prop['jobs_handled'] += 1
                        l_wk_prop['jobs_summary'][job_id]['completed'] = True

                if code:
                    if code not in ['0', '1']:
                        l_wk_prop['jobs_handled'] += 1
                        l_wk_prop['jobs_summary'][job_id]['completed'] = True
                        wk.addEvent('{} job failed: #{} for {}'.format(
                            self.app_name, job_id, l_file_id))
            wk._p_changed = 1
            if l_wk_prop['number_of_jobs'] == l_wk_prop['jobs_handled']:
                self.__finishApplication(workitem_id, REQUEST)
        else:
            feedback_log.warning("Invalid payload: {}".format(payload))

        # test if analyze should be called
        if not l_wk_prop['requests']['published']:
            self.do_request(workitem_id)

        return 1

    def get_restricted_status(self, env, file_id):
        if file_id == 'xml' and env.areRestrictions():
            return True
        doc = env.unrestrictedTraverse(file_id, None)
        if doc and isinstance(doc, Document) and doc.isRestricted():
            return True
        return False

    ##############################################
    #   Private functions
    ##############################################

    def __initializeWorkitem(self, p_workitem_id):
        """ Adds QA-specific extra properties to the workitem """
        wk = getattr(self, p_workitem_id)
        setattr(wk, self.app_name, {})
        setattr(wk, 'UUID', uuid.uuid4())
        l_wk_prop = getattr(wk, self.app_name)
        l_wk_prop['requests'] = {
            'code': 0,
            'last_error': None,
            'next_run': DateTime(),  # Do we need this?
            'published': None
        }

        l_wk_prop['getResult'] = {}
        l_wk_prop['jobs_handled'] = 0
        l_wk_prop['number_of_jobs'] = None
        l_wk_prop['jobs_summary'] = {}

    def __finishApplication(self, p_workitem_id, REQUEST=None):
        """ Completes the workitem and forwards it """
        self.activateWorkitem(p_workitem_id, actor='openflow_engine')
        wk = getattr(self, p_workitem_id)
        env = wk.getMySelf()
        env.wf_status = 'forward'
        env.reindex_object()
        self.completeWorkitem(p_workitem_id, actor='openflow_engine',
                              REQUEST=REQUEST)
        self.forwardWorkitem(p_workitem_id, REQUEST=REQUEST)

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = PageTemplateFile(
        'zpt/remote/application_edit_rabbitmq_qa',
        globals())

    def delete_job(self, job_id, workitem_id):
        """ Make a request to delete the job """
        url = 'asynctasks/qajobs/delete/{}'.format(job_id)
        wk = getattr(self, workitem_id)

        try:
            username = self.REQUEST['AUTHENTICATED_USER'].getUserName()
        except Exception:
            username = 'N/A'
        try:
            res = self.makeHTTPRequest(url, method='POST')
            message = res.json().get('message')
            wk.addEvent(
                '#{} job cancelation triggered by: {} - {}: {}'.format(
                    job_id,
                    username,
                    res.status_code,
                    message))
        except Exception as e:
            wk.addEvent(
                '#{} job cancelation triggered by: {}, failed with: {}'.format(
                    job_id, username, str(e)))

    def listQAScripts(self, file_schema, short=True):
        """Return a list of QA scripts for file schema"""
        # /restapi/qascripts
        url = 'qascripts'
        result = []
        if file_schema:
            params = {
                'schema': file_schema
            }
            try:
                response = self.makeHTTPRequest(url, params=params)
                if response.status_code == 200:
                    scripts = response.json()
                    if short:
                        result = [[script.get('id').encode('utf-8'),
                                   script.get('name').encode('utf-8'),
                                   '',
                                   script.get(
                                    'runOnDemandMaxFileSizeMB').encode(
                                    'utf-8'),
                                   script.get('outputType').encode('utf-8')]
                                  for script in scripts]
                    else:
                        compat = {
                            'outputType': 'content_type_id',
                            'name': 'short_name',
                            'description': 'description',
                            'isActive': 'isActive',
                            'type': 'type',
                            'url': 'query',
                            'schemaUrl': 'xml_schema',
                            'runOnDemandMaxFileSizeMB': 'upper_limit',
                            'content_type_out': 'outputType'
                        }
                        result = []
                        for script in scripts:
                            remapped = {
                                compat[name]: val for name, val in script.iteritems() if compat.get(name)}  # noqa
                            remapped['content_type_out'] = script.get(
                                'outputType')
                            result.append(remapped)
            except Exception:
                pass

        return result

    def runQAScript(self, p_file_url, p_script_id):
        """
        """
        url = 'qajobs'
        data = {
            "sourceUrl": p_file_url,
            "scriptId": p_script_id
        }

        try:
            res = self.makeHTTPRequest(url, method='POST', data=data)
            if res.status_code == 200:
                result = res.json()
                c_type = result.get('feedbackContentType', 'text/html')
                # Creating a class here to preserve backwards compatibility

                class ODQA(object):
                    pass
                odqa = ODQA()
                setattr(odqa, 'data', result.get('feedbackContent', ''))
                return c_type, odqa
            else:
                raise Exception(
                    "Received {} status code from QA service.".format(
                        res.status_code))
        except requests.exceptions.Timeout:
            raise Exception(
                "No response received from QA Service in"
                " the alloted time: {}s".format(self.requestTimeout))


InitializeClass(RemoteRabbitMQQAApplication)
