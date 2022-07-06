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
import transaction
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from DateTime import DateTime
from Document import Document
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.BaseRemoteApplication import BaseRemoteApplication
from Products.Reportek.interfaces import IQAApplication
from Products.Reportek.rabbitmq import queue_msg
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
                 qadeadletter, qaserver, token, app_name):
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

    def manage_settings(self, title, qarequests, qajobs,
                        qadeadletter, qaserver, token, app_name):
        """ Change properties of the QA Application """
        self.title = title
        self.qarequests = qarequests
        self.qajobs = qajobs
        self.qadeadletter = qadeadletter
        self.qaserver = qaserver
        self.token = token
        self.app_name = app_name

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
            self.__manageAutomaticProperty(p_workitem_id=workitem_id,
                                           p_analyze={'code': 2})
            wk.addEvent('Operation completed: no files to analyze')
            if REQUEST is not None:
                REQUEST.set('RemoteApplicationSucceded', 1)
                REQUEST.set('actor', 'openflow_engine')
            self.__finishApplication(workitem_id, REQUEST)
        else:
            self.do_request(workitem_id)
        return 1

    def do_request(self, workitem_id):
        wk = getattr(self, workitem_id)
        # delete all automatic feedbacks previously posted by this application
        l_envelope = wk.getMySelf()
        l_wk_prop = getattr(wk, self.app_name)

        data = {
            "envelopeUrl": l_envelope.absolute_url(),
            "UUID": str(wk.UUID)
        }
        queue_msg(json.dumps(data, indent=4), self.qarequests)
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
        if REQUEST and REQUEST.get('BODY'):
            try:
                payload = json.loads(REQUEST.get('BODY'))
            except Exception as e:
                feedback_log.error(
                    "Unable to parse payload: {}".format(str(e)))

        if payload and self.check_uuid(workitem_id, payload.get('UUID')):
            job_id = payload.get('jobId')
            l_file_id = urllib.unquote(
                string.split(payload.get('documentURL'), '/')[-1])
            if not l_wk_prop['jobs'].get(job_id):
                l_wk_prop['jobs'][job_id] = []
                wk.addEvent('{} job in progress: #{} for {}'.format(
                    self.app_name, job_id, l_file_id))
            l_wk_prop['jobs'][job_id].append(payload)
            # handle results
            job_result = payload.get('jobResult')
            if job_result:
                r_files = job_result.get('REMOTE_FILES')
                if r_files:
                    envelope = self.aq_parent
                    # do we need to handle multiple files?
                    if not isinstance(r_files, list):
                        r_files = [r_files]
                    for r_file in r_files:
                        e_data = {'SCRIPT_TITLE': payload.get('scriptTitle')}
                        self.handle_remote_file(
                            r_file, l_file_id, workitem_id, e_data, job_id,
                            restricted=self.get_restricted_status(
                                envelope, l_file_id))
                    l_wk_prop['jobs']['handled'] += 1
                    jobs_no = job_result.get('numberOfJobs')
                    if jobs_no == l_wk_prop['jobs']['handled']:
                        self.__finishApplication(workitem_id, REQUEST)
        else:
            feedback_log.warning("Invalid payload: {}".format(payload))

        # test if analyze should be called
        if not l_wk_prop['requests']['published']:
            self.do_request(workitem_id)

        return 1

    def runAutomaticLocalApps(self, workitem):
        # call this from a thread (or no)
        wk_status = getattr(workitem, self.app_name)
        for file_id, result, script_id in self._runLocalQAScripts(workitem):
            wk_status = getattr(workitem, self.app_name)
            self._addFeedback(file_id, result, workitem, script_id)
            # mark script for file as done
            wk_status['localQA'][file_id][script_id] = 'done'
            transaction.commit()

    def get_restricted_status(self, env, file_id):
        if file_id == 'xml' and env.areRestrictions():
            return True
        doc = env.unrestrictedTraverse(file_id, None)
        if doc and isinstance(doc, Document) and doc.isRestricted():
            return True
        return False

    def _addFeedback(self, file_id, result, workitem, script_id):
        envelope = self.aq_parent
        qa_repo = self.QARepository
        script_title = qa_repo[script_id].title

        feedback_id = '{0}_{1}_{2}'.format(self.app_name, script_id, file_id)
        feedback_title = '{0} result for file {1}: {2}'.format(self.app_name,
                                                               file_id,
                                                               script_title)
        envelope.manage_addFeedback(
            id=feedback_id,
            title=feedback_title,
            activity_id=workitem.activity_id,
            automatic=1,
            restricted=self.get_restricted_status(envelope, file_id))

        feedback_ob = envelope[feedback_id]
        content = result[1].data
        content_type = result[0]
        if len(content) > FEEDBACKTEXT_LIMIT:
            with tempfile.TemporaryFile() as tmp:
                tmp.write(content.encode('utf-8'))
                tmp.seek(0)
                feedback_ob.manage_uploadFeedback(tmp, filename='qa-output')
            feedback_attach = feedback_ob.objectValues()[0]
            feedback_attach.data_file.content_type = content_type
            feedback_ob.feedbacktext = (
                'Feedback too large for inline display; '
                '<a href="qa-output/view">see attachment</a>.')
            feedback_ob.content_type = 'text/html'

        else:
            feedback_ob.feedbacktext = content
            feedback_ob.content_type = content_type

    def _runLocalQAScripts(self, workitem):
        # 'localQA': {'file_name':{'script_name': 'status',
        #                          'script_name2': 'status'},
        #             'file_name2': {'script_name2': 'status',
        #                            'script_name3': 'status'}
        qa_repo = self.QARepository
        wk_status = getattr(workitem, self.app_name)
        if 'localQA' not in wk_status:
            wk_status['localQA'] = {}
        localQA = wk_status['localQA']
        xmls = (x for x in self.aq_parent.objectValues(Document.meta_type)
                if x.content_type == 'text/xml' and x.xml_schema_location)
        for xml in xmls:
            if xml.id not in localQA:
                localQA[xml.id] = {}
            resultsForXml = localQA[xml.id]
            for script in qa_repo._get_local_qa_scripts(
                    xml.xml_schema_location):
                if (script.id not in resultsForXml
                        or resultsForXml[script.id] == 'failed'):
                    resultsForXml[script.id] = 'in progress'
                    transaction.commit()
                    file_id, result = qa_repo._runQAScript(
                        xml.absolute_url(1), 'loc_%s' % script.id)
                    yield file_id, result, script.id
                    # else, don't yield - nothing will happen in parent's loop

    def _local_scripts_done(self, localQA):
        # not ran yet
        if not localQA:
            return False
        for script_results in localQA.values():
            # any bad status present?
            if any((bad_status for bad_status in script_results.values()
                    if bad_status != 'done')):
                return False
        # truly no bad statuses (including no script -> status pairs) because
        # we check this after join
        return True

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

        l_wk_prop['jobs'] = {}

    def __manageAutomaticProperty(self, p_workitem_id, p_analyze={},
                                  p_getResult={}):
        """
        The instance data for the RemoteApplication is stored in the workitem
        as an additional property - app_name - contaning a dictionary like:
        {
            'analyze':      {code, retries_left, last_error, next_run},
            'getResult':    {jobID: {code, retries_left, last_error, next_run,
                                     fileURL}}
        }
        Possible codes for app_name['analyze']:
            0 - started
            1 - done
            -2 - failed
            2 - nothing found to assess

        Possible codes for app_name['getResult'][jobID]:
            0 - started
            1 - result succefully brought
            -2 - failed
        """
        wk = getattr(self, p_workitem_id)
        l_qa = getattr(wk, self.app_name)

        for l_key in p_analyze.keys():
            l_qa['analyze'][l_key] = p_analyze[l_key]

        for l_job, l_value in p_getResult.items():
            if l_job not in l_qa['getResult']:
                l_qa['getResult'][l_job] = {}
            l_qa['getResult'][l_job].update(l_value)

        # make sure it saves the object
        wk._p_changed = 1

    def __finishApplication(self, p_workitem_id, REQUEST=None):
        """ Completes the workitem and forwards it """
        self.activateWorkitem(p_workitem_id, actor='openflow_engine')
        self.completeWorkitem(p_workitem_id, actor='openflow_engine',
                              REQUEST=REQUEST)

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
