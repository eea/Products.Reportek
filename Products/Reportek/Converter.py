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
# Cornel Nitu, Eau de Web

__doc__ = """
      Converter product module.
      The Converter defines a conversion from one type of file to another

      $Id$
"""
__version__='$Rev$'[6:-2]

from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from AccessControl.Permissions import view_management_screens, view
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from zExceptions import Redirect
import Globals
import RepUtils
import constants
import os
import re
import requests
import string
import xmlrpclib

import blob
from RepUtils import extension
from conversion_registry import request_params

manage_addConverterForm = PageTemplateFile('zpt/converters/item_add', globals())

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

    def __init__(self, id, title, convert_url, ct_input, ct_output, ct_schema, ct_extraparams, description, suffix=''):
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
            self.setstate = True
            self.ct_schema = ''
        if not hasattr(self, 'ct_extraparams'):
            self.setstate = True
            self.ct_extraparams = ''
        if not hasattr(self, 'description'):
            self.setstate = True
            self.description = ''
        if not hasattr(self, 'suffix'):
            self.setstate = True
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
    manage_settings_html = PageTemplateFile('zpt/converters/item_edit', globals())

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
            url = '/'.join([self.api_url, 'convertPush'])
            with file_obj.data_file.open() as f:
                result = requests.post(
                            url,
                            files={'convert_file': (file_obj.id, f)},
                            data={'convert_id': self.id,
                                  'file_name': file_obj.absolute_url(0)},
                            stream=True)
            result.raise_for_status()
            #
            # let zope add the transfer-encoding: chuncked header if required
            # (that is if the connection is not closed so there is more to come)
            # TODO what if the requests does not decode payload?
            # it handles chunked and gzip automatically, but what about the rest?
            #
            # result.headers is a case insensitive dict
            #
            if result.headers.get('transfer-encoding'):
                result.headers.pop('transfer-encoding')
            self.REQUEST.RESPONSE.headers.update(result.headers)
            for chunk in result.iter_content(chunk_size=64*1024):
                self.REQUEST.RESPONSE.write(chunk)
            return self.REQUEST.RESPONSE

        except Exception, error:
            self.REQUEST.SESSION.set('note_title', 'Error in conversion')
            l_tmp = string.maketrans('<>', '  ')
            message = str(error).translate(l_tmp)
            if type(error) == type(requests.HTTPError()):
                message = result.text
            message.replace(r'\n','<br />')
            self.REQUEST.SESSION.set('note_text',
                'The operation could not be completed because of the following error:<br /><br />%s' %message)
            self.REQUEST.SESSION.set('redirect_to', self.REQUEST['HTTP_REFERER'])
            return file_obj.note()


class ConversionResult(object):

    def __init__(self, response):
        self.original_response = response
        self.status_code = response.status_code
        self.reason = response.reason
        self.content_type = response.headers['content-type']

    @property
    def text(self):
        return self.original_response.text

    @property
    def content(self):
        return self.original_response.content


class LocalHttpConverter(Converter):

    def __init__(self, *args, **kwargs):
        super(LocalHttpConverter, self).__init__(*args, **kwargs)
        if not self.suffix:
            self.suffix = extension(self.ct_input)

    def get_file_data(self, file_obj):
        data_file = getattr(file_obj, 'data_file', None)
        if (data_file and isinstance(data_file, blob.FileContainer)):
            return data_file.open()
        else:
            return file_obj

    def convert(self, file_obj, converter_id):
        url = '%s%s' % (self.get_local_http_converters_url(), self.convert_url)
        extra_params = request_params(self.ct_extraparams, obj=file_obj)
        data = self.get_file_data(file_obj)
        files = {'file': data}
        accepts_shp = any(map(lambda item: 'shp' in item, self.ct_input))
        if (accepts_shp):
            shp_container = file_obj.aq_parent
            file_name = file_obj.id.split('.')[0]
            shx_file = shp_container.unrestrictedTraverse(
                                        '.'.join([file_name, 'shx']))
            dbf_file = shp_container.unrestrictedTraverse(
                                        '.'.join([file_name, 'dbf']))
            files['shx'] = self.get_file_data(shx_file)
            files['dbf'] = self.get_file_data(dbf_file)
        resp = requests.post(
                   url,
                   files=files,
                   data={'extraparams': extra_params})

        response = ConversionResult(resp)
        return response


Globals.InitializeClass(Converter)
