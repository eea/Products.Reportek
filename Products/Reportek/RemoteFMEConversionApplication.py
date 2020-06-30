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

## RemoteFMEConversionApplication
##

import json
import logging
import re
from datetime import datetime, timedelta
from StringIO import StringIO
from urlparse import urlparse

import requests
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from DateTime import DateTime
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

logger = logging.getLogger(__name__ + '.FME')

manage_addRemoteFMEConversionApplicationForm = PageTemplateFile('zpt/RemoteFMEConversionApplicationAdd',globals())


def manage_addRemoteFMEConversionApplication(self, id='', title='',
                                             FMEServer='',
                                             FMETokenEndpoint='',
                                             FMEToken=None,
                                             FMEUser='',
                                             FMEPassword='',
                                             FMETokenExpiration='',
                                             FMETokenTimeUnit='minute',
                                             FMEUploadEndpoint='',
                                             FMEUploadDir='',
                                             FMETransformation='',
                                             FMEUploadParams=None,
                                             FMEUploadAll=False,
                                             FMEFileTypes=None,
                                             FMEWorkspace='',
                                             FMEWorkspaceParams=None,
                                             FMEConvCleanup=True,
                                             retryFrequency=300,
                                             app_name='', REQUEST=None):
    """ Generic application that calls a remote FME service """

    ob = RemoteFMEConversionApplication(id, title, FMEServer,
                                        FMETokenEndpoint, FMEToken, FMEUser,
                                        FMEPassword, FMETokenExpiration,
                                        FMETokenTimeUnit, FMEUploadEndpoint,
                                        FMEUploadDir, FMETransformation,
                                        FMEUploadParams, FMEFileTypes,
                                        FMEUploadAll, FMEWorkspace,
                                        FMEWorkspaceParams, FMEConvCleanup,
                                        retryFrequency, app_name)
    self._setObject(id, ob)

    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class RemoteFMEConversionApplication(SimpleItem):

    security = ClassSecurityInfo()
    meta_type = 'Remote FME Application'
    manage_options = (
        ( {'label' : 'Settings', 'action' : 'manage_settings_html'}, ) +
        SimpleItem.manage_options
    )
    UP_METHOD = 'filesys'
    DOWN_METHOD = 'downloadzip'

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = PageTemplateFile('zpt/RemoteFMEConversionApplicationSettings', globals())

    def __init__(self, id, title, FMEServer, FMETokenEndpoint,
                 FMEToken, FMEUser, FMEPassword, FMETokenExpiration,
                 FMETokenTimeUnit, FMEUploadEndpoint, FMEUploadDir,
                 FMETransformation, FMEUploadParams, FMEFileTypes,
                 FMEUploadAll, FMEWorkspace, FMEWorkspaceParams,
                 FMEConvCleanup, retryFrequency, app_name, nRetries=50):
        """ Initialize a new instance of Document """
        self.id = id
        self.title = title
        self.FMEServer = FMEServer
        self.FMETokenEndpoint = FMETokenEndpoint
        self.FMEToken = FMEToken
        self.FMEUser = FMEUser
        self.FMEPassword = FMEPassword
        self.FMETokenExpiration = FMETokenExpiration
        self.FMETokenTimeUnit = FMETokenTimeUnit
        self.FMEUploadEndpoint = FMEUploadEndpoint
        self.FMEUploadDir = FMEUploadDir
        self.FMETransformation = FMETransformation
        self.FMEUploadParams = FMEUploadParams
        self.FMEFileTypes = FMEFileTypes
        self.FMEUploadAll = FMEUploadAll
        self.FMEWorkspace = FMEWorkspace
        self.FMEWorkspaceParams = FMEWorkspaceParams
        self.FMEConvCleanup = FMEConvCleanup
        self.retryFrequency = retryFrequency
        self.app_name = app_name
        self.nRetries = int(nRetries)                    # integer

    def manage_settings(self, REQUEST):
        """ Change properties of the FME Application """
        self.title = REQUEST.form.get('title')
        self.FMEServer = REQUEST.form.get('FMEServer')
        self.FMETokenEndpoint = REQUEST.form.get('FMETokenEndpoint')
        self.FMEToken = REQUEST.form.get('FMEToken')
        self.FMEUser = REQUEST.form.get('FMEUser')
        self.FMEPassword = REQUEST.form.get('FMEPassword')
        self.FMETokenExpiration = REQUEST.form.get('FMETokenExpiration')
        self.FMETokenTimeUnit = REQUEST.form.get('FMETokenTimeUnit')
        self.FMEUploadEndpoint = REQUEST.form.get('FMEUploadEndpoint')
        self.FMEUploadDir = REQUEST.form.get('FMEUploadDir')
        self.FMETransformation = REQUEST.form.get('FMETransformation')
        self.FMEUploadParams = REQUEST.form.get('FMEUploadParams')
        self.FMEFileTypes = REQUEST.form.get('FMEFileTypes')
        self.FMEUploadAll = bool(REQUEST.form.get('FMEUploadAll', False))
        self.FMEWorkspace = REQUEST.form.get('FMEWorkspace')
        self.FMEWorkspaceParams = REQUEST.form.get('FMEWorkspaceParams')
        self.FMEConvCleanup = bool(REQUEST.form.get('FMEConvCleanup', False))
        self.retryFrequency = REQUEST.form.get('retryFrequency')
        self.app_name = REQUEST.form.get('app_name')
        self.nRetries = int(REQUEST.form.get('nRetries'))
        if REQUEST is not None:
            return self.manage_settings_html(manage_tabs_message='Saved changes.')

    def get_fme_token(self):
        """Retrieves the token from FME"""
        res = {}
        params = {
            'user': self.FMEUser,
            'password': self.FMEPassword,
            'expiration': self.FMETokenExpiration,
            'timeunit': self.FMETokenTimeUnit
        }
        t_unit = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }
        offset = int(self.FMETokenExpiration) * t_unit.get(self.FMETokenTimeUnit)
        expires = DateTime(datetime.now() + timedelta(seconds=offset))
        try:
            resp = requests.post('/'.join([self.FMEServer, self.FMETokenEndpoint]),
                                 params=params)
            if resp.ok:
                res['token'] = resp.content
                res['expires'] = expires

            else:
                logger.error('FME authentication request failed. Could not retrieve token: {}-{}'.format(resp.status_code, resp.content))
        except Exception as e:
            logger.error('FME authentication request failed. Could not retrieve token: {}'.format(str(e)))

        return res

    def get_token(self, workitem_id):
        """Retrieves the workitem stored token"""
        workitem = getattr(self, workitem_id)
        # If we have explicit FMEToken, override the auto token generation
        if self.FMEToken:
            return {'token': self.FMEToken}
        token = getattr(workitem, '__token', {})
        expires = token.get('expires')
        if not expires or expires <= DateTime():
            # No token or token expired
            token = self.get_fme_token()
            if token:
                setattr(workitem, '__token', token)
                workitem._p_changed = 1
        return getattr(workitem, '__token', None)

    def get_files(self, workitem_id):
        """Returns the file structure needed for requests upload"""
        workitem = getattr(self, workitem_id)
        env = workitem.getMySelf()
        files = []
        if not self.FMEUploadAll:
            for f_ext in self.FMEFileTypes.splitlines():
                files.extend([f for f in env.objectValues('Report Document')
                              if f.title_or_id().lower().endswith('.' + f_ext.lower())])
        else:
            files = env.objectValues('Report Document')

        return files

    def get_auth_header(self, workitem_id):
        token = self.get_token(workitem_id)
        if token:
            return {"Authorization": "fmetoken token={}".format(token.get('token'))}
        return {}

    def get_headers(self, workitem_id):
        headers = self.get_auth_header(workitem_id)
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        return headers

    def get_env_path_tokenized(self, workitem_id):
        """Return tokenized envelope path."""
        workitem = getattr(self, workitem_id)
        return workitem.getMySelf().getPath().replace('/', '_')[1:]

    def handle_cleanup(self, workitem_id):
        """ Delete the temporary folder on FME."""
        workitem = getattr(self, workitem_id)
        if self.FMEConvCleanup:
            url = '/'.join([self.FMEServer,
                            self.FMEUploadEndpoint,
                            self.UP_METHOD,
                            self.FMEUploadDir,
                            self.get_env_path_tokenized(workitem_id)])
            try:
                headers = self.get_headers(workitem_id)
                res = requests.delete(url, headers=headers)
                if res.status_code == 204:
                    self.__update_storage(workitem, 'cleanup',
                                          status='completed')
            except Exception as e:
                self.__update_storage(workitem, 'cleanup',
                                      err=e,
                                      status='failed',
                                      dec_retry=True)

    def handle_res_zip_download(self, workitem_id):
        """Download the result files as zip"""
        workitem = getattr(self, workitem_id)
        env = workitem.getMySelf()
        url = '/'.join([self.FMEServer,
                        self.FMEUploadEndpoint,
                        self.DOWN_METHOD,
                        self.FMEUploadDir,
                        self.get_env_path_tokenized(workitem_id),
                        'output'])
        params = {
            'zipFileName': 'resources.zip',
            'fileNames': '.'
        }
        headers = self.get_headers(workitem_id)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers['Accept'] = 'application/zip'
        res = requests.post(url, params=params, headers=headers)
        if res.status_code == 200:
            z = StringIO(res.content)
            z.filename = 'resources.zip'
            env.manage_addDDzipfile(file=z)

    def upload_to_fme(self, workitem_id):
        """Upload the file(s) to the fme data upload"""
        workitem = getattr(self, workitem_id)
        upload_storage = getattr(workitem, self.app_name, {}).get('upload')
        if upload_storage.get('retries_left'):
            url = '/'.join([self.FMEServer,
                            self.FMEUploadEndpoint,
                            self.UP_METHOD,
                            self.FMEUploadDir])
            params = {}
            if self.FMEUploadParams:
                for p in self.FMEUploadParams.splitlines():
                    k = p.split(':')[0].strip()
                    v = p.split(':')[1].strip()
                    params[k] = v
            files = self.get_files(workitem_id)
            files = [('files', (f.title_or_id(), f.data_file.open('rb'))) for f in files]
            tokenized_folder = self.get_env_path_tokenized(workitem_id)
            url = '/'.join([url, tokenized_folder])
            try:
                headers = self.get_headers(workitem_id)
                # We need to explicitly remove the content-type on file upload
                del headers['Content-Type']
                res = requests.post(url, params=params,
                                    files=files, headers=headers)
                if res.status_code == 200:
                    srv_res = res.json()
                    if isinstance(srv_res, list):
                        paths = [f.get('name').encode('utf-8')
                                 for f in srv_res]
                        self.__update_storage(workitem, 'upload',
                                              paths=paths, status='completed')

                else:
                    err = 'HTTP: {}: {}'.format(res.status_code, res.content)
                    self.__update_storage(workitem, 'upload',
                                          err=err, dec_retry=True)
            except Exception as e:
                self.__update_storage(workitem, 'upload',
                                      status='failed',
                                      err=e, dec_retry=True)
            # Close the files
            for file in files:
                file[-1][-1].close()

    def get_uploaded_files(self, workitem_id, single_file=False, shapefile=False, zipped=False):
        """Return a list of uploaded files"""
        workitem = getattr(self, workitem_id)
        env = workitem.getMySelf()
        upload_storage = getattr(workitem, self.app_name, {}).get('upload')
        if single_file and upload_storage['paths']:
            return upload_storage['paths'][-1]
        if shapefile and upload_storage['paths']:
            for p in reversed(upload_storage['paths']):
                if (not zipped and p.endswith('.shp')) or (zipped and p.endswith('.zip')):
                    gmls = [fid.split('.')[0] for fid in env.objectIds('Report Document')
                            if fid.endswith('.gml')]
                    if not [x for x in gmls if p.split('.')[0] in x]:
                        return p
        return upload_storage['paths']

    def execute_workspace(self, workitem_id):
        """ Execute the workspace"""
        workitem = getattr(self, workitem_id)
        results = getattr(workitem, self.app_name, {}).get('results')
        url = '/'.join([self.FMEServer, self.FMETransformation,
                        self.FMEWorkspace])
        wks_params = {}
        # Load the params setup on an application level
        if self.FMEWorkspaceParams:
            file_list = [f.absolute_url() for f in self.get_files(workitem_id)]
            wks_params = self.FMEWorkspaceParams.format(GET_FILES_URLS=file_list,
                                                        GET_FILES=self.get_uploaded_files(workitem_id),
                                                        GET_FILE=self.get_uploaded_files(workitem_id, single_file=True),
                                                        GET_SHAPEFILE=self.get_uploaded_files(workitem_id, shapefile=True),
                                                        GET_ZIPPEDSHAPEFILE=self.get_uploaded_files(workitem_id, shapefile=True, zipped=True),
                                                        ENVPATHTOKENIZED=self.get_env_path_tokenized(workitem_id))
            wks_params = json.loads(wks_params.replace("'", '"'))
        try:
            # params should be passed in the body of the request
            res = requests.post(url, data=json.dumps(wks_params), headers=self.get_headers(workitem_id))
            if res.status_code == 202:
                # submission successful, response looks like:
                # res.json()
                # {u'id': 989126}
                # If we posted multiple files, do we get a single ID back? expecting a mail response to this
                results[res.json().get('id')] = {
                    'retries_left': self.nRetries,
                    'last_error': None,
                    'next_run': DateTime(),
                    'status': 'pending'
                }
                self.__update_storage(workitem, 'fmw_exec', status='completed')
            else:
                err = 'HTTP: {}: {}'.format(res.status_code, res.content)
                self.__update_storage(workitem, 'fmw_exec',
                                      status='retry',
                                      err=err, dec_retry=True)
        except Exception as e:
            self.__update_storage(workitem, 'fmw_exec',
                                  status='retry',
                                  err=e, dec_retry=True)

    def poll_results(self, workitem_id):
        """Polls for results"""
        # https://fme.discomap.eea.europa.eu/fmerest/v3/transformations/jobs/id/<job_id>
        workitem = getattr(self, workitem_id)
        results = getattr(workitem, self.app_name, {}).get('results')
        rest_endpoint = 'fmerest/v3/transformations/jobs/id'
        if results:
            for job_id in results.keys():
                if results[job_id].get('status') not in ['completed', 'failed'] and results[job_id].get('retries_left'):
                    url = '/'.join([self.FMEServer, rest_endpoint, str(job_id)])
                    try:
                        res = requests.get(url, headers=self.get_headers(workitem_id))
                        if res.status_code == 200:
                            fme_status = {
                                'SUBMITTED': '',
                                'QUEUED': '',
                                'ABORTED': '',
                                'SUCCESS': '',
                                'FME_FAILURE': '',
                                'JOB_FAILURE': '',
                                'PULLED': ''
                            }
                            response = res.json()
                            fme_status = response.get('status')
                            retry = [
                                'SUBMITTED',
                                'QUEUED',
                                'DELAYED',
                                'PAUSED',
                                'IN_PROCESS',
                                'PULLED'
                            ]
                            abort = [
                                'DELETED',
                                'ABORTED',
                                'FME_FAILURE',
                                'JOB_FAILURE'
                            ]
                            if fme_status == 'SUCCESS':
                                if response.get('result'):
                                    job_status = response['result'].get('status')
                                    if job_status == 'SUCCESS':
                                        try:
                                            self.handle_res_zip_download(workitem_id)
                                            self.__post_feedback(workitem, job_id, 'Conversion successful')
                                            self.__update_storage(workitem, 'results',
                                                                  jobid=job_id,
                                                                  status='completed')
                                        except Exception as e:
                                            self.__update_storage(workitem, 'results',
                                                                  jobid=job_id,
                                                                  status='retry',
                                                                  err=e, dec_retry=True)
                            elif fme_status in retry:
                                err = 'FME Status: {}. Re-scheduled for polling'.format(fme_status)
                                self.__update_storage(workitem, 'results',
                                                      jobid=job_id,
                                                      status='retry',
                                                      err=err, dec_retry=True)
                            elif fme_status in abort:
                                err = 'FME Status: {}. Aborting'.format(fme_status)
                                self.__update_storage(workitem, 'results',
                                                      jobid=job_id,
                                                      status='failed',
                                                      err=err, dec_retry=True)
                                self.__post_feedback(workitem, job_id, 'Conversion failed, aborting')

                    except Exception as e:
                        self.__update_storage(workitem, 'results',
                                              jobid=job_id,
                                              status='retry',
                                              err=e, dec_retry=True)

    def __call__(self, workitem_id, REQUEST=None):
        workitem = getattr(self, workitem_id)

        # Initialize the workitem FME Conversion specific extra properties
        self.__initialize(workitem_id)
        envelope_url = workitem.getMySelf().absolute_url(0)
        self.upload_to_fme(workitem_id)
        upload_storage = getattr(workitem, self.app_name, {}).get('upload')
        if upload_storage.get('status') == 'completed':
            self.execute_workspace(workitem_id)

    security.declareProtected('Use OpenFlow', 'callApplication')
    def callApplication(self, workitem_id, REQUEST):
        workitem = getattr(self, workitem_id)
        envelope_url = workitem.getMySelf().absolute_url(0)
        storage = getattr(workitem, self.app_name, {})
        upload_storage = storage.get('upload')
        results = storage.get('results')
        fmw_exec = storage.get('fmw_exec')
        if upload_storage.get('status') != 'completed' and upload_storage.get('retries_left'):
            self.upload_to_fme(workitem_id)
        elif upload_storage.get('status') != 'completed' and not upload_storage.get('retries_left'):
            self.__post_feedback(workitem, 'upload', 'Conversion failed, aborting')
            self.__finish(workitem_id)
        if upload_storage.get('status') == 'completed':
            if fmw_exec.get('status') != 'completed' and fmw_exec.get('retries_left'):
                self.execute_workspace(workitem_id)
            elif fmw_exec.get('status') != 'completed' and not fmw_exec.get('retries_left'):
                self.__post_feedback(workitem, 'fmw_exec', 'Conversion failed, aborting')
                self.__finish(workitem_id)
        if results:
            poll = [j for j in results
                    if results[j].get('status') not in ['completed', 'failed']]
            if poll:
                self.poll_results(workitem_id)
            else:
                self.handle_cleanup(workitem_id)
                self.__finish(workitem_id)

    def __initialize(self, p_workitem_id):
        """ Adds FME-QA specific extra properties to the workitem """
        workitem = getattr(self, p_workitem_id)
        setattr(workitem, self.app_name, {})
        storage = getattr(workitem, self.app_name)

        if not self.FMEToken:
            token = self.get_fme_token()

            if token:
                setattr(workitem, '__token', token)
                workitem._p_changed = 1

        storage.update({
            'upload': {
                'retries_left': self.nRetries,
                'last_error': None,
                'next_run': DateTime(),
                'status': 'pending'
            },
            'fmw_exec': {
                'retries_left': self.nRetries,
                'last_error': None,
                'next_run': DateTime(),
                'status': 'pending'
            },
            'results': {},
            'cleanup': {
                'retries_left': self.nRetries,
                'last_error': None,
                'next_run': DateTime(),
                'status': 'pending'
            }
        })

    def __update_storage(self, workitem, step, paths=None, jobid=None,
                         status=None, err=None, dec_retry=False):
        if jobid and step == 'results':
            storage = getattr(workitem, self.app_name)[step][jobid]
        else:
            storage = getattr(workitem, self.app_name)[step]
        if paths:
            storage['paths'] = paths
        if dec_retry:
            storage['retries_left'] -= 1
        if err:
            storage['last_error'] = str(err)
        if status:
            storage['status'] = status
        storage['next_run'] = DateTime(int(storage['next_run']) +
                                       int(self.retryFrequency))
        workitem._p_changed = 1

    def __post_feedback(self, workitem, jobid, messages, attach=None):
        envelope = self.aq_parent
        feedback_id = '{0}_{1}'.format(self.app_name, jobid)
        envelope.manage_addFeedback(id=feedback_id, file=attach,
                                    title='%s results' % self.app_name,
                                    activity_id=workitem.activity_id,
                                    automatic=1,
                                    feedbacktext=messages)

    def __finish(self, workitem_id, REQUEST=None):
        """ Completes the workitem and forwards it """
        self.activateWorkitem(workitem_id, actor='openflow_engine')
        self.completeWorkitem(workitem_id, actor='openflow_engine', REQUEST=REQUEST)


InitializeClass(RemoteFMEConversionApplication)
