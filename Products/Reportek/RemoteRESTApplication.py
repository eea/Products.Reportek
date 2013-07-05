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
import os

#http://test.discomap.eea.europa.eu/arcgis/rest/services/Article17QAQCToolBeta/GPServer/Article17QAQCToolBeta/submitJob

class RemoteRESTApplication():

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

    def __call__(self, envelope_url):
        params = {
            'EnvelopeURL': envelope_url,
            'f': 'pjson',
        }

        resp = requests.get(self.ServiceSubmitURL, params=params)

        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                raise Exception, 'response is not json'
            if data and 'jobId' in data:
                job_id = data['jobId']
                job_status = data['jobStatus']
                if job_status == 'esriJobSubmitted':
                    pass
            else:
                raise Exception, 'invalid response'
        else:
            raise Exception, 'invalid status code'

    def get(self, jobid):
        params = {
            'f': 'pjson',
        }

        resp = requests.get(self.ServiceCheckURL + jobid, params=params)

        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                raise Exception, 'response is not json'
            if data and 'jobId' in data:
                job_status = data['jobStatus']
                if job_status == 'esriJobSucceeded':
                    messages = data['messages']
                    return messages
                elif job_status == 'esriJobFailed':
                    raise Exception, 'job failed'
                elif job_status == 'esriJobExecuting':
                    raise Exception, 'job not done'
                else:
                    raise Exception, job_status
            else:
                raise Exception, 'invalid response'
        else:
            raise Exception, 'invalid status code'
