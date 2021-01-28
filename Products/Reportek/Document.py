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

__version__ = '$Rev$'[6:-2]

import hashlib
import io
import json
import logging
import os
import string
from os.path import join
from StringIO import StringIO
from time import time

import Globals
import IconShow
import RepUtils
import requests
import transaction
from AccessControl import ClassSecurityInfo, getSecurityManager
# Product imports
from blob import FileContainer, StorageError
from constants import ENGINE_ID, QAREPOSITORY_ID
from DateTime import DateTime
from Globals import package_home
from interfaces import IDocument
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.RepUtils import DFlowCatalogAware, parse_uri
from Products.ZCatalog.CatalogAwareness import CatalogAware
from webdav.common import rfc1123_date
from XMLInfoParser import SchemaError, detect_schema
from zExceptions import Redirect
from zip_content import ZZipFile, ZZipFileRaw
from zope.contenttype import guess_content_type
from zope.event import notify
from zope.interface import implements
from zope.lifecycleevent import ObjectModifiedEvent
from ZPublisher.HTTPRequest import FileUpload

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

manage_addDocumentForm = PageTemplateFile('zpt/document/add', globals())


def error_message(ctx, message, action=None, REQUEST=None):
    if not action:
        action = ctx.absolute_url()
    if REQUEST is not None:
        accept = REQUEST.environ.get("HTTP_ACCEPT")
        if accept == 'application/json':
            REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
            error = {
                'title': 'Error',
                'description': message
            }
            data = {
                'errors': [error],
            }
            return json.dumps(data, indent=4)
        else:
            return ctx.messageDialog(
                message=message,
                action=action
            )
    return ''

def success_message(ctx, objs, message=None, errors=None, action=None, REQUEST=None):
    if not action:
        action = ctx.absolute_url()
    if not errors:
        errors = []
    if REQUEST is not None:
        accept = REQUEST.environ.get("HTTP_ACCEPT")
        if accept == 'application/json':
            REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
            REQUEST.RESPONSE.setStatus(201)
            files = []
            for obj in objs:
                files.append({
                    'url': obj.absolute_url(0),
                    'title': obj.title,
                    'contentType': obj.content_type,
                    'schemaURL': obj.xml_schema_location,
                    'uploadDate': obj.upload_time().HTML4(),
                    'fileSize': obj.get_size(),
                    'fileSizeHR': obj.size(),
                    'isRestricted': 1 if obj.isRestricted() else 0
                })
            data = {
                'files': files,
                'errors': errors
            }
            return json.dumps(data, indent=4)
        return ctx.messageDialog(
            message=message,
            action=action)
    return ''


def manage_addDocument(self, id='', title='', file='', content_type='',
                       filename='', restricted='', disallow='', REQUEST=None,
                       deferred_compress=None):
    """Add a Document to a folder. The form can be called with three variables
       set in the session object: default_restricted, force_restricted and
       disallow. This will set the restricted flag in the form or
    """

    is_object = hasattr(file, 'read') and (getattr(file, 'filename', None) or filename)
    if is_object and not filename:
        filename = getattr(file, 'filename')
    is_str = file and isinstance(file, basestring)

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
        id = id[max(string.rfind(id, '/'),
                    string.rfind(id, '\\'),
                    string.rfind(id, ':')
                    ) + 1:]
        id = id.strip()
        id = RepUtils.cleanup_id(id)

        # Check to see if file has an extension which is disallowed
        if disallow:
            disallow = disallow.replace(' ', '').split(',')
            for ext in disallow:
                if not ext.startswith('.'):
                    ext = ''.join(['.', ext])
                if id.endswith(ext):
                    return error_message(self, '{} files are disallowed in this context'.format(ext), REQUEST=REQUEST)

        # delete the previous file with the same id, if exists
        if self.get(id) and isinstance(self.get(id), Document):
            save_id = id
            id += '___tmp_%f' % time()

        obj = Document(id, title=title, deferred_compress=deferred_compress)
        self = self.this()
        self._setObject(id, obj)
        obj = self._getOb(id)
        try:
            obj.manage_file_upload(file, content_type)
        except SchemaError as e:
            self.manage_delObjects(id)
            logger.exception('The file is an invalid XML (reason: %s)' % str(e.args))
            return error_message(self, 'The file is an invalid XML (reason: %s)' % str(e.args), REQUEST=REQUEST)
        if save_id:
            self.manage_delObjects(save_id)
            transaction.commit()
            self.manage_renameObject(id, save_id)
            id = save_id
        engine = getattr(self.getPhysicalRoot(), ENGINE_ID, None)
        globally_restricted_site = getattr(engine, 'globally_restricted_site', False)
        if restricted or globally_restricted_site:
            obj.manage_restrictDocument()
        obj.reindex_object()
        if REQUEST is not None:
            # This is an ugly hack, sometimes the PARENTS are in reverse order
            # TODO: Find a better way to handle the issue
            if len(REQUEST.PARENTS) > 1:
                pobj = REQUEST.PARENTS[0]
                if not REQUEST.PARENTS[0].absolute_url(1):
                    pobj = REQUEST.PARENTS[-1]
            ppath = string.join(pobj.getPhysicalPath(), '/')
            msg = 'The file %s was successfully created!' % id
            return success_message(self, [obj], message=msg,
                                   action=ppath, REQUEST=REQUEST)
        else:
            return id
    else:
        return error_message(self, 'You must specify a file!', REQUEST=REQUEST)


class Document(CatalogAware, SimpleItem, IconShow.IconShow, DFlowCatalogAware):
    """ An External Document allows indexing and conversions.

    .. attribute:: data_file

        The document's binary content as :class:`.FileContainer` object.
    """

    implements(IDocument)
    icon = 'misc_/Reportek/document_gif'

    manage_options = (
        {'label':'Edit',                'action': 'manage_main'       },
        {'label':'View/Download',       'action': ''                  },
        {'label':'Upload',              'action': 'manage_uploadForm' },
        {'label':'Security',            'action': 'manage_access'     },
    )

    security = ClassSecurityInfo()

    security.declareProtected('Change permissions', 'manage_access')

    security.declareProtected('Change Envelopes', 'manage_editDocument')
    security.declareProtected('Change Envelopes', 'manage_main')
    security.declareProtected('Change Envelopes', 'manage_uploadForm')
    security.declareProtected('Change Envelopes', 'manage_file_upload')

    security.declareProtected('View', 'index_html')
    security.declareProtected('View', 'link')
    security.declareProtected('View', 'get_size')
    security.declareProtected('View', 'getContentType')
    security.declareProtected('View', '__str__')
    security.declarePrivate('data_file')

    meta_type = 'Report Document'

    ################################
    # Init method                  #
    ################################

    def __init__(self, id, title='', content_type='', deferred_compress=None):
        """ Initialize a new instance of Document
            If a document is created through FTP, self.absolute_url doesn't work.
        """
        self.id = id
        self.title = title
        self.xml_schema_location = '' #needed for XML files
        self.accept_time = None
        ctor_kwargs = {}
        if content_type:
            ctor_kwargs['content_type'] = content_type
        if deferred_compress:
            ctor_kwargs['compress'] = 'deferred'
        self.data_file = FileContainer(**ctor_kwargs)

    ################################
    # Public methods               #
    ################################

    @property
    def content_type(self):
        old_ct = self.__dict__.get('content_type', None)
        if old_ct:
            return old_ct
        return self.data_file.content_type

    @content_type.setter
    def content_type(self, value):
        if 'content_type' in self.__dict__:
            self.__dict__['content_type'] = value
        else:
            self.data_file.content_type = value

    def __str__(self): return self.index_html(self.REQUEST, self.REQUEST.RESPONSE)

    def __len__(self): return 1

    def upload_time(self):
        """ Return the upload time
        """
        return DateTime(self.data_file.mtime)

    def get_accept_time(self):
        """ A document can have an accepted status. It is set by the client, and
            is used to force the file to be immutable even if the envelope is returned
            to draft state. It is used in second and third delivery round, to tell
            the reporter that some files have to be redelivered, but some file are
            accepted and are processed.

            It was used in Article 17 - 2007.
        """
        if getattr(self, 'accept_time', None):
            return DateTime(self.accept_time)
        return None

    security.declareProtected('Change Feedback', 'set_accept_time')
    def set_accept_time(self, totime=1):
        """ Sets the accept time or clears it if totime != 1
        """
        if totime == 1:
            self.accept_time = time()
        else:
            self.accept_time = None

    HEAD__roles__=None
    def HEAD(self, REQUEST, RESPONSE):
        """ Support for HEAD requests from search engines etc. """
        RESPONSE.setHeader('Last-Modified', rfc1123_date(self.data_file.mtime))
        RESPONSE.setHeader('Content-Length', self.data_file.size)
        RESPONSE.setHeader('Content-Type', self.content_type)
        return ''

    security.declarePublic('getMyOwner')
    def getMyOwner(self):
        """ Find the owner in the local roles. """
        for a, b in self.get_local_roles():
            if 'Owner' in b:
                return a
        return ''

    security.declarePublic('getMyOwnerName')
    def getMyOwnerName(self):
        """ Find the owner in the local roles.
            Then use LDAP to find the user's full name.
            TODO: Move LDAP dependency to ReportekEngine.
        """
        return self.getLDAPUserCanonicalName(self.getLDAPUser(self.getMyOwner()))

    def logUpload(self):
        """ Log file upload and any reuploads into the envelope history.
            The workitems' event logs are used since these are displayed
            on the envelope's history tab
        """
        if self.REQUEST and getattr(self.REQUEST, 'AUTHENTICATED_USER', None):
            for l_w in self.getWorkitemsActiveForMe(self.REQUEST):
                l_w.addEvent('file upload', 'File: {0} ({1})'.format(self.id,
                                                                     self.data_file.human_readable(self.data_file.size)))

    def index_html(self, REQUEST, RESPONSE, icon=0):
        """ Returns the contents of the file.  Also, sets the
            Content-Type HTTP header to the objects content type.
        """
        if icon:
            return self.icon_gif(REQUEST, RESPONSE)

        skip_decomp = False
        ae = REQUEST.getHeader('Accept-Encoding')
        # TODO also take weights into consideration (gzip;q=0,deflate;q=1)
        if ae and ae.lower().startswith('gzip'):
            skip_decomp = True
        with self.data_file.open(skip_decompress=skip_decomp) as data_file_handle:
            size = self.data_file.size
            if skip_decomp and self.is_compressed():
                # This is hackish. If the client asked for gzip compression first
                # and we are storing the content compressed
                # then instruct the FileContiner not to decompress the fetched content
                # and tell the client that we are serving his content gzipped
                RESPONSE.setHeader('content-encoding','gzip')
                size = self.data_file.compressed_size
            RepUtils.http_response_with_file(
                REQUEST, RESPONSE, data_file_handle,
                self.content_type, size, self.data_file.mtime)

    security.declarePublic('isGML')
    def isGML(self):
        """ Checks whether or not this is a GML file.
            The content type must be text/xml and it must end with .gml
        """
        return self.content_type == 'text/xml' and self.id[-4:] == '.gml'

    security.declareProtected('View', 'getQAScripts')
    def getQAScripts(self):
        """ Returns a list of QA script labels.
            which can be manually run against the contained XML files
        """
        return getattr(self, QAREPOSITORY_ID).canRunQAOnFiles([self])

    def view_image_or_file(self):
        """ The default view of the contents of the File or Image. """
        raise Redirect, self.absolute_url()

    def link(self, text='', **args):
        """ return a HTML link tag to the file """
        if text=='': text = self.title_or_id()
        strg = '<a href="%s"' % (self.absolute_url())
        for key in args.keys():
            value = args.get(key)
            strg = '%s %s="%s"' % (strg, key, value)
        strg = '%s>%s</a>' % (strg, text)
        return strg

    security.declarePublic('icon_gif')
    def icon_gif(self, REQUEST, RESPONSE):
        """ Return an icon for the file's MIME-Type """
        filename = join(package_home(globals()), self.getIconPath())
        content_type = 'image/gif'
        file_size =  os.path.getsize(filename)
        file_mtime = os.path.getmtime(filename)
        with open(filename, 'rb') as data_file:
            RepUtils.http_response_with_file(
                REQUEST, RESPONSE, data_file,
                content_type, file_size, file_mtime)

    security.declarePublic('icon_html')
    def icon_html(self):
        """ The icon embedded in html with a link to the real file """
        return '<img src="%s/icon_gif" alt="" />' % self.absolute_url()

    def get_size(self):
        """ Returns the size of the file or image """
        try:
            return self.data_file.size
        except StorageError:
            return 0

    rawsize = get_size

    def getFeedbacksForDocument(self):
        """ Returns the Feedback objects associated with this document """
        fbs = []
        brains = self.Catalog(meta_type='Report Feedback',
                              document_id=self.id,
                              path=self.getParentNode().absolute_url(1))
        for brain in brains:
            try:
                fbs.append(brain.getObject())
            except KeyError as e:
                logger.error("Error retrieving feedback object: {} from catalog brain: {}".format(brain.getPath(), str(e)))

        return fbs

    def getExtendedFeedbackForDocument(self):
        """ Returns the feedback relevant for a document - URL and title """
        l_feedbacks = self.getParentNode().objectValues('Report Feedback')
        l_result = {}
        for l_feedback in l_feedbacks:
            if l_feedback.document_id == self.id or (l_feedback.automatic == 0 and l_feedback.releasedate == self.reportingdate):
                l_result[l_feedback.absolute_url()] = l_feedback.title_or_id()
        return l_result

    def size(self):
        """ Returns a formatted stringified version of the file size """
        return self.data_file.human_readable(self.get_size())

    def compressed_size(self):
        if self.data_file.compressed_safe:
            return (self.data_file.compressed_size,
                    self.data_file.human_readable(self.data_file.compressed_size) )

    security.declareProtected('View management screens', 'blob_path')
    def blob_path(self):
        """ Return the actual path of the file on server fs as coded by zope
        inside the blob structure"""
        # Multilang unfriendly. But only tech staff debugging will use these...
        not_found = "file not found"
        path = self.data_file.get_fs_path()
        if not path:
            return not_found + " (upload failed?)"
        if not os.path.isfile(path):
            return not_found + " (should have been: %s)" % path

        return path

    def canHaveOnlineQA(self, upper_limit=None):
        """ Determines whether a HTTP QA can be done during Draft, based on file size
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
    _manage_template = PageTemplateFile('zpt/document/manage', globals())

    security.declareProtected('View', 'get_possible_conversions')
    def get_possible_conversions(self):
        """Return possible conversions for the file"""
        exclude_internal = True if self.REQUEST.get('exclude_internal') else False
        local_converters = []
        remote_converters = []
        warning_message = ''
        try:
            (local_converters, remote_converters) = \
                self.Converters.displayPossibleConversions(self.content_type,
                                                           self.xml_schema_location,
                                                           self.id,
                                                           exclude_internal=exclude_internal
                                                           )
        except requests.ConnectionError as ex:
           local_converters, remote_converters = ex.results
           warning_message='Local conversion service unavailable.'

        self.REQUEST.RESPONSE.setHeader('Content-Type',
                                        'application/json')
        return json.dumps({
            'local_converters': local_converters,
            'remote_converters': remote_converters,
            'warnings': warning_message,
            'file': self.absolute_url(1)
        })

    security.declareProtected('View', 'get_qa_scripts')
    def get_qa_scripts(self):
        """Return the available qa scripts for the file."""
        scripts = self.getQAScripts().get(self.id, [])
        engine = self.getEngine()
        http_res = getattr(engine, 'qa_httpres', False)
        online_qa = []
        large_qa = []
        res = {'online_qa': online_qa,
               'large_qa': large_qa}
        for script in scripts:
            qa = {'title': script[1],
                  'script_id': script[0]}
            if self.canHaveOnlineQA(script[3]):
                online_qa.append(qa)
            else:
                large_qa.append(qa)
        res['file'] = parse_uri(self.absolute_url(), http_res)
        self.REQUEST.RESPONSE.setHeader('Content-Type',
                                        'application/json')
        return json.dumps(res)

    security.declareProtected('View', 'manage_document')
    def manage_document(self, REQUEST=None, manage_and_edit=False):
        """ """
        return self._manage_template(
                   manage_and_edit=manage_and_edit,
               )

    security.declareProtected('View', 'manage_edit_document')
    def manage_edit_document(self, REQUEST=None):
        """ """
        return self.manage_document(REQUEST=REQUEST, manage_and_edit=True)

    security.declareProtected('View', 'flash_document')
    flash_document = PageTemplateFile('zpt/document/flashview', globals())

    def flash_document_js(self):
        if self.canChangeEnvelope() and not self.get_accept_time() and not self.released: editable = 'editable'
        else: editable = ''
        return """<script language="javascript" type="text/javascript">
    <!--
    var absolute_url = '%s', country_code = '%s', editable = '%s';
    // -->
    </script>""" % (self.absolute_url(), self.getParentNode().getCountryCode(), editable)

    security.declareProtected('Change Envelopes', 'manage_restrictDocument')
    def manage_restrictDocument(self, REQUEST=None):
        """ Restrict access to this file
        """
        self.manage_restrict(ids=[self.id])
        if REQUEST:
            return self.messageDialog(
                            message='File restricted to public.',
                            action=REQUEST['HTTP_REFERER'])

    security.declareProtected('Change Envelopes', 'manage_unrestrictDocument')
    def manage_unrestrictDocument(self, REQUEST=None):
        """ Remove access restriction for this file
        """
        self.manage_unrestrict(ids=[self.id])
        if REQUEST:
            return self.messageDialog(
                            message='Document released to public.',
                            action=REQUEST['HTTP_REFERER'])

    security.declarePublic('isRestricted')
    def isRestricted(self):
        """ Returns True if the file is restricted, False otherwise """
        return not self.acquiredRolesAreUsedBy('View')

    ################################
    # Protected management methods #
    ################################
    # Management Interface
    _manage_main_template = PageTemplateFile('zpt/document/edit', globals())
    def manage_main(self, REQUEST=None):
        """ """
        #TODO refactor manage_main and manage_document
        local_converters = []
        remote_converters = []
        warning_message = ''
        try:
            (local_converters, remote_converters) = \
                    self.Converters.displayPossibleConversions(
                        self.content_type,
                        self.xml_schema_location,
                        self.id
                    )
        except requests.ConnectionError as ex:
           local_converters, remote_converters = ex.results
           warning_message='Local conversion service unavailable.'
        return self._manage_main_template(
                   warnings=warning_message,
                   converters=[local_converters, remote_converters]
               )

    def manage_editDocument(self, title='',
                            content_type=None, xml_schema_location=None,
                            applyRestriction='', restricted='',
                            REQUEST=None):
        """ Manage the edited values """
        if content_type is not None:
            self.content_type = content_type
        if xml_schema_location is not None:
            self.xml_schema_location = xml_schema_location
        if self.title!=title:
            self.title = title
        engine = getattr(self.getPhysicalRoot(), ENGINE_ID, None)
        globally_restricted_site = getattr(engine, 'globally_restricted_site', False)
        if globally_restricted_site:
            self.manage_restrictDocument()
        else:
            if applyRestriction:
                if restricted:
                    self.manage_restrictDocument()
                else:
                    self.manage_unrestrictDocument()
        self.reindex_object()  # update ZCatalog
        notify(ObjectModifiedEvent(self))
        if REQUEST is not None:
            return self.messageDialog(
                            message="The properties of %s have been changed!" % self.id,
                            action=REQUEST['HTTP_REFERER'])

    def is_compressed(self):
        return self.data_file.compressed_safe

    def parsed_absolute_url(self):
        l_res = {}
        engine = self.getEngine()
        http_res = getattr(engine, 'qa_httpres', False)

        return parse_uri(self.absolute_url(), http_res)

    @property
    def hash(self):
        return getattr(self, '_hash', None)

    @hash.setter
    def hash(self, value):
        self._hash = value

    def generate_hash(self):
        """Generate a sha256 hash for the file"""

        BLOCK_SIZE = 65536  # The size of each read from the file

        file_hash = hashlib.sha256()
        with self.data_file.open('rb') as f:
            fb = f.read(BLOCK_SIZE)
            while len(fb) > 0:  # While there is still data being read from the file
                file_hash.update(fb)  # Update the hash
                fb = f.read(BLOCK_SIZE)  # Read the next block from the file

        self.hash = file_hash.hexdigest()

    manage_uploadForm = PageTemplateFile('zpt/document/upload', globals())
    def manage_file_upload(self, file='', content_type='', REQUEST=None, preserve_mtime=False):
        """ Upload file from local directory """

        if not content_type:
            content_type = self._get_content_type(file)
        self.data_file.content_type = content_type
        orig_size = self._compute_uncompressed_size(file)

        skip_compress = False
        crc = None
        if isinstance(file, ZZipFileRaw) and file.allowRaw:
            skip_compress = True
            crc = file.CRC
        engine = getattr(self.getPhysicalRoot(), ENGINE_ID, None)
        engine.AVService.scan(file)
        with self.data_file.open('wb', orig_size=orig_size, skip_decompress=skip_compress, crc=crc, preserve_mtime=preserve_mtime) as data_file_handle:
            if hasattr(file, 'read'):
                for chunk in RepUtils.iter_file_data(file):
                    data_file_handle.write(chunk)
            else:
                data_file_handle.write(file)

        if self.content_type == 'text/xml':
            with self.data_file.open('rb') as data_file_handle:
                self.xml_schema_location = detect_schema(data_file_handle)
        else:
            self.xml_schema_location = ''

        self.generate_hash()
        self.accept_time = None
        self.logUpload()
        # update ZCatalog
        self._p_changed = 1
        self.reindex_object()
        if REQUEST is not None:
            return self.messageDialog(
                            message="The file was uploaded successfully!",
                            action=REQUEST['HTTP_REFERER'])


    ################################
    # Private methods              #
    ################################

    def _get_content_type(self, file_or_content):
        """ Determine the mime-type from metadata (file name, headers)
        and eventually the actual content (Note that zope's guess_content_type does a poor
        job detecting from content - it's main detection is based on name/ext
        """
        name = None
        headers = None
        if hasattr(file_or_content, 'filename'):
            name = file_or_content.filename
            headers = getattr(file_or_content, 'headers', None)
            readCount = 100
            body = file_or_content.read(readCount)
            is_ZipRaw = isinstance(file_or_content, ZZipFileRaw)
            if is_ZipRaw:
                name = getattr(file_or_content, 'currentFilename', name)
            if (is_ZipRaw and file_or_content.allowRaw and
               (readCount < 0 or
                    readCount >= ZZipFileRaw.SKIP_RAW_THRESHOLD)):
                file_or_content.rewindRaw()
            else:
                file_or_content.seek(0)
        else:
            body = file_or_content[:100]

        if not name:
            name = self.id.lower()
        else:
            name = name.lower()
        if name.endswith('.gml'):
            return 'text/xml'
        elif name.endswith('.rar'):
            return 'application/x-rar-compressed'

        h_ctype = None
        if headers and 'content-type' in headers:
            h_ctype = headers['content-type']

        # This will discard only utf8 BOM in case it is there
        # zope mime type guessing fails if BOM present
        body = RepUtils.discard_utf8_bom(body)
        content_type, enc = guess_content_type(name, body)
        if content_type == 'text/x-unknown-content-type' and h_ctype:
            return h_ctype

        return content_type

    def _compute_uncompressed_size(self, file_or_content):
        if isinstance(file_or_content, FileUpload) or isinstance(file_or_content, file):
            pos = file_or_content.tell()
            file_or_content.seek(0, 2)
            size = file_or_content.tell()
            file_or_content.seek(pos)
            return size
        elif isinstance(file_or_content, basestring):
            return len(file_or_content)
        elif isinstance(file_or_content, StringIO):
            return file_or_content.len
        elif isinstance(file_or_content, ZZipFileRaw):
            return file_or_content.orig_size
        elif isinstance(file_or_content, ZZipFile):
            return file_or_content.tell()
        else:
            raise RuntimeError("Unable to compute uncompressed size")

    def export_to_file(self, dst_path, file_id=None):
        """Export the document's file to a File in dst_path"""
        dst = self.unrestrictedTraverse(dst_path)
        if not file_id:
            file_id = self.getId()
        f = getattr(self, 'data_file')
        fc = f.open()
        dst.manage_addFile(file_id, file=fc.read())
        fc.close()


Globals.InitializeClass(Document)
