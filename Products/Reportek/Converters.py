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
import string

from OFS.Folder import Folder
from AccessControl import getSecurityManager, ClassSecurityInfo, Unauthorized
from AccessControl.Permissions import view_management_screens, view
from zExceptions import Redirect
import Globals

import Converter
import RepUtils
import constants

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

    def _get_local_converters(self):
        """ """
        return self.objectValues('Converter')

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

    def getConvertersDescriptions(self):
        """ Loops all local and remote converters for display. """
        return [self._get_local_converters(), self._get_remote_converters()]

    security.declarePublic('displayPossibleConversions')
    def displayPossibleConversions(self, contentType, doc_schema='', filename=''):
        """ Finds the converters available for a type of document. """
        local_converters = []
        remote_converters = []
        filesuffix = filename[filename.find('.')+1:] # Drop everything up to period.
        if filesuffix == '': filesuffix='totally-unlikely-suffix.'
        # Find in list of local converters
        for conv_obj in self._get_local_converters():
            if conv_obj.ct_input == contentType or conv_obj.suffix == filesuffix:
                if doc_schema:
                    if conv_obj.ct_schema == doc_schema:
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
        # Only look in remotes if schema is not empty
        if doc_schema:
            for c in self._get_remote_converters(doc_schema):
                c['more_info'] = ''
                remote_converters.append(c)
        return local_converters, remote_converters

    security.declarePublic('convertDocument')
    def convertDocument(self, file_url='', converter_id='', output_file_name='', REQUEST=None):
        """ Converts the document at the file_url. converter_id must start with 'default', 'loc\_' or 'rem\_'.
        """
        file_url = REQUEST.get('file', file_url)
        converter_id = REQUEST.get('conv', converter_id)

        file_obj = self.unrestrictedTraverse(file_url, None)
        if not getSecurityManager().checkPermission(view, file_obj):
            raise Unauthorized, ('You are not authorized to view this document')
        if converter_id == 'default':
            raise Redirect, file_obj.absolute_url()

        if converter_id[:4] == "loc_":
            converter_obj = getattr(self, converter_id.replace("loc_", ""), None)

            if file_obj is None or converter_obj is None:
                REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
                return 'Converter error'
            if file_obj.content_type[0:6] == 'image/':
                raise Redirect, file_obj.absolute_url()
            if converter_obj.ct_output == "flash":
                REQUEST.RESPONSE.redirect("%s/%s" % (file_obj.absolute_url(), converter_obj.convert_url))
            if converter_obj.ct_output and not converter_obj.ct_output == "flash":
                REQUEST.RESPONSE.setHeader('Content-Type', converter_obj.ct_output)

                #generate 'filename'
                if not output_file_name:
                    if converter_obj.ct_output in constants.CONTENT_TYPES.keys():
                        output_file_name = "%s%s" % (file_obj.id[:file_obj.id.rfind('.')], constants.CONTENT_TYPES[converter_obj.ct_output])
                    else:
                        output_file_name = "convertDocument"

                with file_obj.data_file.open() as doc_file:
                    tmp_copy = RepUtils.temporary_named_copy(doc_file)

                with tmp_copy:
                    #generate extra-parameters
                    #the file path is set default as first parameter
                    params = [tmp_copy.name]
                    for k in converter_obj.ct_extraparams:
                        params.append(eval(k))

                    command = converter_obj.convert_url % tuple(params)
                    data = os.popen(command).read()

                REQUEST.RESPONSE.setHeader('Content-Disposition',
                                    'inline; filename=%s' % output_file_name)
                return data

            else:
                REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
                return 'Converter error'

        elif converter_id[:4] == "rem_":
            try:
                server = xmlrpclib.ServerProxy(self.remote_converter)
                #acording to "Architectural and Detailed Design for GDEM under IDA/EINRC/SA6/AIT"
                result = server.ConversionService.convert(file_obj.absolute_url(0), converter_id.replace("rem_", ""))
                REQUEST.RESPONSE.setHeader('Content-Type', result['content-type'])
                REQUEST.RESPONSE.setHeader('Content-Disposition', 'inline;filename="%s"' % result['filename'])
                return result['content'].data
            except Exception, error:
                REQUEST.SESSION.set('note_title', 'Error in conversion')
                l_tmp = string.maketrans('<>', '  ')
                REQUEST.SESSION.set('note_text', 'The operation could not be completed because of the following error:<br /><br />%s' %str(error).translate(l_tmp).replace(r'\n','<br />'))
                REQUEST.SESSION.set('redirect_to', REQUEST['HTTP_REFERER'])
                return file_obj.note()
        else:
            raise 'Redirect', file_obj.absolute_url()

Globals.InitializeClass(Converters)
