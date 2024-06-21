# -*- coding: utf-8 -*-
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
# Soren Roug, EEA

"""Generic functions module"""

# from AccessControl.PermissionRole import rolesForPermissionOn
import base64
import json
import logging
import operator
import os
import re
import string
import sys
import tempfile
import time
import traceback
from copy import deepcopy
from datetime import datetime
from urllib import FancyURLopener

from AccessControl.ImplPython import rolesForPermissionOn
from AccessControl.SecurityInfo import ModuleSecurityInfo
from AccessControl.SecurityManagement import (
    getSecurityManager,
    newSecurityManager,
    setSecurityManager,
)
from AccessControl.User import UnrestrictedUser as BaseUnrestrictedUser
from Acquisition import aq_get, aq_parent
from Acquisition.interfaces import IAcquirer
from DateTime import DateTime
from path import path
from webdav.common import rfc1123_date
from zope.component import getUtility

# from zope.datetime import rfc1123_date
from zope.interface.interfaces import ComponentLookupError

from Products.Five import BrowserView
from Products.Reportek.config import XLS_HEADINGS, ZIP_CACHE_PATH
from Products.Reportek.constants import DEFAULT_CATALOG
from Products.Reportek.permissions import reportek_dataflow_admin

security = ModuleSecurityInfo("Products.Reportek.RepUtils")

_marker = []  # Create a new marker object.
_tool_interface_registry = {}


class UnrestrictedUser(BaseUnrestrictedUser):
    """Unrestricted user that still has an id."""

    def getId(self):
        """Return the ID of the user."""
        return self.getUserName()


def formatException(self, error):
    """
    Format and return the specified exception information as a string.

    This implementation builds the complete stack trace, combining
    traceback.format_exception and traceback.format_stack.
    """
    lines = traceback.format_exception(*error)
    if error[2]:
        lines[1:1] = traceback.format_stack(error[2].tb_frame.f_back)
    return "".join(lines)


logger = logging.getLogger("Reportek.RepUtils")
# logger.setLevel(logging.DEBUG)

# logging.Formatter.formatException = formatException

bad_chars = (
    " ,+&;()[]{}\xc4\xc5\xc1\xc0\xc2\xc3"
    "\xe4\xe5\xe1\xe0\xe2\xe3\xc7\xe7\xc9\xc8\xca\xcb"
    "\xc6\xe9\xe8\xea\xeb\xe6\xcd\xcc\xce\xcf\xed\xec"
    "\xee\xef\xd1\xf1\xd6\xd3\xd2\xd4\xd5\xd8\xf6\xf3"
    "\xf2\xf4\xf5\xf8\x8a\x9a\xdf\xdc\xda\xd9\xdb\xfc"
    "\xfa\xf9\xfb\xdd\x9f\xfd\xff\x8e\x9e"
)

good_chars = (
    "___________AAAAAA"
    "aaaaaaCcEEEE"
    "EeeeeeIIIIii"
    "iiNnOOOOOOoo"
    "ooooSssUUUUu"
    "uuuYYyyZz"
)

TRANSMAP = string.maketrans(bad_chars, good_chars)


def copy_file(infile, outfile):
    """Read binary data from infile and write it to outfile
    infile and outfile may be strings, in which case a file with that
    name is opened, or filehandles, in which case they are accessed
    directly.
    """
    if isinstance(infile, str):
        instream = open(infile, "rb")
        close_in = 1
    else:
        instream = infile
        close_in = 0

    if isinstance(outfile, str):
        outstream = open(outfile, "wb")
        close_out = 1
    else:
        outstream = outfile
        close_out = 0

    blocksize = 2 << 16
    block = instream.read(blocksize)
    outstream.write(block)
    while len(block) == blocksize:
        block = instream.read(blocksize)
        outstream.write(block)
    if close_in:
        instream.close()
    if close_out:
        outstream.close()


def iter_file_data(in_file, chunk_size=131072):
    while True:
        chunk = in_file.read(chunk_size)
        if not chunk:
            break
        yield chunk


def read_file_chunked(in_file, chunk_size=131072):
    f = in_file.open("rb")
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        yield chunk
    f.close()


def cleanup_id(name):
    """Cleanup an id
    Should be more thorough and e.g. remove trailing dots/spaces
    """
    if type(name) is unicode:
        try:
            name = name.encode("ascii")
        except UnicodeEncodeError as e:
            name = name[: e.start].encode("ascii")
    name = string.translate(name, TRANSMAP)
    valid_fn_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return "".join(c for c in name if c in valid_fn_chars)


def generate_id(template):
    """Generate a unique string"""
    if template != "" and template is not None:
        template = cleanup_id(template)
    else:
        template = ""
    k = int(time.time())
    id = ""
    for x in range(4):
        id = chr(k & 0xFF) + id
        k >>= 8
    id = base64.encodestring(id)
    return template + string.translate(string.lower(id), TRANSMAP, "/=\n")


def xmlEncode(p_string):
    """Encode the XML reserved chars"""
    if isinstance(p_string, unicode):
        l_tmp = p_string.encode("utf-8")
    else:
        l_tmp = str(p_string)
    l_tmp = l_tmp.replace("&", "&amp;")
    l_tmp = l_tmp.replace("<", "&lt;")
    l_tmp = l_tmp.replace('"', "&quot;")
    l_tmp = l_tmp.replace("'", "&apos;")
    l_tmp = l_tmp.replace(">", "&gt;")
    return l_tmp


# encode to UTF-8 from user encoding


def utGMLEncode(p_str, p_str_enc):
    """Giving a string and an encoding, returns the string encoded to UTF-8
    If no encoding is provided it will assume as input encoding UTF-8

    Also special characters that might appear in GML files are escaped
    """
    if p_str_enc == "":
        l_tmp = unicode(str(p_str), errors="replace")
    else:
        l_tmp = unicode(str(p_str), "%s" % p_str_enc, errors="replace")
    l_tmp = l_tmp.encode("utf8", "replace")

    # xml entities
    l_tmp = l_tmp.replace("&", "&amp;")
    l_tmp = l_tmp.replace("<", "&lt;")
    l_tmp = l_tmp.replace('"', "&quot;")
    l_tmp = l_tmp.replace("'", "&apos;")
    l_tmp = l_tmp.replace(">", "&gt;")

    # Microsoft Word entities
    l_tmp = l_tmp.replace("—", "-")
    l_tmp = l_tmp.replace("–", "-")
    l_tmp = l_tmp.replace("‘", "'")
    l_tmp = l_tmp.replace("’", "'")
    l_tmp = l_tmp.replace(" ", " ")
    l_tmp = l_tmp.replace("´", "'")
    l_tmp = l_tmp.replace("“", "&quot;")
    l_tmp = l_tmp.replace("”", "&quot;")
    l_tmp = l_tmp.replace("§", "-")
    l_tmp = l_tmp.replace("¤", " ")
    l_tmp = l_tmp.replace("«", "&quot;")
    l_tmp = l_tmp.replace("»", "&quot;")
    l_tmp = l_tmp.replace("…", "...")
    l_tmp = l_tmp.replace("•", "* ")

    return l_tmp


def asciiEncode(p_value):
    """Gets a value and returns a string"""
    if p_value is not None:
        return unicode(str(p_value), "latin-1").encode("ascii", "replace")
    else:
        return ""


def utRead(file):
    """Open file on local or remote system."""
    if "http" in file:
        opener = FancyURLopener()
        f = opener.open(file)
    else:
        f = open(file, "rb+")
    return f


def utf8Encode(p_str):
    """encodes a string to UTF-8"""
    return p_str.encode("utf8")


def to_utf8(s):
    """converts Unicode to UTF-8"""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return s


def utConvertToList(something):
    """Convert to list"""
    ret = something
    if not something:
        return []
    if isinstance(something, str):
        ret = [something]
    return ret


def utConvertListToLines(values):
    """Takes a list of values and returns a value for a textarea control"""
    if len(values) == 0:
        return ""
    else:
        return "\r\n".join(values)


def utConvertLinesToList(value):
    """Takes a value from a textarea control and returns a list of values"""
    if isinstance(value, list):
        return value
    elif not value:
        return []
    else:
        values = []
        for v in value.split("\r\n"):
            if v != "":
                values.append(v)
    return values


def utIsSubsetOf(first_list, second_list):
    """returns true if the first list is a subset of the second"""
    for l_element in utConvertToList(first_list):
        if l_element not in second_list:
            return 0
    return 1


def utSortByAttr(p_obj_list, p_attr, p_sort_order=0):
    """Sort a list of objects by one of the attributes"""
    l_temp = map(
        None,
        map(getattr, p_obj_list, (p_attr,) * len(p_obj_list)),
        xrange(len(p_obj_list)),
        p_obj_list,
    )
    l_temp.sort()
    if p_sort_order:
        l_temp.reverse()
    return map(operator.getitem, l_temp, (-1,) * len(l_temp))


def utSortListByAttr(p_obj_list, p_attr, p_sort_order=0):
    """Sort a list of objects by one of the attributes"""
    l_temp = map(
        None, (p_obj_item[p_attr] for p_obj_item in p_obj_list), p_obj_list
    )
    l_temp.sort()
    if p_sort_order:
        l_temp.reverse()
    return map(operator.getitem, l_temp, (-1,) * len(l_temp))


def utTruncString(s, p_size=50):
    # get a string and returns only a number of size characters
    if len(s) > p_size:
        return "%s..." % s[:p_size]
    else:
        return s


def utSortObjsListByMethod(p_list, p_method, p_desc=1):
    """Sort a list of objects by an attribute values"""
    l_len = len(p_list)
    l_temp = map(
        None,
        map(lambda x, y: getattr(x, y)(), p_list, (p_method,) * l_len),
        xrange(l_len),
        p_list,
    )
    l_temp.sort()
    if p_desc:
        l_temp.reverse()
    return map(operator.getitem, l_temp, (-1,) * l_len)


def utSortObjsListByMethod2(p_list, p_method, p_desc=1):
    """Sort a list of objects by an attribute values"""

    p_list.sort(key=operator.attrgetter(p_method))
    if p_desc:
        p_list.reverse()
    return p_list


def utSortByMethod(p_obj_list, p_attr, p_date, p_sort_order=0):
    """Sort a list of objects by the result of one of their functions"""
    l_temp = map(
        None,
        map(
            lambda x, y: getattr(x, y)(),
            p_obj_list,
            (p_attr,) * len(p_obj_list),
        ),
        xrange(len(p_obj_list)),
        p_obj_list,
        (p_date,) * len(p_obj_list),
    )
    l_temp = filter(lambda x: x[0] < x[3], l_temp)
    l_temp.sort()
    if p_sort_order:
        l_temp.reverse()
    return map(operator.getitem, l_temp, (-2,) * len(l_temp))


def utGrabFromUrl(p_url):
    """Takes a file from a remote server"""
    from urllib import URLopener

    try:
        l_opener = URLopener()
        l_file = l_opener.open(p_url)
        ctype = l_file.headers["Content-Type"]
        l_opener.close()
        return (l_file.read(), ctype)
    except Exception:
        return (None, "text/x-unknown-content-type")


def parse_template(template, dict={}):
    """Make some text from a template file."""
    if dict is not None:
        try:
            text = string.Template(template)
            result = text.substitute(dict)
            return to_utf8(result)
        except (TypeError, ValueError, KeyError) as error:
            logger.exception(error)
            raise Exception("An error occurred while generating this file")


def utGetTemp():
    """return the system temp dir"""
    if sys.platform == "win32":
        return os.getenv("TEMP")
    else:
        return "/tmp"


def getFilename(filename):
    """return only the filename, removing the path"""
    return filename.split("\\")[-1]


def createTempFile(p_file, p_filename=""):
    """create a file in system temp dir"""
    if hasattr(p_file, "filename"):
        l_data = p_file.read()
        l_filename = cookId(p_file)
    else:
        l_data = p_file
        l_filename = p_filename
    file_temp = open(os.path.join(utGetTemp(), l_filename), "wb")
    file_temp.write(l_data)
    file_temp.close()


def deleteTempFile(filename):
    """delete a file from the system temp dir"""
    os.unlink(os.path.join(utGetTemp(), "%s" % filename))


def cookId(file):
    """generate a file ID"""
    if hasattr(file, "filename"):
        filename = file.filename
        id = filename[
            max(
                filename.rfind("/"),
                filename.rfind("\\"),
                filename.rfind(":"),
            )
            + 1:
        ]
        return id
    return file


def extractURLs(s):
    """find all the URLs from a string"""
    return re.findall("(?P<url>http[s]?://[-_&;,?:~=%#+/.0-9a-zA-Z]+)", s)


class TmpFile:
    def __init__(self, data):
        self.fname = tempfile.mktemp()
        open(self.fname, "w+b").write(data)

    def __str__(self):
        return self.fname

    __repr__ = __str__

    def __del__(self):
        os.unlink(self.fname)


def temporary_named_copy(source_file):
    tmp_file = tempfile.NamedTemporaryFile()
    for chunk in iter_file_data(source_file):
        tmp_file.write(chunk)
    tmp_file.flush()
    return tmp_file


def http_response_with_file(
    request, response, data_file, content_type, file_size, file_mtime
):
    # HTTP If-Modified-Since header handling.
    header = request.get_header("If-Modified-Since", None)
    if header is not None:
        header = string.split(header, ";")[0]
        # Some proxies seem to send invalid date strings for this
        # header. If the date string is not valid, we ignore it
        # rather than raise an error to be generally consistent
        # with common servers such as Apache (which can usually
        # understand the screwy date string as a lucky side effect
        # of the way they parse it).
        # This happens to be what RFC2616 tells us to do in the face of an
        # invalid date.
        try:
            mod_since = long(DateTime(header).timeTime())
        except Exception:
            mod_since = None
        if mod_since is not None:
            last_mod = long(file_mtime)
            if last_mod > 0 and last_mod <= mod_since:
                # Set header values since apache caching will return
                # Content-Length of 0 in response if size is not set here
                response.setHeader("Last-Modified", rfc1123_date(file_mtime))
                response.setHeader("Content-Type", content_type)
                response.setHeader("Content-Length", file_size)
                response.setStatus(304)
                return

    response.setHeader("Last-Modified", rfc1123_date(file_mtime))
    response.setHeader("Content-Type", content_type)
    response.setHeader("Content-Length", file_size)

    for chunk in iter_file_data(data_file):
        response.write(chunk)


def iter_ofs_file_data(ofs_file):
    data = ofs_file.data

    if isinstance(data, str):
        yield data

    else:
        while data is not None:
            yield data.data
            data = data.next


def ofs_file_content_tmp(ofs_file):
    tmp_data = tempfile.NamedTemporaryFile()
    if ofs_file.meta_type == "File (Blob)":
        with ofs_file.data_file.open() as f:
            for chunk in iter_file_data(f):
                tmp_data.write(chunk)
    elif ofs_file.meta_type == "File":
        for chunk in iter_ofs_file_data(ofs_file):
            tmp_data.write(chunk)
    else:
        raise ValueError("Unknown meta_type %r" % ofs_file.meta_type)
    tmp_data.seek(0)
    return tmp_data


def _mime_types():
    mime_types = _load_json("mime_types.json")
    return mime_types


def extension(accepted_mime_types):
    for ext, mimes in mime_types.iteritems():
        for mime in mimes:
            if mime in accepted_mime_types:
                return ext


def _load_json(name):
    with open(os.path.join(os.path.dirname(__file__), name), "rb") as f:
        return json.load(f)


def inline_replace(x):
    x["uri"] = x["uri"].replace("eionet.eu.int", "eionet.europa.eu")
    return x


mime_types = _mime_types()


def discard_utf8_bom(body):
    bom = "\xef\xbb\xbf"
    if body.startswith(bom):
        return body[3:]
    else:
        return body


def replace_keys(replace_items, obj):
    """
    Replace keys of a dict
    :param replace_items: dict with keys and replacements
    :param obj: dict where to replace
    :return: modified dict
    """
    if obj:
        for key, replacement in replace_items.iteritems():
            if key in obj:
                obj[replacement] = obj.pop(key)
    return obj


def fix_json_from_id(obj_original):
    """
    Replace keys from json to set the right json format, used in
     SatelliteRegistryManagement class
    :param obj_original: python dict
    :return: the dict in the corect format
    """
    if not obj_original:
        return {}

    obj = deepcopy(obj_original)

    # Replace keys to set the right json format
    obj = replace_keys(
        {
            "oldcompany_account": "Former_Company_no_2007-2010",
            "company_id": "id",
            "representative": "euLegalRepresentativeCompany",
            "users": "contactPersons",
            "businessprofile": "businessProfile",
            "undertaking_type": "@type",
        },
        obj,
    )

    # Replace legal representative format
    if obj["euLegalRepresentativeCompany"]:
        obj["euLegalRepresentativeCompany"] = replace_keys(
            {
                "vatnumber": "vatNumber",
                "contact_last_name": "contactPersonLastName",
                "contact_first_name": "contactPersonFirstName",
                "contact_email": "contactPersonEmailAddress",
            },
            obj["euLegalRepresentativeCompany"],
        )

    # Replace legal representative address format
    if obj["euLegalRepresentativeCompany"]:
        obj["euLegalRepresentativeCompany"]["address"] = replace_keys(
            {"zipcode": "zipCode"},
            obj["euLegalRepresentativeCompany"]["address"],
        )

    # Replace address format
    obj["address"] = replace_keys({"zipcode": "zipCode"}, obj["address"])

    # Replace contact persons format
    for person in obj["contactPersons"]:
        replace_keys(
            {
                "username": "userName",
                "first_name": "firstName",
                "last_name": "lastName",
                "email": "emailAddress",
            },
            person,
        )

    # Replace businessProfile
    obj["businessProfile"] = replace_keys(
        {"highleveluses": "highLevelUses"}, obj["businessProfile"]
    )

    date_created = obj.get("date_created")
    if date_created:
        try:
            pr_date = datetime.strptime(date_created, "%d/%m/%Y").isoformat()
        except ValueError:
            pr_date = None

        obj["portal_registration_date"] = pr_date

    # Delete unused keys
    unused = [
        "country_code",
        "date_created",
        "date_updated",
        "candidates",
        "collection_id",
        "oldcompany_verified",
        "oldcompany_extid",
    ]
    for key in unused:
        obj.pop(key, None)

    return obj


def write_xls_header(sheet):
    """Write the xls header"""
    for head in XLS_HEADINGS:
        column = XLS_HEADINGS.index(head)
        sheet.write(0, column, head[0])
        yield head[1], column


def write_xls_data(data, sheet, header, row):
    """Write data to sheet"""
    for key in header.keys():
        value = data.get(key)
        if isinstance(value, list):
            value = ",".join(value)
            if len(value) > 32000:
                value = (value[:32000] + "..") if len(value) > 32000 else value
        sheet.write(row, header.get(key), value)


def manage_as_owner(func):
    """Decorator to be used by Applications to call methods as
    owner.
    """

    def inner(*args, **kwargs):
        user_id = args[0].REQUEST["AUTHENTICATED_USER"].getUserName()
        if user_id != "Anonymous User":
            smanager = getSecurityManager()
            owner = args[0].getOwner()
            newSecurityManager(args[0].REQUEST, owner)
            res = func(*args, **kwargs)
            setSecurityManager(smanager)
            return res

    return inner


def execute_under_special_role(portal, role, function, *args, **kwargs):
    """Execute code under special role privileges.

    Example how to call::

        execute_under_special_role(
            portal,
            "Manager",
            doSomeNormallyNotAllowedStuff,
            source_folder,
            target_folder,
        )


    @param portal: Reference to ISiteRoot object whose access controls used

    @param function: Method to be called with special privileges

    @param role: User role for the security context when calling the
                 privileged code; e.g. "Manager".

    @param args: Passed to the function

    @param kwargs: Passed to the function
    """

    sm = getSecurityManager()

    try:
        try:
            # Clone the current user and assign a new role.
            # Note that the username (getId()) is left in exception
            # tracebacks in the error_log,
            # so it is an important thing to store.
            tmp_user = UnrestrictedUser(sm.getUser().getId(), "", [role], "")

            # Wrap the user in the acquisition context of the portal
            tmp_user = tmp_user.__of__(portal.acl_users)
            newSecurityManager(None, tmp_user)

            # Call the function
            return function(*args, **kwargs)

        except Exception:
            # If special exception handlers are needed, run them here
            raise
    finally:
        # Restore the old security manager
        setSecurityManager(sm)


def get_zip_cache():
    zc_path = ZIP_CACHE_PATH or CLIENT_HOME  # noqa
    zip_cache = path(zc_path) / "zip_cache"
    if not zip_cache.isdir():
        zip_cache.mkdir()

    return zip_cache


def cleanup_zip_cache(days=7):
    """Cleanup the zip_cache"""
    zip_cache = get_zip_cache()
    removed = []
    # 60 minutes limit for temp files
    t_limit = time.time() - 3600
    # days limit for zip files
    z_limit = time.time() - int(days) * 86400
    for f in os.listdir(zip_cache):
        file_path = os.path.join(zip_cache, f)
        delete = os.stat(file_path).st_mtime < z_limit
        l_msg = (
            "Automatically removed file {} because "
            "it was older than {} days".format(f, days)
        )
        if f.endswith(".temp"):
            delete = os.stat(file_path).st_mtime < t_limit
            l_msg = "Automatically removed orphaned temp file {}".format(f)
        if delete:
            try:
                os.unlink(file_path)
                removed.append(f)
                logger.info(l_msg)
            except OSError as e:
                logger.warning(
                    "Unable to remove file: {} ({})".format(f, str(e))
                )
    return removed


class RemoteApplicationException(Exception):
    """Our own Remote Application exception."""

    pass


class CrashMe(BrowserView):
    """CrashMe view"""

    def __call__(self):
        raise RuntimeError("Crashing as requested by you")


def _mergedLocalRoles(object):
    """Returns a merging of object and its ancestors'
    __ac_local_roles__."""
    # Modified from AccessControl.User.getRolesInContext().
    merged = {}
    object = getattr(object, "aq_inner", object)
    while 1:
        if hasattr(object, "__ac_local_roles__"):
            dict = object.__ac_local_roles__ or {}
            if callable(dict):
                dict = dict()
            for k, v in dict.items():
                if k in merged:
                    merged[k] = merged[k] + v
                else:
                    merged[k] = v
        if hasattr(object, "aq_parent"):
            object = object.aq_parent
            object = getattr(object, "aq_inner", object)
            continue
        if hasattr(object, "__self__"):
            object = object.__self__
            object = getattr(object, "aq_inner", object)
            continue
        break

    return deepcopy(merged)


class DFlowCatalogAware(object):
    """DFlowCatalogAware class to allow for reportek_dataflow_admin permission
    indexing.
    """

    _security_indexes = ("allowedAdminRolesAndUsers", "allowedRolesAndUsers")

    def allowedAdminRolesAndUsers(self):
        """
        Return a list of roles and users with reportek_dataflow_admin
        permission. Used by Catalog to filter out items you're not
        allowed to see.
        """
        ob = self
        allowed = {}
        for r in rolesForPermissionOn(reportek_dataflow_admin, ob):
            allowed[r] = 1
        localroles = _mergedLocalRoles(ob)
        for user, roles in localroles.items():
            for role in roles:
                if role in allowed:
                    allowed["user:" + user] = 1
        if "Owner" in allowed:
            del allowed["Owner"]

        return list(allowed.keys())

    def reindexObjectSecurity(self, skip_self=False):
        """Reindex security-related indexes on the object."""
        catalog = getToolByName(self, DEFAULT_CATALOG, None)
        if catalog is None:
            return
        path = "/".join(self.getPhysicalPath())
        counter = 0
        for brain in catalog.searchResults(path=path):
            brain_path = brain.getPath()
            if brain_path == path and skip_self:
                continue
            # Get the object
            try:
                ob = brain._unrestrictedGetObject()
            except (AttributeError, KeyError):
                # don't fail on catalog inconsistency
                continue
            if ob is None:
                # BBB: Ignore old references to deleted objects.
                # Can happen only when using
                # catalog-getObject-raises off in Zope 2.8
                logger.warning(
                    "reindexObjectSecurity: Cannot get %s from " "catalog",
                    brain_path,
                )
                continue
            counter += 1
            # Recatalog with the same catalog uid.
            s = getattr(ob, "_p_changed", 0)
            catalog.catalog_object(ob, brain_path, self._security_indexes, 0)
            if s is None:
                ob._p_deactivate()


def parse_uri(uri, replace=False):
    """Use only http uris if QA http resources is checked in ReportekEngine
    props
    """
    if replace:
        new_uri = uri.replace("https://", "http://")
        logger.info(
            "Original uri: %s has been replaced with uri: %s" % (uri, new_uri)
        )
        uri = new_uri
    return uri


def encode_dict(dic):
    if isinstance(dic, unicode):
        return dic.encode("utf-8")
    elif isinstance(dic, dict):
        res = {}
        for key in dic:
            res[key.encode("utf-8")] = encode_dict(dic[key])
        return res
    elif isinstance(dic, list):
        new_l = []
        for e in dic:
            new_l.append(encode_dict(e))
        return new_l
    else:
        return dic


@security.private
def registerToolInterface(tool_id, tool_interface):
    """Register a tool ID for an interface

    This method can go away when getToolByName is going away
    """
    global _tool_interface_registry
    _tool_interface_registry[tool_id] = tool_interface


@security.private
def getToolInterface(tool_id):
    """Get the interface registered for a tool ID"""
    global _tool_interface_registry
    return _tool_interface_registry.get(tool_id, None)


def is_unwrapped(utility):
    """Check if the utility is unwrapped or wrapped to a wrong context."""
    parent = aq_parent(utility)

    if parent is None or len(parent.objectIds()) <= 2:
        return True


@security.public
def getToolByName(obj, name, default=_marker):
    """Get the tool, 'toolname', by acquiring it.

    o Application code should use this method, rather than simply
      acquiring the tool by name, to ease forward migration (e.g.,
      to Zope3).
    """
    tool_interface = _tool_interface_registry.get(name)

    if tool_interface is not None:
        try:
            utility = getUtility(tool_interface)
            # Site managers, except for five.localsitemanager, return unwrapped
            # utilities. If the result is something which is
            # acquisition-unaware but unwrapped we wrap it on the context.
            if (
                IAcquirer.providedBy(obj)
                and aq_parent(utility) is None
                and IAcquirer.providedBy(utility)
            ):
                utility = utility.__of__(obj)

            return utility
        except ComponentLookupError:
            # behave in backwards-compatible way
            # fall through to old implementation
            pass

    try:
        tool = aq_get(obj, name, default, 1)
    except AttributeError:
        if default is _marker:
            raise
        return default
    else:
        if tool is _marker:
            raise AttributeError(name)
        return tool


def _getAuthenticatedUser(self):
    return getSecurityManager().getUser()


def checkPermission(permission, obj):
    if not isinstance(permission, str):
        permission = permission.decode()
    return getSecurityManager().checkPermission(permission, obj)
