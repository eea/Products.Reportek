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

## RemoteApplication
##

import requests
from DateTime import DateTime

from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem


manage_addRemoteRESTApplicationForm = PageTemplateFile('zpt/RemoteRESTApplicationAdd',globals())


def manage_addRemoteRESTApplication(self, id='', title='', ServiceSubmitURL='', ServiceCheckURL='', app_name='', REQUEST=None):
    """ Generic application that calls a remote REST service """

    ob = RemoteRESTApplication(id, title, ServiceSubmitURL, ServiceCheckURL, app_name)
    self._setObject(id, ob)

    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class RemoteRESTApplication(SimpleItem):

    security = ClassSecurityInfo()
    meta_type = 'Remote REST Application'

    def __init__(self, id, title, ServiceSubmitURL, ServiceCheckURL, app_name, nRetries=5, retryFrequency=300, nTimeBetweenCalls=60):
        """ Initialize a new instance of Document """
        self.id = id
        self.title = title
        self.ServiceSubmitURL = ServiceSubmitURL
        self.ServiceCheckURL = ServiceCheckURL
        self.app_name = app_name
        self.nRetries = nRetries                    # integer
        self.retryFrequency = retryFrequency        # integer - seconds
        self.nTimeBetweenCalls = nTimeBetweenCalls  # integer - seconds

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
                    workitem.addEvent('%s job request for %s successfully submited.'
                                       % (self.app_name, envelope_url))
            else:
                workitem.addEvent('%s job request for %s response is invalid.'
                                   % (self.app_name, envelope_url))
        else:
            workitem.addEvent('%s job request for %s returned invalid status code %s.'
                               % (self.app_name, envelope_url, resp.status_code))

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
                if job_status == 'esriJobSucceeded':
                    messages = data['messages']
                    workitem.addEvent('%s job id %s for %s successfully finished.'
                                       % (self.app_name, jobid, envelope_url))
                    self.__post_feedback(workitem, jobid)
                    self.__finish(workitem_id, REQUEST)
                elif job_status == 'esriJobFailed':
                    workitem.addEvent('%s job id %s for %s failed.'
                                       % (self.app_name, jobid, envelope_url))
                    self.__finish(workitem_id, REQUEST)
                elif job_status == 'esriJobExecuting':
                    workitem.addEvent('%s job id %s for %s is still running.'
                                       % (self.app_name, jobid, envelope_url))
                else:
                    workitem.addEvent('%s job id %s for %s has status %s.'
                       % (self.app_name, jobid, envelope_url, job_status))
            else:
                workitem.addEvent('%s job id %s for %s output is invalid.'
                                   % (self.app_name, jobid, envelope_url))
        else:
            workitem.addEvent('%s job id %s for %s returned invalid status code %s.'
                               % (self.app_name, jobid, envelope_url, resp.status_code))

    def __initialize(self, p_workitem_id):
        """ Adds REST-QA specific extra properties to the workitem """
        workitem = getattr(self, p_workitem_id)
        setattr(workitem, self.app_name, {})
        storage = getattr(workitem, self.app_name)
        storage.update({
            'jobid': None,
            'retries_left': self.nRetries,
            'last_error':None,
            'next_run':DateTime()
        })

    def __update(self, workitem_id, values):
        workitem = getattr(self, workitem_id)
        getattr(workitem, self.app_name).update(values)

    def __post_feedback(self, workitem, jobid):
        envelope = self.aq_parent
        feedback_id = self.app_name + '_' + str(jobid) + '_' + str(int(DateTime()))
        envelope.manage_addFeedback(id=feedback_id,
                title= self.app_name + str(jobid),
                activity_id=workitem.activity_id,
                automatic=1)

    def __finish(self, workitem_id, REQUEST=None):
        """ Completes the workitem and forwards it """
        self.activateWorkitem(workitem_id, actor='openflow_engine')
        self.completeWorkitem(workitem_id, actor='openflow_engine', REQUEST=REQUEST)

InitializeClass(RemoteRESTApplication)
