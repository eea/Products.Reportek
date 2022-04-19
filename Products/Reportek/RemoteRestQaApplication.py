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
from zope.interface import implements

feedback_log = logging.getLogger(__name__ + '.feedback')

FEEDBACKTEXT_LIMIT = 1024 * 16  # 16KB


manage_addRemoteRESTQAApplicationForm = PageTemplateFile(
    'zpt/remote/application_add_rest_qa',
    globals())


def manage_addRemoteRESTQAApplication(self, id='', title='', RemoteServer='',
                                      token='', app_name='', REQUEST=None):
    """ Generic application that calls a remote service
    """

    ob = RemoteRestQaApplication(id, title, RemoteServer, token, app_name)
    self._setObject(id, ob)

    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class RemoteRestQaApplication(BaseRemoteApplication):
    """ A computerised application, executed by an activity.
        It executes a set of operations on a remote server and generates a
        feedback object into the envelope as result of these.
        The instance data for the RemoteApplication is stored in the workitem
        as an additional property - app_name - contaning a dictionary like::

          {
            'analyze':      {code, retries_left, last_error, next_run},
            'getResult':    {jobID: {code, retries_left, last_error, next_run,
                                     fileURL}}
          }

        First, a call is made to the 'analyze' function from the remote service
        which retireves the list of files that will be analyzed along with
        their jobIDs

        Second, the 'getResult' remote service function is called for every job

        Possible codes for app_name['analyze']:

        -   0 - started
        -   2 - nothing to do
        -   1 - done
        -   -2 - failed

        Possible codes for app_name['getResult'][jobID]:

        -   0 - processing
        -   1 - result succefully brought
        -   -2 - failed
    """

    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()
    implements(IQAApplication)
    meta_type = 'Remote Rest QA Application'

    manage_options = (({'label': 'Settings',
                        'action': 'manage_settings_html'},) +
                      SimpleItem.manage_options
                      )

    def __init__(self, id, title, RemoteServer, token, app_name,
                 nRetries=5, nJobRetries=5, requestTimeout=5,
                 retryFrequency=300, retryJobFrequency=300):
        """ Initialize a new instance of Document """
        self.id = id
        self.title = title
        self.RemoteServer = RemoteServer
        self.app_name = app_name
        self.nRetries = nRetries                            # integer
        self.nJobRetries = nJobRetries                      # integer
        self.requestTimeout = requestTimeout                # integer - seconds
        self.token = token
        self.retryFrequency = retryFrequency                # integer - seconds
        self.retryJobFrequency = retryJobFrequency          # integer - seconds

    def manage_settings(self, title, RemoteServer, app_name, token,
                        nRetries, nJobRetries, requestTimeout, retryFrequency,
                        retryJobFrequency):
        """ Change properties of the QA Application """
        self.title = title
        self.RemoteServer = RemoteServer
        self.nRetries = nRetries
        self.nJobRetries = nJobRetries
        self.token = token
        self.app_name = app_name
        self.requestTimeout = requestTimeout
        self.retryFrequency = retryFrequency
        self.retryJobFrequency = retryJobFrequency

    security.declareProtected('Use OpenFlow', '__call__')

    def __call__(self, workitem_id, REQUEST=None):
        """ Runs the Remote Aplication for the first time """
        # The workitem taken by aquisition
        l_workitem = getattr(self, workitem_id)
        # delete all automatic feedbacks previously posted by this application
        l_envelope = l_workitem.getMySelf()
        for l_item in l_envelope.objectValues('Report Feedback'):
            if l_item.activity_id == self.app_name:
                l_envelope.manage_delObjects(l_item.id)

        # Initialize the workitem QA specific extra properties
        self.__initializeWorkitem(workitem_id)

        no_of_files = len(l_envelope.objectValues('Report Document'))
        if not no_of_files:
            self.__manageAutomaticProperty(p_workitem_id=workitem_id,
                                           p_analyze={'code': 2})
            l_workitem.addEvent('Operation completed: no files to analyze')
            if REQUEST is not None:
                REQUEST.set('RemoteApplicationSucceded', 1)
                REQUEST.set('actor', 'openflow_engine')
            self.__finishApplication(workitem_id, REQUEST)
        else:
            l_ret = self.__analyzeDocuments(workitem_id)
            if not l_ret:
                l_workitem.addEvent(
                    'Operation completed: no QC scripts available to analyze '
                    'the files in the envelope')
                if REQUEST is not None:
                    REQUEST.set('RemoteApplicationSucceded', 1)
                    REQUEST.set('actor', 'openflow_engine')
                self.__finishApplication(workitem_id, REQUEST)
            elif getattr(l_workitem, self.app_name)['analyze']['code'] == -2:
                l_workitem.addEvent(
                    'Operation failed: error calling the remote service')
                if REQUEST is not None:
                    REQUEST.set('RemoteApplicationSucceded', 0)
                    REQUEST.set('actor', 'openflow_engine')
                self.__finishApplication(workitem_id, REQUEST)
        return 1

    def makeHTTPRequest(self, url, method='GET', data=None, params=None):
        headers = {
            'Authorization': self.token,
            'Content-type': 'application/json',
        }
        url = "/".join([self.RemoteServer, url])
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

    security.declareProtected('Use OpenFlow', 'callApplication')

    def callApplication(self, workitem_id, REQUEST=None):
        """ Called on regular basis """
        l_workitem = getattr(self, workitem_id)
        # dictionary of {xml_schema_location: [URL_file]}
        # get the property of the workitem which keeps all the instance data
        # for this operation
        l_wk_prop = getattr(l_workitem, self.app_name)

        # test if analyze should be called
        if l_wk_prop['analyze']['code'] == 0:
            self.__analyzeDocuments(workitem_id)
        # see if it's any point to go on
        elif (l_wk_prop['analyze']['code'] == -2
                and self._local_scripts_done(l_wk_prop.get('localQA'))):
            l_workitem.failure = True
            if REQUEST is not None:
                REQUEST.set('RemoteApplicationSucceded', 0)
                REQUEST.set('actor', 'openflow_engine')
            self.__finishApplication(workitem_id, REQUEST)
            return 1

        self.runAutomaticLocalApps(l_workitem)
        # test if getResult should be called
        l_files_success = {}
        l_files_failed = {}
        for l_jobID, l_job_details in l_wk_prop['getResult'].items():
            if (l_job_details['code'] == 0
                    and l_job_details['next_run'].lessThanEqualTo(DateTime())):
                l_ret_step2 = self.__getResult4XQueryServiceJob(workitem_id,
                                                                l_jobID)
                l_fn = l_job_details['fileURL'].split('/')[-1]
                if l_ret_step2[l_jobID]['code'] == 1:
                    if l_fn in l_files_success:
                        l_files_success[l_fn] += ', #%s' % l_jobID
                    else:
                        l_files_success[l_fn] = '#%s' % l_jobID
                else:
                    if l_fn in l_files_failed:
                        l_files_failed[l_fn] += ', #%s' % l_jobID
                    else:
                        l_files_failed[l_fn] = '#%s' % l_jobID
        # log the results from local QA
        for filename, scripts in l_wk_prop['localQA'].items():
            success = []
            fail = []
            for script, status in scripts.items():
                if status == 'done':
                    success.append("#" + script)
                else:
                    fail.append('#' + script)
            success = ', '.join(success)
            fail = ', '.join(fail)
            # if we have some stuff logged from above
            if filename in l_files_success and success:
                success = ', ' + success
            if filename in l_files_failed and fail:
                fail = ', ' + fail
            if success:
                l_files_success[filename] = l_files_success.get(
                    filename, '') + success
            if fail:
                l_files_failed[filename] = l_files_failed.get(
                    filename, '') + fail

        # write to log the list of file that succeded
        if l_files_success:
            l_filenames_jobs = ''
            for x in l_files_success.keys():
                l_filenames_jobs += '<li>%s for file %s</li>' % (
                    l_files_success[x], x)
            l_workitem.addEvent('%s job(s) completed: <ul>%s</ul>' %
                                (self.app_name, l_filenames_jobs))
        # Check if the application has done its job
        l_complete = 1
        l_failed = 0

        # Retry if we have no getResult
        if not l_wk_prop['getResult']:
            l_complete = 0

        for l_jobID, l_job_details in l_wk_prop['getResult'].items():
            # result retrieved
            if l_job_details['code'] == 1:
                pass
            # error of some kind
            elif l_job_details['code'] == -2:
                l_failed = 1
            # needs to run again, do not complete
            else:
                l_complete = 0

        if l_complete:
            # write to log the list of file that failed
            if l_files_failed:
                l_filenames_jobs = ''
                for x in l_files_failed.keys():
                    l_filenames_jobs += '<li>%s for file %s</li>' % (
                        l_files_failed[x], x)
                l_workitem.addEvent('Giving up on %s job(s): <ul>%s</ul>' %
                                    (self.app_name, l_filenames_jobs))
                l_workitem.failure = True
            if REQUEST is not None:
                REQUEST.set('RemoteApplicationSucceded', 1 - l_failed)
                REQUEST.set('actor', 'openflow_engine')
            self.__finishApplication(workitem_id, REQUEST)
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
    #   XQuery calls
    ##############################################

    def __analyzeDocuments(self, p_workitem_id):
        """ Makes an XML/RPC call to the 'analyzeXMLFiles' function from
            the XQuery service
        """

        l_workitem = getattr(self, p_workitem_id)
        # get the property of the workitem which keeps all the instance data
        # for this operation
        l_wk_prop = getattr(l_workitem, self.app_name)
        envelope_url = l_workitem.getMySelf().absolute_url()
        try:
            url = 'asynctasks/qajobs/batch'
            data = {
                "envelopeUrl": envelope_url
            }
            response = self.makeHTTPRequest(url, method='POST', data=data)
            # if there were no files to assess, return 0 so the work can go on
            data = json.loads(response.content)
            feedback_log.info("Response: {}".format(response.content))
            response.raise_for_status()
            data = data['jobs']
            if len(data) == 0:
                self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                               p_analyze={'code': 2})
                return 0
            # Operation succedded, the rest endpoint got the call
            # and it returned [(jobID, fileURL)]
            l_getResult = {}
            l_files = {}

            # Setting up jobs metadata
            job_ret = self.nJobRetries if getattr(
                self, 'nJobRetries', None) else self.nRetries
            for entry in data:
                l_job = entry['jobId']
                l_file = entry['fileUrl']
                l_getResult[str(l_job)] = {
                    'code': 0,
                    'retries_left': job_ret,
                    'last_error': None,
                    'next_run': DateTime(),
                    'fileURL': l_file
                }
                l_filename = l_file.split('/')[-1]
                if l_filename in l_files:
                    l_files[l_filename] += ', #' + str(l_job)
                else:
                    l_files[l_filename] = '#' + str(l_job)
            self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                           p_analyze={'code': 1},
                                           p_getResult=l_getResult)
            # Write in the envelope's log which files were sent to be analyzed
            # and their QA jobs
            l_filenames_jobs = ''
            for x in l_files.keys():
                l_filenames_jobs += '<li>%s for file %s</li>' % (l_files[x], x)
            l_workitem.addEvent('%s job(s) in progress: <ul>%s</ul>' %
                                (self.app_name, l_filenames_jobs))

        # An XML-RPC fault package - retry later
        # The agreed errors from the XQuery service are embedded
        # in this error type
        except (requests.exceptions.HTTPError):
            l_nRetries = int(l_wk_prop['analyze']['retries_left'])
            code_err = response.status_code
            code_message = response.json().get('errorMessage', '')
            if l_nRetries == 0:
                l_workitem.addEvent('Error in sending files to %s: %s' %
                                    (self.app_name, str(code_message)))
                l_workitem.failure = True
                err = 'Code: {}\nDescription: {}'.format(str(code_err),
                                                         str(code_message))
                self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                               p_analyze={
                                                   'code': -2,
                                                   'last_error': err
                                               })
            else:
                next_run = DateTime(int(l_wk_prop['analyze']['next_run']) +
                                    int(self.retryFrequency))
                err = 'Code: {}\nDescription: {}'.format(str(code_err),
                                                         str(code_message))
                self.__manageAutomaticProperty(
                    p_workitem_id=p_workitem_id,
                    p_analyze={
                        'code': 0,
                        'last_error': err,
                        'retries_left': l_nRetries - 1,
                        'next_run': next_run
                    })
        except Exception as err:
            l_workitem.addEvent('Error in sending files to %s: %s' %
                                (self.app_name, str(err)))
            l_workitem.failure = True
            self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                           p_analyze={
                                               'code': -2,
                                               'last_error': str(err)
                                           })
        return 1

    def __getResult4XQueryServiceJob(self, p_workitem_id, p_jobID):
        """ Makes an XML/RPC call to the 'getResult' function from the remote
            service for an existing job
        """
        l_workitem = getattr(self, p_workitem_id)
        # get the property of the workitem which keeps all the instance data
        # for this operation
        l_wk_prop = getattr(l_workitem, self.app_name)
        # find out what file this job was for
        l_file_url = l_wk_prop['getResult'][p_jobID]['fileURL']
        l_file_id = urllib.unquote(string.split(l_file_url, '/')[-1])
        envelope = self.aq_parent
        try:
            url = 'asynctasks/qajobs/{}'.format(str(p_jobID))
            response = self.makeHTTPRequest(url, method='GET', data={})
            data = json.loads(response.content)
            response.raise_for_status()
            code = data.get('executionStatus', '')
            if code:
                code = code.get('statusId', '')
            else:
                code == ''

            # job ready
            if code == '0':
                r_files = data.get('REMOTE_FILES')
                if r_files:
                    for r_file in r_files:
                        e_data = {'SCRIPT_TITLE': data.get('scriptTitle')}
                        r_res = self.handle_remote_file(
                            r_file, l_file_id, p_workitem_id, e_data, p_jobID,
                            restricted=self.get_restricted_status(
                                envelope, l_file_id))
                        l_getResultDict = {
                            p_jobID: {
                                'code': 1,
                                'fileURL': l_file_url,
                                'debug': {
                                    'c_executionstatus': code,
                                    'c_feedbackstatus': data.get(
                                        'feedbackStatus', 'N/A'),
                                    'c_feedbackmessage': data.get(
                                        'feedbackMessage', 'N/A'),
                                    'c_feedbackcontent_len': len(
                                        data.get('feedbackContent', '')),
                                    'remote_files_debug': r_res
                                }
                            }}
                        self.__manageAutomaticProperty(
                            p_workitem_id=p_workitem_id,
                            p_getResult=l_getResultDict)
                else:
                    if l_file_id == 'xml':
                        l_filename = ' result for: '
                    else:
                        l_filename = ' result for file %s: ' % l_file_id
                    feedback_id = '{0}_{1}'.format(self.app_name, p_jobID)
                    fb_title = ''.join([self.app_name,
                                        l_filename,
                                        data['scriptTitle']])

                    envelope.manage_addFeedback(
                        id=feedback_id,
                        title=fb_title,
                        activity_id=l_workitem.activity_id,
                        automatic=1,
                        document_id=l_file_id,
                        restricted=self.get_restricted_status(
                            envelope, l_file_id))
                    feedback_ob = envelope[feedback_id]

                    content = data['feedbackContent']
                    content_type = data['feedbackContentType']

                    if len(content) > FEEDBACKTEXT_LIMIT:
                        with tempfile.TemporaryFile() as tmp:
                            tmp.write(content.encode('utf-8'))
                            tmp.seek(0)
                            feedback_ob.manage_uploadFeedback(
                                tmp,
                                filename='qa-output')
                        feedback_attach = feedback_ob.objectValues()[0]
                        feedback_attach.data_file.content_type = content_type
                        feedback_ob.feedbacktext = (
                            'Feedback too large for inline display; '
                            '<a href="qa-output/view">see attachment</a>.')
                        feedback_ob.content_type = 'text/html'

                    else:
                        feedback_ob.feedbacktext = content
                        feedback_ob.content_type = content_type

                    feedback_ob.message = data.get('feedbackMessage', '')
                    feedback_ob.feedback_status = data.get(
                        'feedbackStatus', '')

                    if data['feedbackStatus'] == 'BLOCKER':
                        l_workitem.blocker = True

                    feedback_ob.message = data.get('feedbackMessage', '')
                    feedback_ob._p_changed = 1
                    feedback_ob.reindex_object()

                    l_getResultDict = {
                        p_jobID: {
                            'code': 1,
                            'fileURL': l_file_url,
                            'debug': {
                                'c_executionstatus': code,
                                'c_feedbackstatus': data.get(
                                    'feedbackStatus', 'N/A'),
                                'c_feedbackmessage': data.get(
                                    'feedbackMessage', 'N/A'),
                                'c_feedbackcontent_len': len(data.get(
                                    'feedbackContent', ''))
                            }
                        }}
                    self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                                   p_getResult=l_getResultDict)
            # not ready
            elif code == '1':
                l_nRetries = int(
                    l_wk_prop['getResult'][p_jobID]['retries_left'])
                retry = self.retryJobFrequency if getattr(
                    self, 'retryJobFrequency', None) else self.retryFrequency
                next_run = DateTime(
                    int(l_wk_prop['getResult'][p_jobID]['next_run']) +
                    int(retry))
                if l_nRetries > 0:
                    l_getResultDict = {
                        p_jobID: {
                            'code': 0,
                            'retries_left': l_nRetries - 1,
                            'last_error': data['feedbackMessage'],
                            'next_run': next_run,
                            'debug': {
                                'c_executionstatus': code,
                                'c_feedbackstatus': data.get(
                                    'feedbackStatus', 'N/A'),
                                'c_feedbackmessage': data.get(
                                    'feedbackMessage', 'N/A'),
                                'c_feedbackcontent_len': len(data.get(
                                    'feedbackContent', ''))
                            }
                        }
                    }
                    self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                                   p_getResult=l_getResultDict)
                else:
                    l_workitem.addEvent(
                        'Error in the %s, job #%s for file %s: %s' %
                        (self.app_name, p_jobID, l_file_id,
                         data['feedbackMessage']))
                    l_getResultDict = {
                        p_jobID: {
                            'code': -2,
                            'last_error': data['feedbackMessage'],
                            'debug': {
                                'c_executionstatus': code,
                                'c_feedbackstatus': data.get(
                                    'feedbackStatus', 'N/A'),
                                'c_feedbackmessage': data.get(
                                    'feedbackMessage', 'N/A'),
                                'c_feedbackcontent_len': len(
                                    data.get('feedbackContent', ''))
                            }
                        }
                    }
                    self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                                   p_getResult=l_getResultDict)
            # error, do not retry
            else:
                l_workitem.addEvent(
                    'Error in the %s, job #%s for file %s: %s' %
                    (self.app_name, p_jobID, l_file_id,
                     data['feedbackMessage']))
                l_getResultDict = {
                    p_jobID: {
                        'code': -2,
                        'last_error': data['feedbackMessage'],
                        'debug': {
                            'c_executionstatus': code,
                            'c_feedbackstatus': data.get(
                                'feedbackStatus', 'N/A'),
                            'c_feedbackmessage': data.get(
                                'feedbackMessage', 'N/A'),
                            'c_feedbackcontent_len': len(
                                data.get('feedbackContent', ''))
                        }
                    }
                }
                self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                               p_getResult=l_getResultDict)

        # # A client generated exception  - retry later
        # # The agreed errors from the XQuery service are embedded
        # # in this error type
        except (requests.exceptions.HTTPError):
            if response.status_code == 404:
                feedback_log.exception("Unable to get result for job #%s",
                                   p_jobID)
                l_workitem.addEvent('Error in the %s, job #%s for file %s: %s' %
                                    (self.app_name, p_jobID, l_file_id, str(err)))
                l_workitem.failure = True
                l_getResultDict = {p_jobID: {'code': -2, 'last_error': str(err)}}
                self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                            p_getResult=l_getResultDict)
            else:
                l_err = data.get('errorMessage', '')
                l_nRetries = int(l_wk_prop['getResult'][p_jobID]['retries_left'])
                retry = self.retryJobFrequency if getattr(
                    self, 'retryJobFrequency', None) else self.retryFrequency
                if l_nRetries == 0:
                    l_workitem.addEvent(
                        'Error in the %s, job #%s for file %s: %s' %
                        (self.app_name, p_jobID, l_file_id, str(l_err)))
                    l_workitem.failure = True
                    l_getResultDict = {
                        p_jobID: {'code': -2, 'last_error': str(l_err)}}
                    self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                                p_getResult=l_getResultDict)
                else:
                    next_run = DateTime(
                        int(l_wk_prop['getResult'][p_jobID]['next_run']) +
                        int(retry))
                    err = 'Error retrieving job #{} result: {}'.format(
                        p_jobID, str(l_err))
                    l_getResultDict = {
                        p_jobID: {
                            'code': 0,
                            'last_error': err,
                            'retries_left': l_nRetries - 1,
                            'next_run': next_run
                        }
                    }
                    self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                                p_getResult=l_getResultDict)
        # Fatal error - do not retry
        except Exception as err:
            feedback_log.exception("Error saving remote feedback, job #%s",
                                   p_jobID)
            l_workitem.addEvent('Error in the %s, job #%s for file %s: %s' %
                                (self.app_name, p_jobID, l_file_id, str(err)))
            l_workitem.failure = True
            l_getResultDict = {p_jobID: {'code': -2, 'last_error': str(err)}}
            self.__manageAutomaticProperty(p_workitem_id=p_workitem_id,
                                           p_getResult=l_getResultDict)

        return l_getResultDict

    ##############################################
    #   Private functions
    ##############################################

    def __initializeWorkitem(self, p_workitem_id):
        """ Adds QA-specific extra properties to the workitem """
        l_workitem = getattr(self, p_workitem_id)
        setattr(l_workitem, self.app_name, {})
        l_wk_prop = getattr(l_workitem, self.app_name)
        l_wk_prop['analyze'] = {
            'code': 0,
            'retries_left': self.nRetries,
            'last_error': None,
            'next_run': DateTime()
        }

        l_wk_prop['getResult'] = {}

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
        l_workitem = getattr(self, p_workitem_id)
        l_qa = getattr(l_workitem, self.app_name)

        for l_key in p_analyze.keys():
            l_qa['analyze'][l_key] = p_analyze[l_key]

        for l_job, l_value in p_getResult.items():
            if l_job not in l_qa['getResult']:
                l_qa['getResult'][l_job] = {}
            l_qa['getResult'][l_job].update(l_value)

        # make sure it saves the object
        l_workitem._p_changed = 1

    def __finishApplication(self, p_workitem_id, REQUEST=None):
        """ Completes the workitem and forwards it """
        self.activateWorkitem(p_workitem_id, actor='openflow_engine')
        self.completeWorkitem(p_workitem_id, actor='openflow_engine',
                              REQUEST=REQUEST)

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = PageTemplateFile(
        'zpt/remote/application_edit_rest_qa',
        globals())

    def delete_job(self, job_id, workitem_id):
        """ Make a request to delete the job """
        url = 'asynctasks/qajobs/delete/{}'.format(job_id)
        l_workitem = getattr(self, workitem_id)

        try:
            username = self.REQUEST['AUTHENTICATED_USER'].getUserName()
        except Exception:
            username = 'N/A'
        try:
            res = self.makeHTTPRequest(url, method='POST')
            message = res.json().get('message')
            l_workitem.addEvent(
                '#{} job cancelation triggered by: {} - {}: {}'.format(
                    job_id,
                    username,
                    res.status_code,
                    message))
        except Exception as e:
            l_workitem.addEvent(
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


InitializeClass(RemoteRestQaApplication)
