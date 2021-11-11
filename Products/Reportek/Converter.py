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

from conversion_registry import request_params
from RepUtils import extension
import blob
import string
import requests
import os
import constants
import RepUtils
import Globals
from copy import deepcopy
from Products.Reportek.blob import StorageError
from ZODB.POSException import POSKeyError
from zExceptions import Redirect
from RestrictedPython.Eval import RestrictionCapableEval
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl.Permissions import view_management_screens, view
from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from OFS.SimpleItem import SimpleItem
__doc__ = """
      Converter product module.
      The Converter defines a conversion from one type of file to another

      $Id$
"""
__version__ = '$Rev$'[6:-2]


manage_addConverterForm = PageTemplateFile(
    'zpt/converters/item_add', globals())


def manage_addConverter(self, id, title='', convert_url='', ct_input='',
                        ct_output='', ct_schema='', ct_extraparams='',
                        description='', suffix='', REQUEST=None):
    """ add a new converter object """
    ob = Converter(id, title, convert_url, ct_input, ct_output, ct_schema,
                   RepUtils.utConvertLinesToList(ct_extraparams), description,
                   suffix)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class Converter(SimpleItem):
    """ """
    meta_type = "Converter"

    manage_options = (
        (
            {'label': 'Settings', 'action': 'manage_settings_html'},
        )
        +
        SimpleItem.manage_options
    )

    def __init__(self, id, title, convert_url, ct_input, ct_output, ct_schema,
                 ct_extraparams, description, suffix='', internal=False):
        """ """
        self.id = id
        self.title = title
        self.convert_url = convert_url
        self.ct_input = ct_input
        self.ct_output = ct_output
        self.ct_schema = ct_schema
        self.ct_extraparams = ct_extraparams
        self.description = description
        # Drop everything up to period.
        self.suffix = suffix[suffix.find('.')+1:]
        self.internal = internal

    # security stuff
    security = ClassSecurityInfo()

    security.declareProtected(view_management_screens, 'manage_settings')

    def manage_settings(self, title='', ct_input='', ct_output='',
                        ct_schema='', convert_url='', ct_extraparams='',
                        description='', suffix='', internal=False,
                        REQUEST=None):
        """ """
        self.title = title
        self.convert_url = convert_url
        self.ct_input = ct_input
        self.ct_output = ct_output
        self.ct_schema = ct_schema
        self.ct_extraparams = RepUtils.utConvertLinesToList(ct_extraparams)
        self.description = description
        # Drop everything up to period.
        self.suffix = suffix[suffix.find('.')+1:]
        self.internal = internal
        self._p_changed = 1
        if REQUEST:
            message = "Content changed."
            return self.manage_settings_html(self, REQUEST,
                                             manage_tabs_message=message)

    security.declareProtected(view_management_screens, 'getExtraParameters')

    def getExtraParameters(self):
        """ """
        return RepUtils.utConvertListToLines(self.ct_extraparams)

    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = PageTemplateFile(
        'zpt/converters/item_edit', globals())

    def __call__(self, file_url, converter_id, output_file_name='',
                 REQUEST=None):
        file_obj = self.getPhysicalRoot().restrictedTraverse(file_url, None)
        if not getSecurityManager().checkPermission(view, file_obj):
            raise Unauthorized('You are not authorized to view this document')
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
            raise Redirect(file_obj.absolute_url())
        if converter_obj.ct_output == "flash":
            self.REQUEST.RESPONSE.redirect(
                "%s/%s" % (file_obj.absolute_url(), converter_obj.convert_url))
        if converter_obj.ct_output and not converter_obj.ct_output == "flash":
            self.REQUEST.RESPONSE.setHeader(
                'Content-Type', converter_obj.ct_output)

            # generate 'filename'
            if not output_file_name:
                if converter_obj.ct_output in constants.CONTENT_TYPES.keys():
                    output_file_name = "%s%s" % (
                        file_obj.id[:file_obj.id.rfind('.')],
                        constants.CONTENT_TYPES[converter_obj.ct_output])
                else:
                    output_file_name = "convertDocument"

            with file_obj.data_file.open() as doc_file:
                tmp_copy = RepUtils.temporary_named_copy(doc_file)

            with tmp_copy:
                # generate extra-parameters
                # the file path is set default as first parameter
                params = [tmp_copy.name]
                eval_map = {
                    'file_obj': file_obj,
                    'converter_obj': converter_obj,
                    'REQUEST': self.REQUEST,
                }
                for k in converter_obj.ct_extraparams:
                    eval_res = RestrictionCapableEval(k).eval(eval_map)
                    params.append(eval_res)

                command = converter_obj.convert_url % tuple(params)
                data = os.popen(command).read()

            self.REQUEST.RESPONSE.setHeader(
                'Content-Disposition',
                'inline; filename=%s' % output_file_name)
            return data

        else:
            self.REQUEST.RESPONSE.setHeader('Content-Type', 'text/plain')
            return 'Converter error'


class RemoteConverter(Converter):

    def __init__(self, converter_id):
        super(Converter, self).__init__(converter_id)
        self.id = converter_id

    def __call__(self, file_url, write_to_response=True):
        file_obj = self.getPhysicalRoot().restrictedTraverse(file_url, None)
        if not getSecurityManager().checkPermission(view, file_obj):
            raise Unauthorized('You are not authorized to view this document')

        if write_to_response:
            converter = self.convert
        else:
            converter = self.convert_for_script

        return converter(file_obj)

    def _do_conversion(self, file_url):
        url = '/'.join([self.api_url, 'convert'])
        data = dict(convert_id=self.id, url=file_url)
        return requests.post(url, data=data)

    def convert_for_script(self, file_obj):
        result = self._do_conversion(file_obj.absolute_url())
        result.raise_for_status()
        return result.content

    def convert(self, file_obj):
        try:
            result = self._do_conversion(file_obj.absolute_url())
            result.raise_for_status()
            headers = deepcopy(result.headers)
            # Let Zope add the transfer-encoding: chuncked header if
            # required (that is if the connection is not closed, so there is
            # more to come).

            # TODO what if the requests does not decode payload?
            # it handles chunked and gzip automatically, but what
            # about the rest?

            if headers.get('Transfer-Encoding'):
                headers.pop('Transfer-Encoding')
            # Due to https://taskman.eionet.europa.eu/issues/96712. The recent
            # changes to converters allow the converters to return gzip
            # content.
            # However, requests automatically decompresses the content and we
            # need to replace the 'Content-Encoding' value with none.
            if headers.get('Content-Encoding') == 'gzip':
                headers['Content-Encoding'] = 'none'
            self.REQUEST.RESPONSE.headers.update(headers)
            for chunk in result.iter_content(chunk_size=64*1024):
                self.REQUEST.RESPONSE.write(chunk)
            return self.REQUEST.RESPONSE

        except Exception as error:
            self.REQUEST.SESSION.set('note_title', 'Error in conversion')
            if isinstance(error, requests.HTTPError):
                message = result.text
            else:
                l_tmp = string.maketrans('<>', '  ')
                message = str(error).translate(l_tmp)
            message.replace(r'\n', '<br />')
            self.REQUEST.SESSION.set('note_text', (
                'The operation could not be completed because of '
                'the following error:<br /><br />%s'
            ) % message
            )
            self.REQUEST.SESSION.set(
                'redirect_to', self.REQUEST['HTTP_REFERER']
            )
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
            try:
                return data_file.open()
            except (POSKeyError, StorageError):
                return ''
        else:
            return file_obj

    def convert(self, file_obj, converter_id, extra_params=None):
        url = '%s%s' % (self.get_local_http_converters_url(), self.convert_url)
        # We could have a valid '' here
        if extra_params is None:
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
        resp = requests.post(url, files=files,
                             data={'extraparams': extra_params})

        response = ConversionResult(resp)
        return response


Globals.InitializeClass(Converter)
