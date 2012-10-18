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
      Converter product module.
      The Converter define a conversion type
      .

      $Id$
"""
__version__='$Rev$'[6:-2]

from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from AccessControl.Permissions import view_management_screens, view
from zExceptions import Redirect
import Globals
import RepUtils
import constants
import os
import requests
import string
import xmlrpclib

manage_addConverterForm = Globals.DTMLFile('dtml/converterAdd', globals())

def manage_addConverter(self, id, title='', convert_url='', ct_input='', ct_output='', ct_schema='', ct_extraparams='', description='', suffix='', REQUEST=None):
    """ add a new converter object """
    ob = Converter(id, title, convert_url, ct_input, ct_output, ct_schema, RepUtils.utConvertLinesToList(ct_extraparams), description, suffix)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)

class Converter(SimpleItem):
    """ """
    meta_type = "Converter"

    manage_options = (
        (
            {'label' : 'Settings', 'action' : 'manage_settings_html'},
        )
        +
        SimpleItem.manage_options
    )

    def __init__(self, id, title, convert_url, ct_input, ct_output, ct_schema, ct_extraparams, description, suffix):
        """ """
        self.id = id
        self.title = title
        self.convert_url = convert_url
        self.ct_input = ct_input
        self.ct_output = ct_output
        self.ct_schema = ct_schema
        self.ct_extraparams = ct_extraparams
        self.description = description
        self.suffix = suffix[suffix.find('.')+1:] # Drop everything up to period.

    def __setstate__(self, state):
        """ update """
        Converter.inheritedAttribute('__setstate__')(self, state)
        if not hasattr(self, 'ct_schema'):
            self.ct_schema = ''
        if not hasattr(self, 'ct_extraparams'):
            self.ct_extraparams = ''
        if not hasattr(self, 'description'):
            self.description = ''
        if not hasattr(self, 'suffix'):
            self.suffix = ''

    #security stuff
    security = ClassSecurityInfo()

    security.declareProtected(view_management_screens, 'manage_settings')
    def manage_settings(self, title='', ct_input='', ct_output='', ct_schema='', convert_url='', ct_extraparams='', description='', suffix='', REQUEST=None):
        """ """
        self.title = title
        self.convert_url = convert_url
        self.ct_input = ct_input
        self.ct_output = ct_output
        self.ct_schema = ct_schema
        self.ct_extraparams = RepUtils.utConvertLinesToList(ct_extraparams)
        self.description = description
        self.suffix = suffix[suffix.find('.')+1:] # Drop everything up to period.
        self._p_changed = 1
        if REQUEST:
            message="Content changed."
            return self.manage_settings_html(self,REQUEST,manage_tabs_message=message)

    security.declareProtected(view_management_screens, 'getExtraParameters')
    def getExtraParameters(self):
        """ """
        return RepUtils.utConvertListToLines(self.ct_extraparams)

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = Globals.DTMLFile('dtml/converterEdit', globals())

    def __call__(self, file_url, converter_id, output_file_name='', REQUEST=None):
        file_obj = self.getPhysicalRoot().restrictedTraverse(file_url, None)
        if not getSecurityManager().checkPermission(view, file_obj):
            raise Unauthorized, ('You are not authorized to view this document')
        args = [file_obj, converter_id]
        if output_file_name:
            args.append(output_file_name)
        return self.convert(*args)

    def convert(self, file_obj, converter_id='', output_file_name=''):
        converter_obj = getattr(self, converter_id, None)

        if file_obj is None or converter_obj is None:
            self.REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
            return 'Converter error'
        if file_obj.content_type[0:6] == 'image/':
            raise Redirect, file_obj.absolute_url()
        if converter_obj.ct_output == "flash":
            self.REQUEST.RESPONSE.redirect("%s/%s" % (file_obj.absolute_url(), converter_obj.convert_url))
        if converter_obj.ct_output and not converter_obj.ct_output == "flash":
            self.REQUEST.RESPONSE.setHeader('Content-Type', converter_obj.ct_output)

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

            self.REQUEST.RESPONSE.setHeader('Content-Disposition',
                                'inline; filename=%s' % output_file_name)
            return data

        else:
            self.REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
            return 'Converter error'


class RemoteConverter(Converter):

    def __init__(self, converter_id):
        super(Converter, self).__init__(converter_id)
        self.id = converter_id

    def __call__(self, file_url):
        file_obj = self.getPhysicalRoot().restrictedTraverse(file_url, None)
        if not getSecurityManager().checkPermission(view, file_obj):
            raise Unauthorized, ('You are not authorized to view this document')
        return self.convert(file_obj)

    def convert(self, file_obj):
        try:
            server = xmlrpclib.ServerProxy(self.remote_converter)
            #acording to "Architectural and Detailed Design for GDEM under IDA/EINRC/SA6/AIT"
            result = server.ConversionService.convert(file_obj.absolute_url(0), self.id)
            self.REQUEST.RESPONSE.setHeader('Content-Type', result['content-type'])
            self.REQUEST.RESPONSE.setHeader('Content-Disposition', 'inline;filename="%s"' % result['filename'])
            return result['content'].data
        except Exception, error:
            self.REQUEST.SESSION.set('note_title', 'Error in conversion')
            l_tmp = string.maketrans('<>', '  ')
            self.REQUEST.SESSION.set('note_text', 'The operation could not be completed because of the following error:<br /><br />%s' %str(error).translate(l_tmp).replace(r'\n','<br />'))
            self.REQUEST.SESSION.set('redirect_to', self.REQUEST['HTTP_REFERER'])
            return file_obj.note()


class LocalHttpConverter(Converter):

    def convert(self, file_obj, converter_id):
        url = '%s%s' % (self.get_local_http_converters_url(), self.convert_url)
        resp = requests.post(url, data=file_obj.data_file.open())
        self.REQUEST.RESPONSE.setStatus(resp.status_code, resp.reason)
        self.REQUEST.RESPONSE.setHeader('Content-Type', self.ct_output)
        return resp.content

Globals.InitializeClass(Converter)
