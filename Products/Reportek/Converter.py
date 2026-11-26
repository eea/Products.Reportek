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

import re
from copy import deepcopy

import requests
from AccessControl import ClassSecurityInfo, Unauthorized, getSecurityManager
from AccessControl.class_init import InitializeClass
from AccessControl.Permissions import view, view_management_screens
from OFS.SimpleItem import SimpleItem
from zExceptions import BadRequest
from ZODB.POSException import POSKeyError

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.blob import StorageError

from . import RepUtils, blob
from .conversion_registry import request_params

__doc__ = """
      Converter product module.
      The Converter defines a conversion from one type of file to another

      $Id$
"""
__version__ = "$Rev$"[6:-2]

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://")
_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def _strip_hop_by_hop_headers(headers):
    """Remove HTTP hop-by-hop headers before copying to a WSGI response."""
    connection_tokens = {
        token.strip().lower()
        for header, value in headers.items()
        if header.lower() == "connection"
        for token in value.split(",")
        if token.strip()
    }
    blocked_headers = _HOP_BY_HOP_HEADERS | connection_tokens
    # the headers are removed from the mapping, so they are listed first
    blocked = [header for header in headers if header.lower() in blocked_headers]
    for header in blocked:
        headers.pop(header, None)
    return headers


def validate_file_url(file_url):
    """Reject file URLs that point to external resources (SSRF prevention).

    Only relative Zope paths are allowed. Absolute URLs with a scheme
    (e.g. http://, https://, ftp://) are rejected.
    """
    if file_url and isinstance(file_url, str) and _SCHEME_RE.match(file_url):
        raise BadRequest("External URLs are not allowed in the file parameter.")


# Converter objects can no longer be added through the web: their convert_url
# ran as a shell command on the Zope host. Local conversions come from the
# local-converters service (Converters._get_local_converters).


class Converter(SimpleItem):
    """ """

    meta_type = "Converter"

    manage_options = (
        {"label": "Settings", "action": "manage_settings_html"},
    ) + SimpleItem.manage_options

    def __init__(
        self,
        id,
        title,
        convert_url,
        ct_input,
        ct_output,
        ct_schema,
        ct_extraparams,
        description,
        suffix="",
        internal=False,
    ):
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
        self.suffix = suffix[suffix.find(".") + 1 :]
        self.internal = internal

    # security stuff
    security = ClassSecurityInfo()

    security.declareProtected(view_management_screens, "manage_settings")

    def manage_settings(
        self,
        title="",
        ct_input="",
        ct_output="",
        ct_schema="",
        convert_url="",
        ct_extraparams="",
        description="",
        suffix="",
        internal=False,
        REQUEST=None,
    ):
        """ """
        self.title = title
        self.convert_url = convert_url
        self.ct_input = ct_input
        self.ct_output = ct_output
        self.ct_schema = ct_schema
        self.ct_extraparams = RepUtils.utConvertLinesToList(ct_extraparams)
        self.description = description
        # Drop everything up to period.
        self.suffix = suffix[suffix.find(".") + 1 :]
        self.internal = internal
        self._p_changed = 1
        if REQUEST:
            message = "Content changed."
            return self.manage_settings_html(self, REQUEST, manage_tabs_message=message)

    security.declareProtected(view_management_screens, "getExtraParameters")

    def getExtraParameters(self):
        """ """
        return RepUtils.utConvertListToLines(self.ct_extraparams)

    security.declareProtected(view_management_screens, "manage_settings_html")
    manage_settings_html = PageTemplateFile("zpt/converters/item_edit.zpt", globals())

    def __call__(self, file_url, converter_id, output_file_name="", REQUEST=None):
        file_obj = self.getPhysicalRoot().restrictedTraverse(file_url, None)
        if not getSecurityManager().checkPermission(view, file_obj):
            raise Unauthorized("You are not authorized to view this document")
        args = [file_obj, converter_id]
        if output_file_name:
            args.append(output_file_name)
        return self.convert(*args)

    def convert(self, file_obj, converter_id="", output_file_name=""):
        # This used to run convert_url as a shell command on the Zope host,
        # with ct_extraparams evaluated as Python. Conversions now run only in
        # the local-converters service (LocalHttpConverter) or remotely
        # (RemoteConverter), which override this.
        raise NotImplementedError(
            "In-process conversion was removed; use the local-converters "
            "service or a remote converter."
        )


class RemoteConverter(Converter):
    def __init__(self, converter_id):
        self.id = converter_id

    def __call__(self, file_url, write_to_response=True):
        file_obj = self.getPhysicalRoot().restrictedTraverse(file_url, None)
        if not getSecurityManager().checkPermission(view, file_obj):
            raise Unauthorized("You are not authorized to view this document")

        if write_to_response:
            converter = self.convert
        else:
            converter = self.convert_for_script

        return converter(file_obj)

    def _do_conversion(self, file_url, stream=False):
        url = "/".join([self.api_url, "convert"])
        data = dict(convert_id=self.id, url=file_url)
        return requests.post(url, data=data, stream=stream)

    def convert_for_script(self, file_obj):
        result = self._do_conversion(file_obj.absolute_url())
        result.raise_for_status()
        return result.content

    def convert(self, file_obj):
        result = None
        try:
            result = self._do_conversion(file_obj.absolute_url(), stream=True)
            result.raise_for_status()
            headers = deepcopy(result.headers)
            # Let Zope add the transfer-encoding: chuncked header if
            # required (that is if the connection is not closed, so there is
            # more to come).

            # TODO what if the requests does not decode payload?
            # it handles chunked and gzip automatically, but what
            # about the rest?

            _strip_hop_by_hop_headers(headers)
            # Due to https://taskman.eionet.europa.eu/issues/96712. The recent
            # changes to converters allow the converters to return gzip
            # content.
            # However, requests automatically decompresses the content and we
            # need to replace the 'Content-Encoding' value with none.
            if headers.get("Content-Encoding", "").lower() not in ("", "identity"):
                # requests decodes gzip, deflate, ...: the content is not
                # encoded anymore and it has not the length of the encoded one
                headers["Content-Encoding"] = "none"
                headers.pop("Content-Length", None)
            # Zope and the server add their own
            for header in ("Date", "Server"):
                headers.pop(header, None)
            self.REQUEST.RESPONSE.headers.update(headers)
            # RESPONSE.write() does not stream under WSGI, the converted
            # file would be kept in memory until the request is done
            return RepUtils.StreamIterator(
                result.iter_content(chunk_size=64 * 1024), result.close
            )

        except Exception as error:
            self.REQUEST.SESSION.set("note_title", "Error in conversion")
            if isinstance(error, requests.HTTPError):
                message = result.text
            else:
                l_tmp = str.maketrans("<>", "  ")
                message = str(error).translate(l_tmp)
            message.replace(r"\n", "<br />")
            self.REQUEST.SESSION.set(
                "note_text",
                (
                    "The operation could not be completed because of "
                    "the following error:<br /><br />%s"
                )
                % message,
            )
            self.REQUEST.SESSION.set("redirect_to", self.REQUEST["HTTP_REFERER"])
            if result is not None:
                result.close()
            return file_obj.note()


class ConversionResult(object):
    def __init__(self, response):
        self.original_response = response
        self.status_code = response.status_code
        self.reason = response.reason
        self.content_type = response.headers["content-type"]

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
            self.suffix = RepUtils.extension(self.ct_input)

    def get_file_data(self, file_obj):
        data_file = getattr(file_obj, "data_file", None)
        if data_file and isinstance(data_file, blob.FileContainer):
            try:
                return data_file.open()
            except (POSKeyError, StorageError):
                return ""
        else:
            return file_obj

    def convert(self, file_obj, converter_id, extra_params=None):
        url = "%s%s" % (self.get_local_http_converters_url(), self.convert_url)
        # We could have a valid '' here
        if extra_params is None:
            extra_params = request_params(self.ct_extraparams, obj=file_obj)
        data = self.get_file_data(file_obj)
        files = {"file": data}
        file_handles = [data] if hasattr(data, "close") else []
        accepts_shp = any(["shp" in item for item in self.ct_input])
        if accepts_shp:
            shp_container = file_obj.aq_parent
            file_name = file_obj.id.split(".")[0]
            shx_file = shp_container.unrestrictedTraverse(".".join([file_name, "shx"]))
            dbf_file = shp_container.unrestrictedTraverse(".".join([file_name, "dbf"]))
            shx_data = self.get_file_data(shx_file)
            dbf_data = self.get_file_data(dbf_file)
            files["shx"] = shx_data
            files["dbf"] = dbf_data
            if hasattr(shx_data, "close"):
                file_handles.append(shx_data)
            if hasattr(dbf_data, "close"):
                file_handles.append(dbf_data)
        try:
            resp = requests.post(url, files=files, data={"extraparams": extra_params})
            response = ConversionResult(resp)
            return response
        finally:
            for fh in file_handles:
                fh.close()


InitializeClass(Converter)
