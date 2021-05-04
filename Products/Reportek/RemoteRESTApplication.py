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
# Agency (EEA). Portions created by Eau de Web are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Miruna Badescu, Eau de Web

# RemoteApplication
##

import logging
import re
from StringIO import StringIO

import requests
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from DateTime import DateTime
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.interfaces import IQAApplication
from zope.interface import implements

logger = logging.getLogger(__name__ + '.gisqa')

manage_addRemoteRESTApplicationForm = PageTemplateFile(
    'zpt/rest_add', globals())


def manage_addRemoteRESTApplication(self, id='', title='', ServiceSubmitURL='',
                                    ServiceCheckURL='', app_name='',
                                    REQUEST=None):
    """ Generic application that calls a remote REST service """

    ob = RemoteRESTApplication(
        id, title, ServiceSubmitURL, ServiceCheckURL, app_name)
    self._setObject(id, ob)

    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class RemoteRESTApplication(SimpleItem):

    security = ClassSecurityInfo()
    implements(IQAApplication)
    meta_type = 'Remote REST Application'
    manage_options = (
        ({'label': 'Settings',
          'action': 'manage_settings_html'}, )
        + SimpleItem.manage_options
    )

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = PageTemplateFile('zpt/rest_edit', globals())

    def __init__(self, id, title, ServiceSubmitURL, ServiceCheckURL, app_name,
                 nRetries=5):
        """ Initialize a new instance of Document """
        self.id = id
        self.title = title
        self.ServiceSubmitURL = ServiceSubmitURL
        self.ServiceCheckURL = ServiceCheckURL
        self.app_name = app_name
        self.nRetries = nRetries                    # integer

    def manage_settings(self, title, ServiceSubmitURL, ServiceCheckURL,
                        app_name, nRetries, REQUEST):
        """ Change properties of the QA REST Application """
        self.title = title
        self.title = title
        self.ServiceSubmitURL = ServiceSubmitURL
        self.ServiceCheckURL = ServiceCheckURL
        self.app_name = app_name
        self.nRetries = nRetries
        if REQUEST is not None:
            return self.manage_settings_html(
                manage_tabs_message='Saved changes.')

    def __call__(self, workitem_id, REQUEST=None):
        workitem = getattr(self, workitem_id)

        # Initialize the workitem REST-QA specific extra properties
        self.__initialize(workitem_id)

        envelope_url = workitem.getMySelf().absolute_url(0)
        params = {
            'EnvelopeURL': envelope_url,
            'f': 'pjson',
        }

        resp = requests.get(self.ServiceSubmitURL, params=params)

        if resp.status_code == 200:
            data = None
            try:
                data = resp.json()
            except ValueError:
                workitem.addEvent('%s job request for %s response is not json.'
                                  % (self.app_name, envelope_url))
            if data and 'jobId' in data:
                job_id = data['jobId']
                self.__update(workitem_id, {'jobid': job_id})
                job_status = data['jobStatus']
                if job_status == 'esriJobSubmitted':
                    workitem.addEvent(
                        '%s job request for %s successfully submited.'
                        % (self.app_name, envelope_url))
            else:
                workitem.addEvent('%s job request for %s response is invalid.'
                                  % (self.app_name, envelope_url))
        else:
            workitem.addEvent(
                '%s job request for %s returned invalid status code %s.'
                % (self.app_name, envelope_url, resp.status_code))

    security.declareProtected('Use OpenFlow', 'callApplication')

    def callApplication(self, workitem_id, REQUEST):
        workitem = getattr(self, workitem_id)
        envelope_url = workitem.getMySelf().absolute_url(0)
        attributes = getattr(workitem, self.app_name)
        params = {
            'f': 'pjson',
        }
        jobid = attributes['jobid']
        resp = requests.get(self.ServiceCheckURL + str(jobid), params=params)

        if resp.status_code == 200:
            data = None
            try:
                data = resp.json()
            except ValueError:
                workitem.addEvent('%s job id %s for %s output is not json.'
                                  % (self.app_name, jobid, envelope_url))
            if data and 'jobId' in data:
                job_status = data['jobStatus']
                attach = None
                if job_status == 'esriJobSucceeded':
                    workitem.addEvent(
                        '%s job id %s for %s successfully finished.'
                        % (self.app_name, jobid, envelope_url))
                    try:
                        result_url = data['results']['ResultZip']['paramUrl']
                        resp = requests.get(
                            self.ServiceCheckURL + '%s/%s' % (
                                str(jobid), result_url), params=params)
                        if resp.status_code == 200:
                            zip_url = re.sub(
                                '(/)*\\\\', '/', resp.json()['value'])
                            resp = requests.get(zip_url)
                            if resp.status_code == 200:
                                attach = StringIO(resp.content)
                                attach.filename = '%s_results.zip'\
                                    % workitem.getMySelf().id
                            else:
                                logger.warning(
                                    '''Could not fetch result file from '''
                                    '''this URL: %s''' % resp.json()['value']
                                )
                        else:
                            logger.warning(
                                'Could not fetch results from: %s'
                                % result_url
                            )
                    except KeyError as err:
                        logger.warning('Unable to find %s in JSON.' % err)

                    messages = ('''The results for this assessment are '''
                                '''attached to this feedback.''')
                    self.__post_feedback(workitem, jobid, messages, attach)
                    self.__finish(workitem_id, REQUEST)
                elif job_status == 'esriJobFailed':
                    workitem.addEvent('%s job id %s for %s failed.'
                                      % (self.app_name, jobid, envelope_url))
                    messages = (
                        "Your delivery didn't pass validation."
                    )
                    if data:
                        attach = StringIO()
                        for item in data.get('messages'):
                            attach.write('%s: %s\n' % (
                                item.get('type'), item.get('description')))
                        attach.flush()
                        attach.seek(0)
                        attach.filename = 'output.log'
                    self.__post_feedback(workitem, jobid, messages, attach)
                    self.__finish(workitem_id, REQUEST)
                elif job_status == 'esriJobExecuting':
                    workitem.addEvent('%s job id %s for %s is still running.'
                                      % (self.app_name, jobid, envelope_url))
                    self.__decrease_retries(workitem, REQUEST)
                else:
                    workitem.addEvent('%s job id %s for %s has status %s.'
                                      % (self.app_name, jobid, envelope_url,
                                         job_status))
                    self.__decrease_retries(workitem, REQUEST)
            else:
                workitem.addEvent('%s job id %s for %s output is invalid.'
                                  % (self.app_name, jobid, envelope_url))
                self.__finish(workitem_id, REQUEST)
        else:
            workitem.addEvent(
                '%s job id %s for %s returned invalid status code %s.'
                % (self.app_name, jobid, envelope_url, resp.status_code))
            self.__finish(workitem_id, REQUEST)

    def __initialize(self, p_workitem_id):
        """ Adds REST-QA specific extra properties to the workitem """
        workitem = getattr(self, p_workitem_id)
        setattr(workitem, self.app_name, {})
        storage = getattr(workitem, self.app_name)
        storage.update({
            'jobid': None,
            'retries_left': self.nRetries,
            'last_error': None,
            'next_run': DateTime()
        })

    def __update(self, workitem_id, values):
        workitem = getattr(self, workitem_id)
        getattr(workitem, self.app_name).update(values)
        workitem._p_changed = 1

    def __decrease_retries(self, workitem, REQUEST):
        getattr(workitem, self.app_name)['retries_left'] -= 1
        workitem._p_changed = 1
        if getattr(workitem, self.app_name)['retries_left'] == 0:
            self.__finish(workitem.id, REQUEST)

    def __post_feedback(self, workitem, jobid, messages, attach=None):
        envelope = self.aq_parent
        feedback_id = '{0}_{1}'.format(self.app_name, jobid)
        envelope.manage_addFeedback(
            id=feedback_id,
            file=attach,
            title='%s results' % self.app_name,
            activity_id=workitem.activity_id,
            automatic=1,
            feedbacktext=messages
        )

    def __finish(self, workitem_id, REQUEST=None):
        """ Completes the workitem and forwards it """
        self.activateWorkitem(workitem_id, actor='openflow_engine')
        self.completeWorkitem(
            workitem_id, actor='openflow_engine', REQUEST=REQUEST)


InitializeClass(RemoteRESTApplication)
