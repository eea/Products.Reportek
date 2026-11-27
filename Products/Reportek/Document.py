# The contents of this file are subject to the Mozilla Public,
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

#     $Id$

import hashlib
import json
import logging
import os
import copy
import re
import struct
import tempfile
import zlib
from io import IOBase, StringIO
from itertools import islice
from os.path import join
from time import time
from urllib.parse import quote
import zipfile
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

import plone.protect.interfaces
from plone.protect.interfaces import IDisableCSRFProtection

# import RepUtils
import requests
import transaction
import xmltodict
from AccessControl import ClassSecurityInfo, getSecurityManager
from AccessControl.class_init import InitializeClass
from App.Common import package_home
from zope.datetime import rfc1123_date
from DateTime import DateTime
from OFS.SimpleItem import SimpleItem
from zExceptions import BadRequest, NotFound, Redirect, Unauthorized
from zope.component import getMultiAdapter
from zope.contenttype import guess_content_type
from zope.event import notify
from zope.interface import alsoProvides, implementer
from zope.lifecycleevent import ObjectModifiedEvent
from ZPublisher import zpublish
from ZPublisher.HTTPRequest import FileUpload

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek import IconShow, RepUtils, qa

# Product imports
from Products.Reportek.blob import FileContainer, StorageError
from Products.Reportek.CatalogAware import CatalogAware
from Products.Reportek.constants import (
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_XML,
    DEFAULT_CATALOG,
    ENGINE_ID,
    METATYPE_DOCUMENT,
)
from Products.Reportek.interfaces import IDocument
from Products.Reportek.modification_date import set_reportek_modification_date
from Products.Reportek.RepUtils import (
    DFlowCatalogAware,
    getToolByName,
    parse_uri,
    refuse_when_frozen,
)
from Products.Reportek.XMLInfoParser import SchemaError, detect_schema
from Products.Reportek.zip_content import SizeCappedReader, ZZipFile, ZZipFileRaw
from Products.Reportek.permissions import change_envelopes

__version__ = "$Rev$"[6:-2]

FLAT = 0
SYNC_ZODB = 1
SLICED = 2
REPOSITORY = SYNC_ZODB


# format for the files in the repository:
# %u=user, %p=path, %n=file name, %e=file extension, %c=counter, %t=time
FILE_FORMAT = "%n%c%e"

BACKUP_ON_DELETE = 0
ALWAYS_BACKUP = 1
UNDO_POLICY = BACKUP_ON_DELETE
logger = logging.getLogger("Reportek")

# The zip archives that are listed: by type, or by name for the types that are
# used for anything (octet-stream)
ZIP_CONTENT_TYPES = (
    "application/zip",
    "application/x-zip",
    "application/x-zip-compressed",
)
# The biggest file of an archive that is sent. The file is read while it is
# sent, so this bounds what a client can make the server decompress.
ZIP_MEMBER_MAX_SIZE = 500 * 1024 * 1024
# An archive that is stored compressed is decompressed into a temporary file,
# that stays in memory up to this size
ZIP_SPOOL_SIZE = 8 * 1024 * 1024
# The biggest archive that is stored compressed that is read: it is decompressed
# into a temporary file first
ZIP_SPOOL_MAX_SIZE = 100 * 1024 * 1024
# The most files of an archive that are listed on the page
ZIP_MAX_LISTED = 1000
ZIP_ENCRYPTED_FLAG = 0x1
ZIP_UTF8_FLAG = 0x800
# the mode of the files of an archive that is made: a plain file, rw-r--r--
ZIP_FILE_ATTRIBUTES = 0o100644 << 16
# The files that are chosen to download together: how many, and how big they are
# together, as they are in the archive and as they are when they are unpacked
ZIP_SELECTION_MAX_FILES = 100
ZIP_SELECTION_MAX_SIZE = 500 * 1024 * 1024
# The files of an archive are copied as they are, without being compressed or
# decompressed, so these are the compressions that every program can read
ZIP_COPY_METHODS = (ZIP_STORED, ZIP_DEFLATED)

manage_addDocumentForm = PageTemplateFile(
    os.path.join(package_home(globals()), "zpt/document/add.zpt")
)


def _is_file(info):
    """A file of a zip, not a folder."""
    return bool(info.filename) and not info.is_dir()


def _is_anonymous():
    return getSecurityManager().getUser().getUserName() == "Anonymous User"


def _is_safe_path(name):
    """Whether a name of a file of an archive stays where it is unpacked: not an
    absolute path, not a drive, no folder above. A program that unpacks an archive
    does not always check it, and the archive that is made is ours."""
    if name.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", name):
        return False
    return ".." not in re.split(r"[\\/]", name)


def _can_be_copied(info):
    """Whether the file can be chosen to be downloaded with others."""
    return (
        not info.flag_bits & ZIP_ENCRYPTED_FLAG
        and info.file_size <= ZIP_MEMBER_MAX_SIZE
        and info.compress_type in ZIP_COPY_METHODS
        and _is_safe_path(info.filename)
    )


def _dos_date_time(date_time):
    year, month, day, hour, minute, second = date_time
    return (
        ((year - 1980) << 9) | (month << 5) | day,
        (hour << 11) | (minute << 5) | (second // 2),
    )


def _base_name(path):
    """The name of a file of a zip without the folders it is in."""
    return re.split(r"[\\/]", path)[-1] or "file"


def _attachment(filename):
    """The Content-Disposition of a download: a name for the old clients that
    has nothing in it that could end the header, and the real one."""
    fallback = re.sub(r"[^A-Za-z0-9._ -]", "_", filename)
    return "attachment; filename=\"%s\"; filename*=UTF-8''%s" % (
        fallback,
        quote(filename, safe=""),
    )


class ArchiveTooBig(ValueError):
    """An archive that is stored compressed and is too big to read."""


# What reading a file of a zip can raise when the file is damaged
ZIP_MEMBER_ERRORS = (BadZipFile, zlib.error, EOFError)
# What opening a zip can raise when the file is not one that can be read
ZIP_READ_ERRORS = (BadZipFile, OSError, ValueError, StorageError, NotImplementedError)


class ZipMemberReader:
    """A file of a zip as the response needs it: read up to the size that the
    zip says, and close. It is not a file on purpose: the server measures a
    file by reading it to the end, which for this means decompressing it."""

    def __init__(self, member, size, close_archive):
        self._member = member
        self._left = size
        self._close_archive = close_archive
        self._closed = False

    def read(self, size=-1):
        if self._left <= 0:
            return b""
        if size is None or size < 0 or size > self._left:
            size = self._left
        chunk = self._member.read(size)
        if not chunk:
            # the length was sent already: a file that ends early must break
            # the download, not be taken for a shorter one
            raise BadZipFile("The file in the archive is shorter than it says")
        self._left -= len(chunk)
        return chunk

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._member.close()
        finally:
            self._close_archive()


def error_message(ctx, message, action=None, REQUEST=None):
    if not action:
        action = ctx.absolute_url()
    if REQUEST is not None:
        accept = REQUEST.environ.get("HTTP_ACCEPT")
        if accept == CONTENT_TYPE_JSON:
            REQUEST.RESPONSE.setHeader("Content-Type", CONTENT_TYPE_JSON)
            error = {"title": "Error", "description": message}
            data = {
                "errors": [error],
            }
            return json.dumps(data, indent=4)
        else:
            return ctx.messageDialog(message=message, action=action)
    return ""


def success_message(ctx, objs, message=None, errors=None, action=None, REQUEST=None):
    if not action:
        action = ctx.absolute_url()
    if not errors:
        errors = []
    if REQUEST is not None:
        accept = REQUEST.environ.get("HTTP_ACCEPT")
        if accept == CONTENT_TYPE_JSON:
            REQUEST.RESPONSE.setHeader("Content-Type", CONTENT_TYPE_JSON)
            REQUEST.RESPONSE.setStatus(201)
            files = []
            for obj in objs:
                files.append(
                    {
                        "url": obj.absolute_url(0),
                        "title": obj.title,
                        "contentType": obj.content_type,
                        "schemaURL": obj.xml_schema_location,
                        "uploadDate": obj.upload_time().HTML4(),
                        "fileSize": obj.get_size(),
                        "fileSizeHR": obj.size(),
                        "isRestricted": 1 if obj.isRestricted() else 0,
                    }
                )
            data = {"files": files, "errors": errors}
            return json.dumps(data, indent=4)
        return ctx.messageDialog(message=message, action=action)
    return ""


@refuse_when_frozen
def manage_addDocument(
    self,
    id="",
    title="",
    file="",
    content_type="",
    filename="",
    restricted="",
    disallow="",
    REQUEST=None,
    deferred_compress=None,
):
    """Add a Document to a folder. The form can be called with three variables
    set in the session object: default_restricted, force_restricted and
    disallow. This will set the restricted flag in the form or
    """
    # disable csrf due to verification reporting uploading files
    if "IDisableCSRFProtection" in dir(plone.protect.interfaces):
        if REQUEST:
            alsoProvides(REQUEST, plone.protect.interfaces.IDisableCSRFProtection)
    is_object = hasattr(file, "read") and (getattr(file, "filename", None) or filename)
    if is_object and not filename:
        filename = getattr(file, "filename")
    is_str = file and isinstance(file, (str, bytes))

    if is_object:
        if not id:
            id = filename
        else:
            _, ext = os.path.splitext(id)
            if not ext:
                _, ext = os.path.splitext(filename)
                id += ext

    if (is_str or is_object) and id:
        save_id = None
        id = id[
            max(
                id.rfind("/"),
                id.rfind("\\"),
                id.rfind(":"),
            )
            + 1 :
        ]
        id = id.strip()
        id = RepUtils.cleanup_id(id)

        # Check to see if file has an extension which is disallowed
        if disallow:
            disallow = disallow.replace(" ", "").split(",")
            for ext in disallow:
                if not ext.startswith("."):
                    ext = "".join([".", ext])
                if id.endswith(ext):
                    return error_message(
                        self,
                        "{} files are disallowed in this context".format(ext),
                        REQUEST=REQUEST,
                    )

        # delete the previous file with the same id, if exists
        if self.get(id) and isinstance(self.get(id), Document):
            save_id = id
            id += "___tmp_%f" % time()

        obj = Document(id, title=title, deferred_compress=deferred_compress)
        self = self.this()
        self._setObject(id, obj)
        obj = self._getOb(id)
        try:
            obj.manage_file_upload(file, content_type)
        except SchemaError as e:
            self.manage_delObjects(id)
            logger.exception("The file is an invalid XML (reason: %s)" % str(e.args))
            return error_message(
                self,
                "The file is an invalid XML (reason: %s)" % str(e.args),
                REQUEST=REQUEST,
            )
        if save_id:
            self.manage_delObjects(save_id)
            transaction.commit()
            self.manage_renameObject(id, save_id)
            id = save_id
        r_enabled = (
            hasattr(self, "is_globally_restricted") and self.is_globally_restricted()
        ) or (hasattr(self, "is_workflow_restricted") and self.is_workflow_restricted())
        if restricted or r_enabled:
            obj.manage_restrictDocument()
        obj.reindexObject()
        if REQUEST is not None:
            # This is an ugly hack, sometimes the PARENTS are in reverse order
            # TODO: Find a better way to handle the issue
            if len(REQUEST.PARENTS) > 1:
                pobj = REQUEST.PARENTS[0]
                if not REQUEST.PARENTS[0].absolute_url(1):
                    pobj = REQUEST.PARENTS[-1]
            ppath = "/".join(pobj.getPhysicalPath())
            msg = "The file %s was successfully created!" % id
            return success_message(
                self, [obj], message=msg, action=ppath, REQUEST=REQUEST
            )
        else:
            return id
    else:
        return error_message(self, "You must specify a file!", REQUEST=REQUEST)


@implementer(IDocument)
class Document(CatalogAware, SimpleItem, IconShow.IconShow, DFlowCatalogAware):
    """An External Document allows indexing and conversions.

    .. attribute:: data_file

        The document's binary content as :class:`.FileContainer` object.
    """

    icon = "++resource++images/document.gif"

    manage_options = (
        {"label": "Edit", "action": "manage_main"},
        {"label": "View/Download", "action": ""},
        {"label": "Upload", "action": "manage_uploadForm"},
        {"label": "Security", "action": "manage_access"},
    )

    security = ClassSecurityInfo()

    security.declareProtected("Change permissions", "manage_access")

    security.declareProtected(change_envelopes, "manage_editDocument")
    security.declareProtected(change_envelopes, "manage_main")
    security.declareProtected(change_envelopes, "manage_uploadForm")
    security.declareProtected(change_envelopes, "manage_file_upload")

    security.declareProtected("View", "index_html")
    security.declareProtected("View", "link")
    security.declareProtected("View", "get_size")
    security.declareProtected("View", "getContentType")
    security.declareProtected("View", "__str__")
    security.declarePrivate("data_file")

    import os

    from App.Common import package_home

    _macros_template = PageTemplateFile(
        os.path.join(package_home(globals()), "zpt/document/macros.zpt")
    )

    @property
    def macros(self):
        return self._macros_template.macros

    meta_type = METATYPE_DOCUMENT

    ################################
    # Init method                  #
    ################################

    def __init__(self, id, title="", content_type="", deferred_compress=None):
        """Initialize a new instance of Document
        If a document is created through FTP, self.absolute_url doesn't
        work.
        """
        set_reportek_modification_date(self)
        self.id = id
        self.title = title
        self.xml_schema_location = ""  # needed for XML files
        self.accept_time = None
        ctor_kwargs = {}
        if content_type:
            ctor_kwargs["content_type"] = content_type
        if deferred_compress:
            ctor_kwargs["compress"] = "deferred"
        self.data_file = FileContainer(**ctor_kwargs)

    ################################
    # Public methods               #
    ################################

    @property
    def content_type(self):
        old_ct = self.__dict__.get("content_type", None)
        if old_ct:
            return old_ct
        return self.data_file.content_type

    @content_type.setter
    def content_type(self, value):
        if "content_type" in self.__dict__:
            self.__dict__["content_type"] = value
        else:
            self.data_file.content_type = value

    def __str__(self):
        return self.index_html(self.REQUEST, self.REQUEST.RESPONSE)

    def __len__(self):
        return 1

    @zpublish(False)
    def upload_time(self):
        """Return the upload time"""
        return DateTime(self.data_file.mtime)

    @zpublish(False)
    def get_accept_time(self):
        """A document can have an accepted status. It is set by the client,
        and is used to force the file to be immutable even if the envelope
        is returned to draft state. It is used in second and third delivery
        round, to tell the reporter that some files have to be redelivered,
        but some file are accepted and are processed.

        It was used in Article 17 - 2007.
        """
        if getattr(self, "accept_time", None):
            return DateTime(self.accept_time)
        return None

    security.declareProtected("Change Feedback", "set_accept_time")

    def set_accept_time(self, totime=1):
        """Sets the accept time or clears it if totime != 1"""
        if totime == 1:
            self.accept_time = time()
        else:
            self.accept_time = None

    HEAD__roles__ = None

    def HEAD(self, REQUEST, RESPONSE):
        """Support for HEAD requests from search engines etc."""
        RESPONSE.setHeader("Last-Modified", rfc1123_date(self.data_file.mtime))
        RESPONSE.setHeader("Content-Length", self.data_file.size)
        RESPONSE.setHeader("Content-Type", self.content_type)
        return ""

    security.declarePublic("getMyOwner")

    def getMyOwner(self):
        """Find the owner in the local roles."""
        for a, b in self.get_local_roles():
            if "Owner" in b:
                return a
        return ""

    security.declarePublic("getMyOwnerName")

    def getMyOwnerName(self):
        """Find the owner in the local roles.
        Then use LDAP to find the user's full name.
        TODO: Move LDAP dependency to ReportekEngine.
        """
        return self.getLDAPUserCanonicalName(self.getLDAPUser(self.getMyOwner()))

    @zpublish(False)
    def logUpload(self):
        """Log file upload and any reuploads into the envelope history.
        The workitems' event logs are used since these are displayed
        on the envelope's history tab
        """
        if self.REQUEST and getattr(self.REQUEST, "AUTHENTICATED_USER", None):
            for l_w in self.getWorkitemsActiveForMe(self.REQUEST):
                l_w.addEvent(
                    "file upload",
                    "File: {0} ({1})".format(
                        self.id,
                        self.data_file.human_readable(self.data_file.size),
                    ),
                )

    def index_html(self, REQUEST, RESPONSE, icon=0):
        """Returns the contents of the file.  Also, sets the
        Content-Type HTTP header to the objects content type.
        """
        if icon:
            return self.icon_gif(REQUEST, RESPONSE)

        skip_decomp = False
        ae = REQUEST.getHeader("Accept-Encoding")
        # TODO also take weights into consideration (gzip;q=0,deflate;q=1)
        if ae and ae.lower().startswith("gzip"):
            skip_decomp = True
        # The file is closed when the body of the response is sent
        data_file_handle = self.data_file.open(skip_decompress=skip_decomp)
        try:
            size = self.data_file.size
            if skip_decomp and self.is_compressed():
                # This is hackish. If the client asked for gzip compression
                # first and we are storing the content compressed
                # then instruct the FileContiner not to decompress the fetched
                # content and tell the client that we are serving his content
                # gzipped
                RESPONSE.setHeader("content-encoding", "gzip")
                size = self.data_file.compressed_size
        except BaseException:
            data_file_handle.close()
            raise
        return RepUtils.http_response_with_file(
            REQUEST,
            RESPONSE,
            data_file_handle,
            self.content_type,
            size,
            self.data_file.mtime,
        )

    security.declareProtected("View", "is_zip")

    @zpublish(False)
    def is_zip(self):
        """Whether the file is a zip archive, by its type or by its name."""
        return self.content_type in ZIP_CONTENT_TYPES or self.id.lower().endswith(
            ".zip"
        )

    security.declarePublic("can_browse_zip")

    @zpublish(False)
    def can_browse_zip(self):
        """Whether the user can list the files of this archive and get them:
        a user that is logged in, who can view the file."""
        return bool(
            self.is_zip()
            and not _is_anonymous()
            and self.canViewContent()
            and getSecurityManager().checkPermission("View", self)
        )

    def _check_zip_access(self):
        """The same rules as the zip of an envelope: not for a user that is not
        logged in (a crawler could follow a link for each file of each archive)
        and only where the content of the envelope can be seen. The permission to
        view the file is the one of the methods."""
        if _is_anonymous():
            raise Unauthorized("You must log in to see the files of an archive")
        if not self.canViewContent():
            raise Unauthorized("The files of the envelope are not available")

    def _open_zip(self):
        """Open the stored file as a zip archive.

        Return the archive and the function that closes it and what is under
        it. A zip is read from its end, so the file has to be one that can seek:
        a file that is stored compressed can only seek by being read, so it is
        decompressed once into a temporary file.
        """
        compressed = self.data_file.compressed_safe
        if compressed and self.data_file.size > ZIP_SPOOL_MAX_SIZE:
            raise ArchiveTooBig("The archive is stored compressed and is too big")
        handle = self.data_file.open()
        spool = None
        try:
            source = handle
            if compressed:
                spool = tempfile.SpooledTemporaryFile(max_size=ZIP_SPOOL_SIZE)
                for chunk in RepUtils.iter_file_data(handle):
                    spool.write(chunk)
                source = spool
            archive = ZipFile(source)
        except BaseException:
            if spool is not None:
                spool.close()
            handle.close()
            raise

        def close():
            try:
                archive.close()
            finally:
                if spool is not None:
                    spool.close()
                handle.close()

        return archive, close

    security.declareProtected("View", "zip_member_url")

    @zpublish(False)
    def zip_member_url(self, name):
        return "%s/zip_member?name=%s" % (self.absolute_url(), quote(name, safe=""))

    security.declareProtected("View", "get_zip_members")

    @zpublish(False)
    def get_zip_members(self):
        """The files of the zip archive, with the folders they are in as part of
        the name and without the folders themselves, as dictionaries with the
        name, the size and the link to it.

        Only the end of the archive is read, where the list is kept, so the
        cost does not depend on how big the files are.
        """
        if not self.is_zip():
            return []
        try:
            archive, close = self._open_zip()
        except ZIP_READ_ERRORS:
            logger.warning("Cannot read the zip %s", self.absolute_url(), exc_info=True)
            return []
        try:
            # by name, as the archive can have a name twice and a name opens the
            # last one
            infos = {i.filename: i for i in archive.infolist() if _is_file(i)}
            return [
                {
                    "name": info.filename,
                    "size": info.file_size,
                    "human_size": FileContainer.human_readable(info.file_size),
                    "url": self.zip_member_url(info.filename),
                    "encrypted": bool(info.flag_bits & ZIP_ENCRYPTED_FLAG),
                    "too_big": info.file_size > ZIP_MEMBER_MAX_SIZE,
                    "selectable": _can_be_copied(info),
                }
                for info in islice(infos.values(), ZIP_MAX_LISTED)
            ]
        finally:
            close()

    security.declareProtected("View", "zip_selection_limit")

    @zpublish(False)
    def zip_selection_limit(self):
        """The most files that are downloaded together."""
        return ZIP_SELECTION_MAX_FILES

    security.declareProtected("View", "zip_listing_limit")

    @zpublish(False)
    def zip_listing_limit(self):
        """The most files of an archive that the page lists."""
        return ZIP_MAX_LISTED

    _zip_contents_template = PageTemplateFile(
        os.path.join(package_home(globals()), "zpt/document/zip_contents.zpt")
    )

    security.declareProtected("View", "zip_contents")

    def zip_contents(self, REQUEST=None):
        """The files of the zip archive, to download one at a time."""
        self._check_zip_access()
        return self._zip_contents_template()

    security.declareProtected("View", "zip_member")

    def zip_member(self, name, REQUEST, RESPONSE):
        """Send one file of the zip archive.

        The file is copied into a temporary file first, that is in memory up to
        ZIP_SPOOL_SIZE, and the server sends that one, so that no thread waits
        for a slow client (a damaged file is found before anything is sent too).
        """
        self._check_zip_access()
        if not self.is_zip() or not isinstance(name, str):
            raise NotFound("The file is not a zip archive or has no such file")
        try:
            archive, close = self._open_zip()
        except ArchiveTooBig as e:
            raise BadRequest(str(e))
        except ZIP_READ_ERRORS:
            logger.warning("Cannot read the zip %s", self.absolute_url(), exc_info=True)
            raise NotFound("The file is not a zip archive")
        try:
            try:
                info = archive.getinfo(name)
            except KeyError:
                raise NotFound("There is no such file in the archive")
            if not _is_file(info):
                raise NotFound("There is no such file in the archive")
            if info.flag_bits & ZIP_ENCRYPTED_FLAG:
                raise BadRequest("The file is encrypted")
            if info.file_size > ZIP_MEMBER_MAX_SIZE:
                raise BadRequest("The file is too big to download from the archive")
            spool = self._spool_member(archive, info)
        finally:
            close()
        content_type = guess_content_type(info.filename)[0]
        if content_type in (None, "text/x-unknown-content-type"):
            content_type = "application/octet-stream"
        try:
            RESPONSE.setHeader(
                "Content-Disposition", _attachment(_base_name(info.filename))
            )
            RESPONSE.setHeader("X-Content-Type-Options", "nosniff")
        except BaseException:
            spool.close()
            raise
        return RepUtils.http_response_with_file(
            REQUEST,
            RESPONSE,
            spool,
            content_type,
            info.file_size,
            self.data_file.mtime,
        )

    def _spool_member(self, archive, info):
        """Copy one file of the archive into a temporary file, that stays in
        memory when it is small and goes to the zip cache when it is not, and
        return it, at its start. What is read is never more than the entry says."""
        spool = tempfile.SpooledTemporaryFile(
            max_size=ZIP_SPOOL_SIZE, dir=str(RepUtils.get_zip_cache())
        )
        try:
            try:
                with archive.open(info) as member:
                    reader = ZipMemberReader(member, info.file_size, lambda: None)
                    for chunk in RepUtils.iter_file_data(reader):
                        spool.write(chunk)
            except NotImplementedError:
                raise BadRequest("The file in the archive cannot be read")
            except ZIP_MEMBER_ERRORS:
                logger.warning(
                    "Damaged file %s in the zip %s",
                    info.filename,
                    self.absolute_url(),
                    exc_info=True,
                )
                raise BadRequest("The file in the archive is damaged")
            spool.seek(0)
        except BaseException:
            spool.close()
            raise
        return spool

    security.declareProtected("View", "zip_selection")

    def zip_selection(self, REQUEST, RESPONSE, names=None):
        """Send some of the files of the zip archive as a new zip archive (one
        file is sent as it is).

        The files are copied as they are in the archive, compressed: nothing is
        compressed or decompressed, so the work is the one of reading and
        writing the bytes. The checksums are the ones of the archive, a program
        that unpacks the new archive finds a file that is damaged.
        """
        self._check_zip_access()
        if REQUEST.method != "POST":
            raise BadRequest("The files are chosen with a POST request")
        if not IDisableCSRFProtection.providedBy(REQUEST):
            authenticator = getMultiAdapter((self, REQUEST), name="authenticator")
            if not authenticator.verify("zip_selection"):
                raise Unauthorized("Unable to verify authenticator")
        if isinstance(names, str):
            names = [names] if names else []
        if not names or not all(isinstance(name, str) for name in names):
            raise BadRequest("Choose at least one file")
        # in the order of the choice, once each
        names = list(dict.fromkeys(names))
        if len(names) > ZIP_SELECTION_MAX_FILES:
            raise BadRequest(
                "Choose at most %d files at a time" % ZIP_SELECTION_MAX_FILES
            )
        if len(names) == 1:
            # one file is sent as it is, not in a zip archive of its own
            return self.zip_member(names[0], REQUEST, RESPONSE)
        if not self.is_zip():
            raise NotFound("The file is not a zip archive")
        try:
            archive, close = self._open_zip()
        except ArchiveTooBig as e:
            raise BadRequest(str(e))
        except ZIP_READ_ERRORS:
            logger.warning("Cannot read the zip %s", self.absolute_url(), exc_info=True)
            raise NotFound("The file is not a zip archive")
        try:
            infos = self._chosen_infos(archive, names)
            spool = self._copy_chosen(archive, infos)
        finally:
            close()
        try:
            spool.seek(0, 2)
            size = spool.tell()
            spool.seek(0)
            stem = self.id[:-4] if self.id.lower().endswith(".zip") else self.id
            RESPONSE.setHeader(
                "Content-Disposition", _attachment("%s-selection.zip" % stem)
            )
            RESPONSE.setHeader("X-Content-Type-Options", "nosniff")
        except BaseException:
            spool.close()
            raise
        return RepUtils.http_response_with_file(
            REQUEST, RESPONSE, spool, "application/zip", size, self.data_file.mtime
        )

    def _chosen_infos(self, archive, names):
        """The entries of the files that are chosen, when they can be copied."""
        infos = []
        offsets = set()
        size = compressed = 0
        for name in names:
            try:
                info = archive.getinfo(name)
            except KeyError:
                raise NotFound("There is no such file in the archive")
            if not _is_file(info):
                raise NotFound("There is no such file in the archive")
            if info.flag_bits & ZIP_ENCRYPTED_FLAG:
                raise BadRequest("A file is encrypted")
            if info.file_size > ZIP_MEMBER_MAX_SIZE:
                raise BadRequest("A file is too big to download from the archive")
            if info.compress_type not in ZIP_COPY_METHODS:
                raise BadRequest("A file is compressed in a way that cannot be copied")
            if not _is_safe_path(info.filename):
                raise BadRequest("A file has a name that is not safe to unpack")
            if info.header_offset in offsets:
                # two files never share their bytes, but an archive that is made
                # to be bigger when it is read could have them
                raise BadRequest("The archive is damaged")
            offsets.add(info.header_offset)
            size += info.file_size
            compressed += info.compress_size
            if max(size, compressed) > ZIP_SELECTION_MAX_SIZE:
                raise BadRequest("The files are too big to download together")
            infos.append(info)
        return infos

    def _copy_chosen(self, archive, infos):
        """Write a zip archive with the compressed data of the entries, as it is
        in the archive: a header for each file, its bytes, then the directory."""
        out = tempfile.SpooledTemporaryFile(
            max_size=ZIP_SPOOL_SIZE, dir=str(RepUtils.get_zip_cache())
        )
        try:
            entries = []
            for info in infos:
                entry = copy.copy(info)
                # a name in UTF-8, no extra data, no data descriptor: the sizes
                # and the checksum are the ones of the directory
                entry.flag_bits = 0
                entry.extra = b""
                entry.comment = b""
                # a plain file: the permissions of the source (a link, a program)
                # are not passed on
                entry.create_system = 3
                entry.external_attr = ZIP_FILE_ATTRIBUTES
                entry.internal_attr = 0
                entry.create_version = entry.extract_version = 20
                entry.header_offset = out.tell()
                out.write(entry.FileHeader(False))
                self._copy_compressed(archive.fp, info, out)
                entries.append(entry)
            start = out.tell()
            for entry in entries:
                name, flags = entry._encodeFilenameFlags()
                date, time = _dos_date_time(entry.date_time)
                out.write(
                    struct.pack(
                        zipfile.structCentralDir,
                        zipfile.stringCentralDir,
                        entry.create_version,
                        entry.create_system,
                        entry.extract_version,
                        entry.reserved,
                        flags,
                        entry.compress_type,
                        time,
                        date,
                        entry.CRC,
                        entry.compress_size,
                        entry.file_size,
                        len(name),
                        0,
                        0,
                        0,
                        entry.internal_attr,
                        entry.external_attr,
                        entry.header_offset,
                    )
                    + name
                )
            out.write(
                struct.pack(
                    zipfile.structEndArchive,
                    zipfile.stringEndArchive,
                    0,
                    0,
                    len(entries),
                    len(entries),
                    out.tell() - start,
                    start,
                    0,
                )
            )
        except BaseException:
            out.close()
            raise
        return out

    def _copy_compressed(self, source, info, out):
        """Copy the compressed bytes of an entry of the archive to `out`."""
        source.seek(info.header_offset)
        header = source.read(zipfile.sizeFileHeader)
        if len(header) != zipfile.sizeFileHeader:
            raise BadRequest("The file in the archive is damaged")
        header = struct.unpack(zipfile.structFileHeader, header)
        if header[0] != zipfile.stringFileHeader:
            raise BadRequest("The file in the archive is damaged")
        # the lengths of the name and of the extra data of the header of the file
        source.seek(header[10] + header[11], 1)
        left = info.compress_size
        while left:
            chunk = source.read(min(left, 131072))
            if not chunk:
                raise BadRequest("The file in the archive is damaged")
            out.write(chunk)
            left -= len(chunk)

    security.declarePublic("isGML")

    def isGML(self):
        """Checks whether or not this is a GML file.
        The content type must be text/xml and it must end with .gml
        """
        return self.content_type == CONTENT_TYPE_XML and self.id.endswith(".gml")

    security.declareProtected("View", "getQAScripts")

    def getQAScripts(self):
        """Returns a list of QA script labels.
        which can be manually run against the contained XML files
        """
        return qa.can_run_qa_on_files(self, [self])

    security.declareProtected("View", "view_image_or_file")

    def view_image_or_file(self):
        """The default view of the contents of the File or Image."""
        raise Redirect(self.absolute_url())

    def link(self, text="", **args):
        """return a HTML link tag to the file"""
        if text == "":
            text = self.title_or_id()
        strg = '<a href="%s"' % (self.absolute_url())
        for key in list(args.keys()):
            value = args.get(key)
            strg = '%s %s="%s"' % (strg, key, value)
        strg = "%s>%s</a>" % (strg, text)
        return strg

    security.declarePublic("icon_gif")

    def icon_gif(self, REQUEST, RESPONSE):
        """Return an icon for the file's MIME-Type"""
        filename = join(package_home(globals()), self.getIconPath())
        content_type = "image/gif"
        file_size = os.path.getsize(filename)
        file_mtime = os.path.getmtime(filename)
        return RepUtils.http_response_with_file(
            REQUEST,
            RESPONSE,
            open(filename, "rb"),
            content_type,
            file_size,
            file_mtime,
        )

    security.declarePublic("icon_html")

    def icon_html(self):
        """The icon embedded in html with a link to the real file"""
        return '<img src="%s/icon_gif" alt="" />' % self.absolute_url()

    @zpublish(False)
    def get_size(self):
        """Returns the size of the file or image"""
        try:
            return self.data_file.size
        except StorageError:
            return 0

    rawsize = get_size

    @zpublish(False)
    def getFeedbacksForDocument(self):
        """Returns the Feedback objects associated with this document"""
        fbs = []
        catalog = getToolByName(self, DEFAULT_CATALOG, None)
        brains = catalog.searchResults(
            **dict(
                meta_type="Report Feedback",
                document_id=self.id,
                path=self.getParentNode().absolute_url(1),
            )
        )
        for brain in brains:
            try:
                fbs.append(brain.getObject())
            except KeyError as e:
                logger.exception(
                    """Error retrieving feedback object: {} from catalog """
                    """brain: {}""".format(brain.getPath(), str(e))
                )

        return fbs

    @zpublish(False)
    def getExtendedFeedbackForDocument(self):
        """Returns the feedback relevant for a document - URL and title"""
        l_feedbacks = self.getParentNode().objectValues("Report Feedback")
        l_result = {}
        for l_feedback in l_feedbacks:
            if l_feedback.document_id == self.id or (
                l_feedback.automatic == 0
                and l_feedback.releasedate == self.reportingdate
            ):
                l_result[l_feedback.absolute_url()] = l_feedback.title_or_id()
        return l_result

    @zpublish(False)
    def size(self):
        """Returns a formatted stringified version of the file size"""
        return self.data_file.human_readable(self.get_size())

    def compressed_size(self):
        if self.data_file.compressed_safe:
            return (
                self.data_file.compressed_size,
                self.data_file.human_readable(self.data_file.compressed_size),
            )

    security.declareProtected("View management screens", "blob_path")

    def blob_path(self):
        """Return the actual path of the file on server fs as coded by zope
        inside the blob structure"""
        # Multilang unfriendly. But only tech staff debugging will use these...
        not_found = "file not found"
        path = self.data_file.get_fs_path()
        if not path:
            return not_found + " (upload failed?)"
        if not os.path.isfile(path):
            return not_found + " (should have been: %s)" % path

        return path

    @zpublish(False)
    def canHaveOnlineQA(self, upper_limit=None):
        """Determines whether a HTTP QA can be done during Draft, based on
        file size
        The reason is that some on-demand QAs can take more than a minute,
        and that will time out.
        """
        if not upper_limit:
            upper_limit = 4

        # upper_limit is MB
        if self.get_size() > float(upper_limit) * 1024 * 1024:
            return False
        return True

    # Below there are the two forms for the document operations
    # The second one contains links to the file editing (regular upload
    # or editing with external editors e.g. XForms)
    _manage_template = PageTemplateFile(
        os.path.join(package_home(globals()), "zpt/document/manage.zpt")
    )

    security.declareProtected("View", "get_possible_conversions")

    def get_possible_conversions(self):
        """Return possible conversions for the file"""
        exclude_internal = True if self.REQUEST.get("exclude_internal") else False
        local_converters = []
        remote_converters = []
        warning_message = ""
        try:
            (local_converters, remote_converters) = (
                self.Converters.displayPossibleConversions(
                    self.content_type,
                    self.xml_schema_location,
                    self.id,
                    exclude_internal=exclude_internal,
                )
            )
        except requests.ConnectionError as ex:
            local_converters, remote_converters = ex.results
            warning_message = "Local conversion service unavailable."

        self.REQUEST.RESPONSE.setHeader("Content-Type", CONTENT_TYPE_JSON)
        return json.dumps(
            {
                "local_converters": local_converters,
                "remote_converters": remote_converters,
                "warnings": warning_message,
                "file": self.absolute_url(1),
            }
        )

    security.declareProtected("View", "get_qa_scripts")

    def get_qa_scripts(self):
        """Return the available qa scripts for the file."""
        scripts = self.getQAScripts().get(self.id, [])
        engine = self.getEngine()
        http_res = getattr(engine, "qa_httpres", False)
        online_qa = []
        large_qa = []
        res = {"online_qa": online_qa, "large_qa": large_qa}
        for script in scripts:
            qa = {"title": script[1], "script_id": script[0]}
            if self.canHaveOnlineQA(script[3]):
                online_qa.append(qa)
            else:
                large_qa.append(qa)
        res["file"] = parse_uri(self.absolute_url(), http_res)
        self.REQUEST.RESPONSE.setHeader("Content-Type", CONTENT_TYPE_JSON)
        return json.dumps(res)

    security.declareProtected("View", "file_metadata")

    def file_metadata(self):
        """Return the file metadata in JSON format."""
        self.REQUEST.RESPONSE.setHeader("Content-Type", CONTENT_TYPE_JSON)
        res = {}
        try:
            res = {
                "url": self.absolute_url(0),
                "title": self.title,
                "contentType": self.content_type,
                "schemaURL": self.xml_schema_location,
                "uploadDate": self.upload_time().HTML4(),
                "fileSize": self.get_size(),
                "fileSizeHR": self.size(),
                "hash": self.hash,
                "isRestricted": 1 if self.isRestricted() else 0,
            }
        except Exception as e:
            return error_message(
                self,
                "An error occured: {}".format(str(e)),
                REQUEST=self.REQUEST,
            )
        return json.dumps(res)

    security.declareProtected("View", "manage_document")

    def manage_document(self, REQUEST=None, manage_and_edit=False):
        """ """
        return self._manage_template(
            manage_and_edit=manage_and_edit,
        )

    security.declareProtected("View", "manage_edit_document")

    def manage_edit_document(self, REQUEST=None):
        """ """
        return self.manage_document(REQUEST=REQUEST, manage_and_edit=True)

    security.declareProtected("View", "flash_document")
    flash_document = PageTemplateFile(
        os.path.join(package_home(globals()), "zpt/document/flashview.zpt")
    )

    def flash_document_js(self):
        if (
            self.canChangeEnvelope()
            and not self.get_accept_time()
            and not self.released
        ):
            editable = "editable"
        else:
            editable = ""
        return """<script language="javascript" type="text/javascript">
    <!--
    var absolute_url = '%s', country_code = '%s', editable = '%s';
    // -->
    </script>""" % (
            self.absolute_url(),
            self.getParentNode().getCountryCode(),
            editable,
        )

    security.declareProtected(change_envelopes, "manage_restrictDocument")

    def manage_restrictDocument(self, REQUEST=None):
        """Restrict access to this file"""
        self.manage_restrict(ids=[self.id])
        if REQUEST:
            return self.messageDialog(
                message="File restricted to public.",
                action=REQUEST["HTTP_REFERER"],
            )

    security.declareProtected(change_envelopes, "manage_unrestrictDocument")

    def manage_unrestrictDocument(self, REQUEST=None):
        """Remove access restriction for this file"""
        self.manage_unrestrict(ids=[self.id])
        if REQUEST:
            return self.messageDialog(
                message="Document released to public.",
                action=REQUEST["HTTP_REFERER"],
            )

    security.declarePublic("isRestricted")

    def isRestricted(self):
        """Returns True if the file is restricted, False otherwise"""
        return not self.acquiredRolesAreUsedBy("View")

    ################################
    # Protected management methods #
    ################################
    # Management Interface
    _manage_main_template = PageTemplateFile(
        os.path.join(package_home(globals()), "zpt/document/edit.zpt")
    )

    def manage_main(self, REQUEST=None):
        """ """
        # TODO refactor manage_main and manage_document
        local_converters = []
        remote_converters = []
        warning_message = ""
        try:
            (local_converters, remote_converters) = (
                self.Converters.displayPossibleConversions(
                    self.content_type, self.xml_schema_location, self.id
                )
            )
        except requests.ConnectionError as ex:
            local_converters, remote_converters = ex.results
            warning_message = "Local conversion service unavailable."
        return self._manage_main_template(
            warnings=warning_message,
            converters=[local_converters, remote_converters],
        )

    @refuse_when_frozen
    def manage_editDocument(
        self,
        title="",
        content_type=None,
        xml_schema_location=None,
        applyRestriction="",
        restricted="",
        REQUEST=None,
    ):
        """Manage the edited values"""
        if content_type is not None:
            self.content_type = content_type
        if xml_schema_location is not None:
            self.xml_schema_location = xml_schema_location
        if self.title != title:
            self.title = title
        if hasattr(self, "is_globally_restricted") and self.is_globally_restricted():
            self.manage_restrictDocument()
        else:
            if applyRestriction:
                if restricted:
                    self.manage_restrictDocument()
                else:
                    self.manage_unrestrictDocument()
        self.reindexObject()  # update ZCatalog
        notify(ObjectModifiedEvent(self))
        if REQUEST is not None:
            return self.messageDialog(
                message="The properties of %s have been changed!" % self.id,
                action=REQUEST["HTTP_REFERER"],
            )

    def is_compressed(self):
        return self.data_file.compressed_safe

    def parsed_absolute_url(self):
        engine = self.getEngine()
        http_res = getattr(engine, "qa_httpres", False)

        return parse_uri(self.absolute_url(), http_res)

    @property
    def hash(self):
        return getattr(self, "_hash", None)

    @hash.setter
    def hash(self, value):
        self._hash = value

    @zpublish(False)
    def generate_hash(self, limit=None):
        """Generate a sha256 hash for the file; with `limit`, refuse a file
        bigger than that once unpacked"""

        BLOCK_SIZE = 65536  # The size of each read from the file

        file_hash = hashlib.sha256()
        with self.data_file.open("rb") as f:
            if limit is not None:
                f = SizeCappedReader(f, limit, name=self.getId())
            fb = f.read(BLOCK_SIZE)
            while len(fb) > 0:  # While there is still data being read
                file_hash.update(fb)  # Update the hash
                fb = f.read(BLOCK_SIZE)  # Read the next block from the file

        self.hash = file_hash.hexdigest()

    manage_uploadForm = PageTemplateFile(
        os.path.join(package_home(globals()), "zpt/document/upload.zpt")
    )

    @refuse_when_frozen
    def manage_file_upload(
        self, file="", content_type="", REQUEST=None, preserve_mtime=False
    ):
        """Upload file from local directory"""

        if not content_type:
            content_type = self._get_content_type(file)
        self.data_file.content_type = content_type
        orig_size = self._compute_uncompressed_size(file)

        skip_compress = False
        crc = None
        if isinstance(file, ZZipFileRaw) and file.allowRaw:
            skip_compress = True
            crc = file.CRC

        with self.data_file.open(
            "wb",
            orig_size=orig_size,
            skip_decompress=skip_compress,
            crc=crc,
            preserve_mtime=preserve_mtime,
        ) as data_file_handle:
            if hasattr(file, "read"):
                for chunk in RepUtils.iter_file_data(file):
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    data_file_handle.write(chunk)
            else:
                data = file
                if isinstance(data, str):
                    data = data.encode("utf-8")
                data_file_handle.write(data)

        # a file of a zip archive is unpacked as it is read: read no more of it
        # than the archive said it holds
        limit = orig_size if isinstance(file, ZZipFile) else None
        with self.data_file.open("rb") as data_file_handle:
            if limit is not None:
                data_file_handle = SizeCappedReader(
                    data_file_handle, limit, name=self.getId()
                )
            engine = getattr(self, ENGINE_ID, None)
            if engine:
                # the size unpacked: a file stored compressed cannot tell it
                engine.AVService.scan(
                    data_file_handle, filesize=orig_size, filename=self.getId()
                )
            if self.content_type == CONTENT_TYPE_XML:
                self.xml_schema_location = detect_schema(data_file_handle)
            else:
                self.xml_schema_location = ""

        self.generate_hash(limit)
        self.accept_time = None
        self.logUpload()
        # update ZCatalog
        self._p_changed = 1
        self.reindexObject()
        if REQUEST is not None:
            return self.messageDialog(
                message="The file was uploaded successfully!",
                action=REQUEST["HTTP_REFERER"],
            )

    ################################
    # Private methods              #
    ################################

    def _get_content_type(self, file_or_content):
        """Determine the mime-type from metadata (file name, headers)
        and eventually the actual content (Note that zope's guess_content_type
        does a poor job detecting from content - it's main detection is based
        on name/ext
        """
        name = None
        headers = None
        if hasattr(file_or_content, "filename"):
            name = file_or_content.filename
            headers = getattr(file_or_content, "headers", None)
            readCount = 100
            body = file_or_content.read(readCount)
            is_ZipRaw = isinstance(file_or_content, ZZipFileRaw)
            if is_ZipRaw:
                name = getattr(file_or_content, "currentFilename", name)
            if (
                is_ZipRaw
                and file_or_content.allowRaw
                and (readCount < 0 or readCount >= ZZipFileRaw.SKIP_RAW_THRESHOLD)
            ):
                file_or_content.rewindRaw()
            else:
                file_or_content.seek(0)
        else:
            body = file_or_content[:100]
            # Ensure body is bytes for guess_content_type
            if isinstance(body, str):
                body = body.encode("utf-8")

        if not name:
            name = self.id.lower()
        else:
            name = name.lower()
        if name.endswith(".gml"):
            return CONTENT_TYPE_XML
        elif name.endswith(".rar"):
            return "application/x-rar-compressed"

        h_ctype = None
        if headers and "content-type" in headers:
            h_ctype = headers["content-type"]

        # This will discard only utf8 BOM in case it is there
        # zope mime type guessing fails if BOM present
        body = RepUtils.discard_utf8_bom(body)
        content_type, enc = guess_content_type(name, body)
        if content_type == "text/x-unknown-content-type" and h_ctype:
            return h_ctype

        return content_type

    def _compute_uncompressed_size(self, file_or_content):
        if isinstance(file_or_content, FileUpload) or isinstance(
            file_or_content, IOBase
        ):
            pos = file_or_content.tell()
            file_or_content.seek(0, 2)
            size = file_or_content.tell()
            file_or_content.seek(pos)
            return size
        elif isinstance(file_or_content, (str, bytes)):
            return len(file_or_content)
        elif isinstance(file_or_content, StringIO):
            return file_or_content.len
        elif isinstance(file_or_content, ZZipFileRaw):
            return file_or_content.orig_size
        elif isinstance(file_or_content, ZZipFile):
            return file_or_content.tell()
        else:
            raise RuntimeError("Unable to compute uncompressed size")

    @zpublish(False)
    def export_to_file(self, dst_path, file_id=None):
        """Export the document's file to a File in dst_path"""
        dst = self.unrestrictedTraverse(dst_path)
        if not file_id:
            file_id = self.getId()
        f = getattr(self, "data_file")
        with f.open() as fc:
            dst.manage_addFile(file_id, file=fc.read())

    security.declareProtected("View", "xml_to_json")

    def xml_to_json(self, REQUEST=None):
        """Convert XML content to JSON if the document is an XML file

        GET request returns full XML as JSON.
        POST request accepts a JSON object in body with format:
        {
            "tags": ["tag1", "path/to/tag2"]
        }
        to filter specific tags or paths to tags.
        """
        if self.content_type != CONTENT_TYPE_XML:
            return error_message(
                self, "This document is not an XML file", REQUEST=REQUEST
            )

        try:
            tags = None
            if REQUEST is not None:
                method = REQUEST.get("REQUEST_METHOD", "")
                if method == "POST":
                    try:
                        body = REQUEST.get("BODY")
                        if not body:
                            return error_message(
                                self, "Empty request body", REQUEST=REQUEST
                            )

                        try:
                            body_json = json.loads(body)
                        except ValueError:
                            return error_message(
                                self,
                                "Invalid JSON in request body",
                                REQUEST=REQUEST,
                            )

                        tags = body_json.get("tags")
                        if not tags:
                            return error_message(
                                self,
                                "Missing or empty 'tags' key in request body",
                                REQUEST=REQUEST,
                            )

                        if not isinstance(tags, list):
                            return error_message(
                                self,
                                "'tags' must be a list of strings",
                                REQUEST=REQUEST,
                            )

                        def is_valid_tag(tag):
                            """Check if a tag is a non-empty string."""
                            return isinstance(tag, str) and tag.strip()

                        if not all(is_valid_tag(tag) for tag in tags):
                            return error_message(
                                self,
                                "All tags must be non-empty strings",
                                REQUEST=REQUEST,
                            )

                    except Exception as e:
                        logger.exception("Error processing request body")
                        return error_message(
                            self,
                            "Error processing request: %s" % str(e),
                            REQUEST=REQUEST,
                        )
                elif method != "GET":
                    return error_message(
                        self,
                        "Only GET and POST methods are supported",
                        REQUEST=REQUEST,
                    )

            xml_content = None
            with self.data_file.open() as xml_file:
                try:
                    xml_content = xml_file.read()
                    xml_dict = xmltodict.parse(xml_content)
                except Exception as e:
                    logger.exception("Error parsing XML content")
                    return error_message(
                        self, "Error parsing XML: %s" % str(e), REQUEST=REQUEST
                    )

            if tags:
                # Pre-process tags for efficiency
                simple_tags = set()
                path_tags = []
                for tag in tags:
                    tag = tag.strip()
                    if "/" in tag:
                        parts = [p.strip() for p in tag.split("/") if p.strip()]
                        if parts:
                            path_tags.append(parts)
                    elif tag:
                        simple_tags.add(tag)

                def check_path(current_path, tag_path):
                    """Check if current path matches any of the
                    requested tag paths
                    """
                    return len(current_path) <= len(tag_path) and all(
                        cp == tp for cp, tp in zip(current_path, tag_path)
                    )

                def filter_content(content, current_path=None):
                    """Recursively filter content based on tag
                    paths/simple tags
                    """
                    if current_path is None:
                        current_path = []

                    if not isinstance(content, (dict, list)):
                        return content

                    if isinstance(content, dict):
                        filtered = {}
                        for key, value in content.items():
                            new_path = current_path + [key]

                            # Handle attributes
                            if key.startswith("@"):
                                if key in simple_tags or any(
                                    new_path == path for path in path_tags
                                ):
                                    filtered[key] = value
                                continue

                            is_match = key in simple_tags or any(
                                new_path == path for path in path_tags
                            )
                            is_parent = any(
                                check_path(new_path, path) for path in path_tags
                            )
                            should_traverse = bool(simple_tags or is_parent)

                            # Add matched content
                            if is_match:
                                filtered[key] = value

                            # Process nested content if needed
                            is_dl = isinstance(value, (dict, list))
                            if should_traverse and is_dl:
                                nested = filter_content(value, new_path)
                                if nested:
                                    if key not in filtered:
                                        filtered[key] = nested
                                    elif isinstance(filtered[key], dict):
                                        filtered[key].update(nested)

                        return filtered if filtered else None

                    # Handle lists
                    filtered = []
                    for item in content:
                        nested = filter_content(item, current_path)
                        if nested:
                            filtered.append(nested)
                    return filtered if filtered else None

                # Apply filtering to the whole document
                filtered_dict = {}
                for root_key, root_value in xml_dict.items():
                    filtered = filter_content(root_value, [root_key])
                    if filtered:
                        filtered_dict[root_key] = filtered

                if not filtered_dict:
                    return error_message(
                        self,
                        "No content found for specified tags",
                        REQUEST=REQUEST,
                    )

                xml_dict = filtered_dict

            if REQUEST is not None:
                REQUEST.RESPONSE.setHeader("Content-Type", CONTENT_TYPE_JSON)
                return json.dumps(xml_dict, indent=2, ensure_ascii=False).encode(
                    "utf-8"
                )
            return xml_dict

        except Exception as e:
            logger.exception("Error in xml_to_json")
            return error_message(
                self,
                "Error converting XML to JSON: %s" % str(e),
                REQUEST=REQUEST,
            )


InitializeClass(Document)
