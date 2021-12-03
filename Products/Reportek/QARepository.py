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
# Agency (EEA).  Portions created by Finsiel are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Cornel Nitu, Finsiel Romania

import shlex
import subprocess

import constants
import Globals
import QAScript
import RepUtils
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from OFS.Folder import Folder
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.constants import ENGINE_ID
from RestrictedPython.Eval import RestrictionCapableEval

__doc__ = """
      QARepository product module.
      The QARepository is used to make different type of quality assurance
      checks of the Report Documents.
"""


class QARepository(Folder):
    """ """
    meta_type = 'Reportek QARepository'
    icon = 'misc_/Reportek/QARepository'

    # security stuff
    security = ClassSecurityInfo()

    def __init__(self):
        """ """
        self.id = constants.QAREPOSITORY_ID
        self.QA_application = 'EnvelopeQAApplication'

    meta_types = (
        {'name': 'QAScript', 'action': 'manage_addQAScriptForm'},)
    all_meta_types = meta_types

    manage_addQAScriptForm = QAScript.manage_addQAScriptForm
    manage_addQAScript = QAScript.manage_addQAScript

    manage_options = (
        Folder.manage_options[:2]
        +
        (
            {'label': 'Remote QA Scripts', 'action': 'manage_qascripts_html'},
        )
        +
        Folder.manage_options[3:-2]
    )

    def getQAApplication(self):
        """Default to the AutomaticQA application setup in the properties"""
        aqa_path = self.QA_application
        try:
            env = self.getMySelf()
            process = env.getProcess()
            if 'AutomaticQA' in process.listActivities():
                aqa_act = getattr(process, 'AutomaticQA')
                aqa_path = aqa_act.mapped_application_details()['path']
        except Exception:
            pass

        return self.unrestrictedTraverse(aqa_path, None)

    def _get_local_qa_scripts(self, p_schema=None, dataflow_uris=None,
                              content_type_in=''):
        """ """
        if p_schema and not dataflow_uris:
            return [x for x in self.objectValues('QAScript')
                    if x.xml_schema == p_schema]
        elif p_schema and dataflow_uris and not content_type_in:
            return [x for x in self.objectValues('QAScript')
                    if (getattr(x, 'workflow', None) in dataflow_uris
                        or x.xml_schema == p_schema)]
        elif p_schema and dataflow_uris and content_type_in:
            return [x for x in self.objectValues('QAScript')
                    if ((getattr(x, 'workflow', None) in dataflow_uris
                        and content_type_in == getattr(x, 'content_type_in',
                                                       None))
                        and x.xml_schema == p_schema)]
        elif dataflow_uris and content_type_in:
            return [x for x in self.objectValues('QAScript')
                    if (getattr(x, 'workflow', None) in dataflow_uris
                        and content_type_in == getattr(x, 'content_type_in',
                                                       None))]
        elif dataflow_uris and not content_type_in:
            return [x for x in self.objectValues('QAScript')
                    if (getattr(x, 'workflow', None) in dataflow_uris)]
        elif not dataflow_uris and content_type_in:
            return [x for x in self.objectValues('QAScript')
                    if (content_type_in == getattr(x, 'content_type_in',
                                                   None))]
        elif not dataflow_uris:
            return self.objectValues('QAScript')

    def _get_remote_qa_scripts(self, p_schema=''):
        """ """
        l_qa_app = self.getQAApplication()
        if not l_qa_app:
            return []
        r_scripts = l_qa_app.listQAScripts(p_schema, short=False)
        if not r_scripts:
            r_scripts = []

        return r_scripts

    def getQAScriptsDescriptions(self):
        """ Loops all local and remote QA scripts for display """
        return [self._get_local_qa_scripts(), self._get_remote_qa_scripts()]

    security.declareProtected('View', 'getQAScriptsForSchema')

    def getQAScriptsForSchema(self, p_schema):
        """ Returns the list of QA script ids available for an XML type
            Used for running the QA scripts on the envelope's 'xml' file
        """
        if not p_schema:
            return []
        l_ret = []
        # local scripts
        l_ret.extend([x.id for x in self._get_local_qa_scripts()
                      if x.xml_schema == p_schema])
        # remote scripts
        l_qa_app = self.getQAApplication()
        if l_qa_app:
            l_tmp = l_qa_app.listQAScripts(p_schema)
            if l_tmp:
                l_ret.extend([x[0] for x in l_tmp])
        return l_ret

    def getDataflowMappingsContainer(self):
        """ """
        return getattr(self, constants.DATAFLOW_MAPPINGS)

    security.declareProtected('View', 'canRunQAOnFiles')

    def canRunQAOnFiles(self, files):
        """ Returns a list of QA script labels
            which can be manually run against the contained XML files
        """
        l_ret = {}
        # calculate remote service URL
        l_qa_app = self.getQAApplication()

        for l_file in files:
            # get the valid schemas for the envelope's dataflows
            l_valid_schemas = self.getDataflowMappingsContainer(
            ).getSchemasForDataflows(l_file.dataflow_uris)
            # go on only if it's an XML file with a non-empty valid schema or
            # if no valid schemas are defined for those dataflows
            # NOTE due to updated dataflow_uris, l_valid_schemas is always None
            if ((l_file.xml_schema_location
                and (l_file.xml_schema_location in l_valid_schemas
                     or not l_valid_schemas))
                    or self._get_local_qa_scripts(
                        dataflow_uris=l_file.dataflow_uris)):
                # remote scripts
                if l_qa_app:
                    scripts = l_qa_app.listQAScripts(
                        l_file.xml_schema_location)
                    # Exclude ZIP output type - refs: 136918
                    l_ret[l_file.id] = [script for script in scripts
                                        if script[4] != 'ZIP']
                # local scripts
                l_buff = [
                    ['loc_%s' % y.id, y.title, y.bobobase_modification_time(),
                     y.max_size] for y in
                    self._get_local_qa_scripts(
                        l_file.xml_schema_location,
                        dataflow_uris=l_file.dataflow_uris,
                        content_type_in=l_file.content_type)
                ]
                if len(l_buff):
                    if l_file.id in l_ret:
                        l_ret[l_file.id].extend(l_buff)
                    else:
                        l_ret[l_file.id] = l_buff

        return l_ret

    def _runQAScript(self, p_file_url, p_script_id):
        """ Runs the QA script with the specified id against
            the source XML file

            If the id starts with 'loc_', then the script is local (Python),
            otherwise call the query service

            This method can be only called from the browser and the result is
            displayed in a temporary page
        """
        l_res_ct = 'text/plain'
        l_res_data = QAResult()
        engine = self.unrestrictedTraverse(ENGINE_ID)
        server_url = self.REQUEST.SERVER_URL
        if engine:
            http_res = getattr(engine, 'qa_httpres', False)
            if http_res:
                server_url = self.REQUEST.SERVER_URL.replace('https://',
                                                             'http://')

        # make sure p_file_url is a real Zope file
        l_file_relative_url = p_file_url.replace('%s/' % server_url, '')
        file_obj = self.unrestrictedTraverse(l_file_relative_url, None)

        if file_obj is not None:
            l_file_id = p_file_url.split('/')[-1]
            # local script
            if p_script_id.startswith('loc_'):

                l_script_obj = getattr(
                    self, p_script_id.replace('loc_', ''), None)

                if l_script_obj is None:
                    l_res_data.data = 'QA error'

                else:
                    if l_script_obj.content_type_out:
                        l_res_ct = l_script_obj.content_type_out

                        with file_obj.data_file.open() as doc_file:
                            tmp_copy = RepUtils.temporary_named_copy(doc_file)

                        with tmp_copy:
                            # generate extra-parameters
                            # the file path is set default as first parameter
                            params = [tmp_copy.name]
                            eval_map = {
                                'file_obj': file_obj,
                                'l_script_obj': l_script_obj,
                                'REQUEST': self.REQUEST,
                            }
                            for k in l_script_obj.qa_extraparams:
                                eval_res = RestrictionCapableEval(
                                    k).eval(eval_map)
                                params.append(eval_res)

                            command = l_script_obj.script_url % tuple(params)
                            proc = subprocess.Popen(
                                shlex.split(command),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                shell=False)
                            l_res_data.data = proc.stdout.read()
                    else:
                        l_res_data.data = 'QA error'

                l_tmp = [l_res_ct, l_res_data]

            # remote script
            else:
                l_qa_app = self.getQAApplication()
                if l_qa_app:
                    try:
                        l_tmp = l_qa_app.runQAScript(p_file_url, p_script_id)
                    except Exception as e:
                        l_res_data.data = 'QA error: {}'.format(str(e))
                        l_tmp = ['', l_res_data]
        else:
            # invalid or missing file
            l_file_id = ''
            l_res_data.data = 'QA error'
            l_tmp = ['', l_res_data]

        return l_file_id, l_tmp

    security.declareProtected(view_management_screens, 'manage_edit')

    def manage_edit(self, QA_application, REQUEST=None):
        """ """
        self.QA_application = QA_application
        if REQUEST:
            message = "Content changed"
            return self.manage_qascripts_html(self, REQUEST,
                                              manage_tabs_message=message)

    security.declareProtected(view_management_screens, 'manage_qascripts_html')
    manage_qascripts_html = PageTemplateFile('zpt/qa/scripts_edit', globals())

    security.declareProtected(view_management_screens, 'index_html')
    index_html = PageTemplateFile('zpt/qa/scripts_index', globals())


Globals.InitializeClass(QARepository)


class QAResult:
    """ container for QAScript results """

    def __init__(self):
        self.data = ''
