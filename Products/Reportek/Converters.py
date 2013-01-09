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

__doc__ = """
The Converters is used to make different type of conversions of the Report Documents.

There are two types of converters: Local and Remote. The remote only handles XML files
and there must be an XML schema. To find out which remote convertersions are available,
Reportek calls http://converters.eionet.europa.eu/RpcRouter via XML-RPC.
"""
#     $Id$

import os
import xmlrpclib
import requests
import string
import logging
import base64
import json

from OFS.Folder import Folder
from AccessControl import getSecurityManager, ClassSecurityInfo, Unauthorized
from AccessControl.Permissions import view_management_screens, view
from zExceptions import Redirect
import Globals

import Converter
import RepUtils
import constants

detection_log = logging.getLogger(__name__ + '.detection')

class Converters(Folder):
    """ """
    meta_type = "Reportek Converters"
    icon = 'misc_/Reportek/Converters'

    #security stuff
    security = ClassSecurityInfo()

    manage_options = (
        Folder.manage_options[:2]
        +
        (
            {'label' : 'Remote converters', 'action' : 'manage_converters_html'},
        )
        +
        Folder.manage_options[3:-2]
    )

    meta_types = ({'name': 'Converter', 'action': 'manage_addConverterForm'},)
    all_meta_types = meta_types

    manage_addConverterForm = Converter.manage_addConverterForm
    manage_addConverter = Converter.manage_addConverter

    security.declareProtected(view_management_screens, 'index_html')
    index_html = Globals.DTMLFile('dtml/convertersIndex', globals())

    security.declareProtected(view_management_screens, 'manage_converters_html')
    manage_converters_html = Globals.DTMLFile('dtml/convertersEdit', globals())

    security.declareProtected(view_management_screens, 'remote_converters')
    remote_converters = Globals.DTMLFile('dtml/convertersRemoteTable', globals())

    def __init__(self):
        """ """
        self.id = constants.CONVERTERS_ID
        self.remote_converter = "http://converters.eionet.europa.eu/RpcRouter"

    def __setstate__(self, state):
        """ update """
        Converters.inheritedAttribute('__setstate__')(self, state)
        if not hasattr(self, 'remote_converter'):
            self.remote_converter = "http://converters.eionet.europa.eu/RpcRouter"

    security.declareProtected(view_management_screens, 'manage_edit')
    def manage_edit(self, remote_converter, REQUEST=None):
        """ """
        self.remote_converter = remote_converter
        if REQUEST:
            message="Content changed"
            return self.manage_converters_html(self,REQUEST,manage_tabs_message=message)

    def get_local_http_converters_url(self):
        return 'http://localhost:5000/'  # TODO configure via os.environ

    def _http_params(self):
        url = self.get_local_http_converters_url() + 'params'
        resp = requests.get(url)
        return resp.json['list']

    def _get_local_converters(self):
        local_converters = []
        for attrs in self._http_params():
            conv = Converter.LocalHttpConverter(*attrs).__of__(self)
            local_converters.append(conv)
        return local_converters

    """
    def _get_local_converters(self):
        """ """
        return self.objectIds()
    """

    def ajax_remote_converters(self):
        """ """
        convs = self._get_remote_converters()
        return self.remote_converters(convs=convs)

    def _get_remote_converters(self, doc_schema=None):
        """ """
        try:
            server = xmlrpclib.ServerProxy(self.remote_converter)
            #acording to "Architectural and Detailed Design for GDEM under IDA/EINRC/SA6/AIT"
            if doc_schema:
                return server.ConversionService.listConversions(doc_schema)
            else:
                return server.ConversionService.listConversions()
        except:
            return []

    def getConvertersDescriptions(self, include_remote=True):
        """ Loops all local and remote converters for display. """
        if not include_remote:
            return [self._get_local_converters()]
        return [self._get_local_converters(), self._get_remote_converters()]

    def get_remote_converters_for_schema(self, doc_schema):
        remote_converters = []
        for c in self._get_remote_converters(doc_schema):
            c['more_info'] = ''
            remote_converters.append(c)
        return remote_converters

    security.declarePublic('displayPossibleConversions')
    def displayPossibleConversions(self, contentType, doc_schema='', filename=''):
        """ Finds the converters available for a type of document. """
        local_converters = []
        remote_converters = []
        filesuffix = filename[filename.find('.')+1:] # Drop everything up to period.
        if filesuffix == '': filesuffix='totally-unlikely-suffix.'
        # Find in list of local converters
        try:
            available_local_converters = self._get_local_converters()
        except requests.ConnectionError as ex:
            if doc_schema:
                remote_converters = self.get_remote_converters_for_schema(doc_schema)
            ex.results=(local_converters, remote_converters)
            raise ex
        possible_good_converters = ''
        for conv_obj in available_local_converters:
            if contentType in conv_obj.ct_input or conv_obj.suffix == filesuffix:
                if doc_schema:
                    if conv_obj.ct_schema:
                        if conv_obj.ct_schema == doc_schema:
                            local_converters.append({'xsl':conv_obj.id,
                               'description':conv_obj.title,
                               'content_type_out': conv_obj.ct_output,
                               'more_info': conv_obj.description})
                    else:
                        local_converters.append({'xsl':conv_obj.id,
                           'description':conv_obj.title,
                           'content_type_out': conv_obj.ct_output,
                           'more_info': conv_obj.description})
                else:
                    if conv_obj.ct_schema == '':
                        local_converters.append({'xsl':conv_obj.id,
                           'description':conv_obj.title,
                           'content_type_out': conv_obj.ct_output,
                           'more_info': conv_obj.description})
                if (contentType and
                    (contentType != 'application/octet-stream') and
                    contentType not in conv_obj.ct_input and
                    filesuffix == conv_obj.suffix):
                    # Getting here means:
                    # (contentType and no matching converter) and
                    # (jundging by the file extension there are converters available):
                    possible_good_converters+=('%s\n' %conv_obj.id)

        if possible_good_converters.strip():
            message = (
                'No converter found based on this mime-type "%s",\n'
                'but there are converters able to handle this extension "%s".\n'
                'Perhaps you should consider adding this mime-type to '
                'one or more of these converters: \n'
                '%s' %(contentType, filesuffix, possible_good_converters))
            detection_log.warning(message)

        # Only look in remotes if schema is not empty
        if doc_schema:
            remote_converters = self.get_remote_converters_for_schema(doc_schema)
        return local_converters, remote_converters

    def valid_local_ids(self):
        return [conv.id for conv in self._get_local_converters()]

    def valid_converter(self, converter_id, source):
        #NOTE no validation for remote source
        if (converter_id == 'default' or
            source not in ['local', 'remote'] or
            (source == 'local' and converter_id not in self.valid_local_ids())):
            return False
        else:
            return True

    def convertDocument(self, file_url='', converter_id='', output_file_name='', REQUEST=None):
        """Proxy to run_conversion for API compatibility."""
        flag = REQUEST.get('conv', converter_id)[:3]
        _id = REQUEST.get('conv', converter_id)[4:]
        REQUEST.set('file_url', REQUEST.get('file', file_url))
        if flag == 'rem':
            source = 'remote'
        elif flag == 'loc':
            source = 'local'
        REQUEST.set('conv', _id)
        REQUEST.set('source', source)
        return self.run_conversion(REQUEST=REQUEST)

    security.declarePublic('run_conversion')
    def run_conversion(self, file_url='', converter_id='', source='',
                       ajax_call=None, REQUEST=None):
        """ """
        if REQUEST:
            source = REQUEST.get('source', source)
            file_url = REQUEST.get('file', file_url)
            converter_id = REQUEST.get('conv', converter_id)

        if not self.valid_converter(converter_id, source):
            raise Redirect, file_url

        if source == 'local':
            for conv in self._get_local_converters():
                if conv.id == converter_id:
                    data = conv(file_url, converter_id)
                    if ajax_call:
                        if 'image' in conv.ct_output:
                            data = base64.b64encode(conv(file_url, converter_id))
                        json_data = {'mime_type': conv.ct_output,
                                    'content': data}
                        REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
                        return json.dumps(json_data)
                    return data

        if source == 'remote':
            conv = Converter.RemoteConverter(converter_id).__of__(self)
            return conv(file_url)



Globals.InitializeClass(Converters)
