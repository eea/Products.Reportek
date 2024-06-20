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

#     $Id$

import base64
import json
import logging
import re

import constants
import Converter
import Globals
import requests
import StringIO
import xmlrpclib
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens
from OFS.Folder import Folder
from zExceptions import Redirect

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.config import (
    LOCAL_CONVERTERS_HOST,
    LOCAL_CONVERTERS_PORT,
    LOCAL_CONVERTERS_SCHEME,
)
from Products.Reportek.exceptions import LocalConversionException

__doc__ = """
The Converters is used to make different type of conversions of the Report
Documents.

There are two types of converters: Local and Remote. The remote only handles
XML files and there must be an XML schema. To find out which remote
convertersions are available, Reportek calls
http://converters.eionet.europa.eu/RpcRouter via XML-RPC.
"""
detection_log = logging.getLogger(__name__ + ".detection")


class Converters(Folder):
    """ """

    meta_type = "Reportek Converters"
    icon = "misc_/Reportek/Converters"

    # security stuff
    security = ClassSecurityInfo()

    manage_options = (
        Folder.manage_options[:2]
        + ({"label": "Remote converters", "action": "manage_converters_html"},)
        + Folder.manage_options[3:-2]
    )

    meta_types = ({"name": "Converter", "action": "manage_addConverterForm"},)
    all_meta_types = meta_types

    manage_addConverterForm = Converter.manage_addConverterForm
    manage_addConverter = Converter.manage_addConverter

    security.declareProtected(view_management_screens, "index_html")
    index_html = PageTemplateFile("zpt/converters/index", globals())

    security.declareProtected(
        view_management_screens, "manage_converters_html"
    )
    manage_converters_html = PageTemplateFile("zpt/converters/edit", globals())

    security.declareProtected(view_management_screens, "remote_converters")
    remote_converters = PageTemplateFile("zpt/converters/remote", globals())

    def __init__(self):
        """ """
        self.id = constants.CONVERTERS_ID
        self.remote_converter = "http://converters.eionet.europa.eu/RpcRouter"
        self.api_url = "http://converters.eionet.europa.eu/api"

    def __getitem__(self, attr):
        try:
            available_ids = requests.get(
                "{0}list".format(self.get_local_http_converters_url())
            ).json()["list"]
            if attr in available_ids:
                url = "%s%s" % (
                    self.get_local_http_converters_url(),
                    "params/%s" % attr,
                )
                attrs = requests.get(url).json()
                return Converter.LocalHttpConverter(**attrs).__of__(self)
            else:
                raise KeyError
        except requests.exceptions.ConnectionError as err:
            raise LocalConversionException(err.message)

    security.declareProtected(view_management_screens, "manage_edit")

    def manage_edit(self, remote_converter, api_url, REQUEST=None):
        """ """
        self.remote_converter = remote_converter
        self.api_url = api_url
        if REQUEST:
            message = "Content changed"
            return self.manage_converters_html(
                self, REQUEST, manage_tabs_message=message
            )

    def get_local_http_converters_url(self):
        return "%s://%s:%s/" % (
            LOCAL_CONVERTERS_SCHEME,
            LOCAL_CONVERTERS_HOST,
            LOCAL_CONVERTERS_PORT,
        )

    def _http_params(self, exclude_internal=False):
        url = self.get_local_http_converters_url() + "params"
        resp = requests.get(url)
        result = resp.json()["list"]
        if exclude_internal:
            # Exclude converters that are for internal usage only
            result = [c for c in result if not c[-1]]
        return result

    def _get_local_converters(self, exclude_internal=False):
        local_converters = []
        for attrs in self._http_params(exclude_internal=exclude_internal):
            conv = Converter.LocalHttpConverter(*attrs).__of__(self)
            local_converters.append(conv)
        return local_converters

    def ajax_remote_converters(self):
        """ """
        convs = self._get_remote_converters()
        return self.remote_converters(convs=convs)

    def _get_remote_converters(self, doc_schema=None):
        """ """
        try:
            server = xmlrpclib.ServerProxy(self.remote_converter)
            # acording to "Architectural and Detailed Design for GDEM
            # under IDA/EINRC/SA6/AIT"
            if doc_schema:
                return server.ConversionService.listConversions(doc_schema)
            else:
                return server.ConversionService.listConversions()
        except Exception:
            return []

    def getConvertersDescriptions(self, include_remote=True):
        """Loops all local and remote converters for display."""
        if not include_remote:
            return [self._get_local_converters()]
        return [self._get_local_converters(), self._get_remote_converters()]

    def get_remote_converters_for_schema(self, doc_schema):
        remote_converters = []
        for c in self._get_remote_converters(doc_schema):
            c["more_info"] = ""
            remote_converters.append(c)
        return remote_converters

    security.declarePublic("displayPossibleConversions")

    def displayPossibleConversions(
        self, contentType, doc_schema="", filename="", exclude_internal=False
    ):
        """Finds the converters available for a type of document."""
        local_converters = []
        remote_converters = []
        # Drop everything up to period.
        filesuffix = filename[filename.find(".") + 1 :]
        if filesuffix == "":
            filesuffix = "totally-unlikely-suffix."
        # Find in list of local converters
        try:
            available_local_converters = self._get_local_converters(
                exclude_internal=exclude_internal
            )
        except requests.ConnectionError as ex:
            if doc_schema:
                remote_converters = self.get_remote_converters_for_schema(
                    doc_schema
                )
            ex.results = (local_converters, remote_converters)
            raise ex
        possible_good_converters = ""
        for conv_obj in available_local_converters:
            if (
                contentType in conv_obj.ct_input
                or conv_obj.suffix == filesuffix
            ):
                if doc_schema:
                    if conv_obj.ct_schema:
                        if conv_obj.ct_schema == doc_schema:
                            local_converters.append(
                                {
                                    "xsl": conv_obj.id,
                                    "description": conv_obj.title,
                                    "content_type_out": conv_obj.ct_output,
                                    "more_info": conv_obj.description,
                                }
                            )
                    else:
                        local_converters.append(
                            {
                                "xsl": conv_obj.id,
                                "description": conv_obj.title,
                                "content_type_out": conv_obj.ct_output,
                                "more_info": conv_obj.description,
                            }
                        )
                else:
                    if conv_obj.ct_schema == "":
                        local_converters.append(
                            {
                                "xsl": conv_obj.id,
                                "description": conv_obj.title,
                                "content_type_out": conv_obj.ct_output,
                                "more_info": conv_obj.description,
                            }
                        )
                if (
                    contentType
                    and (contentType != "application/octet-stream")
                    and contentType not in conv_obj.ct_input
                    and filesuffix == conv_obj.suffix
                ):
                    # Getting here means:
                    # (contentType and no matching converter) and
                    # (jundging by the file extension there are converters
                    # available):
                    possible_good_converters += "%s\n" % conv_obj.id

        if (
            possible_good_converters.strip()
            and contentType not in constants.IGNORED_MIME_TYPES
        ):
            message = (
                'No converter found based on this mime-type "%s",\n'
                'but there are converters able to handle this extension "%s".'
                "\nPerhaps you should consider adding this mime-type to "
                "one or more of these converters: \n"
                "%s" % (contentType, filesuffix, possible_good_converters)
            )
            detection_log.warning(message)

        # Only look in remotes if schema is not empty
        if doc_schema:
            remote_converters = self.get_remote_converters_for_schema(
                doc_schema
            )
        return local_converters, remote_converters

    def valid_local_ids(self):
        return [conv.id for conv in self._get_local_converters()]

    def valid_converter(self, converter_id, source):
        # NOTE no validation for remote source
        if (
            converter_id == "default"
            or source not in ["local", "remote"]
            or (
                source == "local"
                and converter_id not in self.valid_local_ids()
            )
        ):
            return False
        else:
            return True

    def convertDocument(
        self, file_url="", converter_id="", output_file_name="", REQUEST=None
    ):
        """Proxy to run_conversion for API compatibility."""
        name = REQUEST.get("conv", converter_id)
        regex_result = re.match("(loc|rem)_(\w+$)", name)
        if regex_result:
            flag, _id = regex_result.groups()
            if flag == "rem":
                source = "remote"
            elif flag == "loc":
                source = "local"
        else:
            _id = "default"
            source = None
        REQUEST.set("file", REQUEST.get("file", file_url))
        REQUEST.set("conv", _id)
        REQUEST.set("source", source)
        return self.run_conversion(REQUEST=REQUEST)

    security.declarePublic("run_conversion")

    def run_conversion(
        self,
        file_url="",
        converter_id="",
        source="",
        ajax_call=None,
        REQUEST=None,
    ):
        """ """
        if REQUEST:
            source = REQUEST.get("source", source)
            file_url = REQUEST.get("file", file_url)
            converter_id = REQUEST.get("conv", converter_id)

        if not self.valid_converter(converter_id, source):
            raise Redirect(file_url)

        if source == "local":
            for conv in self._get_local_converters():
                if conv.id == converter_id:
                    result = conv(file_url, converter_id)
                    if ajax_call:
                        if "image" in result.content_type:
                            data = base64.b64encode(result.content)
                        json_data = {
                            "mime_type": result.content_type,
                            "content": data,
                        }
                        REQUEST.RESPONSE.setHeader(
                            "Content-Type", "application/json"
                        )
                        return json.dumps(json_data)
                    self.REQUEST.RESPONSE.setStatus(
                        result.status_code, result.reason
                    )
                    self.REQUEST.RESPONSE.setHeader(
                        "Content-Type", result.content_type
                    )
                    return result.content

        if source == "remote":
            return self.run_remote_conversion(file_url, converter_id)

    security.declarePublic("run_remote_conversion")

    def run_remote_conversion(
        self, file_url, converter_id, write_to_response=True
    ):
        conv = Converter.RemoteConverter(converter_id).__of__(self)
        return conv(file_url, write_to_response=write_to_response)


Globals.InitializeClass(Converters)
