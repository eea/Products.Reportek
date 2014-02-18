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

__version__='$Rev$'[6:-2]

import Globals, IconShow
import requests
import stat
import urllib, os, types, string
from __main__ import *
from AccessControl import getSecurityManager, ClassSecurityInfo
from Products.ZCatalog.CatalogAwareness import CatalogAware
from OFS.SimpleItem import SimpleItem
from zExceptions import Forbidden, Redirect
from Globals import MessageDialog, package_home
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
try: from zope.contenttype import guess_content_type # Zope 2.10 and newer
except: from zope.app.content_types import guess_content_type # Zope 2.9 and older
from webdav.common import rfc1123_date
from DateTime import DateTime
from mimetools import choose_boundary
from os.path import join, isfile
from zope.interface import implements
try:
    from zope.container.interfaces import IObjectRemovedEvent, IObjectAddedEvent
except ImportError:
    from zope.app.container.interfaces import IObjectRemovedEvent, IObjectAddedEvent
from time import time
try: from cStringIO import StringIO
except: from StringIO import StringIO

# Product imports
import RepUtils
from Converters import Converters
from XMLInfoParser import detect_schema
from constants import CONVERTERS_ID, QAREPOSITORY_ID, ENGINE_ID
from interfaces import IDocument
from blob import FileContainer, StorageError
from ZODB.blob import FilesystemHelper

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

manage_addDocumentForm = PageTemplateFile('zpt/document/add', globals())

def manage_addDocument(self, id='', title='',
        file='', content_type='', restricted='', REQUEST=None):
    """Add a Document to a folder. The form can be called with two variables
       set in the session object: default_restricted and force_restricted.
       This will set the restricted flag in the form.
    """

    # content_type argument is probably not used anywhere.
    if id=='' and type(file) is not type('') and hasattr(file,'filename'):
        # generate id from filename and make sure, there are no spaces in the id
        id = file.filename
    if id:
        id = id[max(string.rfind(id,'/'),
                  string.rfind(id,'\\'),
                  string.rfind(id,':')
                 )+1:]
        id = id.strip()
        id = RepUtils.cleanup_id(id)
        # delete the previous file with the same id, if exists
        if hasattr(self, id):
            self.manage_delObjects(id)
        self = self.this()
        self._setObject(id, Document(id, title))
        obj = self._getOb(id)
        obj.manage_file_upload(file, content_type)
        engine = getattr(self.getPhysicalRoot(), ENGINE_ID, None)
        globally_restricted_site = getattr(engine, 'globally_restricted_site', False)
        if restricted or globally_restricted_site:
            obj.manage_restrictDocument()
        obj.reindex_object()
        if REQUEST is not None:
            security=getSecurityManager()
            if security.checkPermission('View management screens',self):
                ppath = './manage_main'
            else:
                pobj = REQUEST.PARENTS[0]
                ppath = string.join(pobj.getPhysicalPath(), '/')
            return self.messageDialog(
                            message='The file %s was successfully created!' % id,
                            action=ppath)
        else:
            return id
    else:
        if REQUEST is not None:
            return self.messageDialog(
                            message='You must specify a file!',
                            action='./manage_main')
        else:
            return ''

class Document(CatalogAware, SimpleItem, IconShow.IconShow):
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

    def __init__(self, id, title='', content_type=''):
        """ Initialize a new instance of Document
            If a document is created through FTP, self.absolute_url doesn't work.
        """
        self.id = id
        self.title = title
        self.content_type = content_type
        self.xml_schema_location = '' #needed for XML files
        self.accept_time = None
        self.data_file = FileContainer()

    ################################
    # Public methods               #
    ################################

    def __str__(self): return self.index_html()

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
        for l_w in self.getWorkitemsActiveForMe(self.REQUEST):
            l_w.addEvent('file upload', 'File: %s' % self.id)

    def index_html(self, REQUEST, RESPONSE, icon=0):
        """ Returns the contents of the file.  Also, sets the
            Content-Type HTTP header to the objects content type.
        """
        if icon:
            return self.icon_gif(REQUEST, RESPONSE)

        with self.data_file.open() as data_file_handle:
            RepUtils.http_response_with_file(
                REQUEST, RESPONSE, data_file_handle,
                self.content_type, self.data_file.size, self.data_file.mtime)

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
#   getSize = get_size

    def getFeedbacksForDocument(self):
        """ Returns the Feedback objects associated with this document """
        return [x for x in self.getParentNode().objectValues('Report Feedback') if x.document_id == self.id]

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
        return self._bytetostring(self.get_size())

    security.declareProtected('View management screens', 'blob_path')
    def blob_path(self):
        """ Return the actual path of the file on server fs as coded by zope
        inside the blob structure"""
        if getattr(self.data_file, 'fs_path', None) is None:
            return 'file not found'
        return self.data_file.fs_path

    def canHaveOnlineQA(self, upper_limit=None):
        """ Determines whether a HTTP QA can be done during Draft, based on file size
            The reason is that some on-demand QAs can take more than a minute,
            and that will time out.
        """
        if not upper_limit:
            upper_limit = 4
        if self.get_size() > int(upper_limit) * 1000 * 1024: #bytes
            return False
        return True

    # Below there are the two forms for the document operations
    # The second one contains links to the file editing (regular upload 
    # or editing with external editors e.g. XForms)
    _manage_template = PageTemplateFile('zpt/document/manage', globals())

    security.declareProtected('View', 'manage_document')
    def manage_document(self, REQUEST=None, manage_and_edit=False):
        """ """
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
        return self._manage_template(
                   manage_and_edit=manage_and_edit,
                   warnings=warning_message,
                   converters=[local_converters, remote_converters]
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
        """ Returns 1 if the file is restricted, 0 otherwise """
        if self.acquiredRolesAreUsedBy('View'):
            return 0
        return 1

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
        if REQUEST is not None:
            return self.messageDialog(
                            message="The properties of %s have been changed!" % self.id,
                            action=REQUEST['HTTP_REFERER'])

    def _setFileSchema(self, src):
        """ If it is an XML file, then extract structure information.
            The structure is the XML schema or the DTD.
        """
        if self.content_type == 'text/xml':
            self.xml_schema_location = detect_schema(src)
        else:
            self.xml_schema_location = ''

    # File upload Interface
    manage_uploadForm = PageTemplateFile('zpt/document/upload', globals())

    def manage_file_upload(self, file='', content_type='', REQUEST=None):
        """ Upload file from local directory """

        if hasattr(file, 'filename'):
            with self.data_file.open('wb') as data_file_handle:
                for chunk in RepUtils.iter_file_data(file):
                    data_file_handle.write(chunk)

        else:
            with self.data_file.open('wb') as data_file_handle:
                data_file_handle.write(file)

        with self.data_file.open('rb') as data_file_handle:
            self.content_type = self._get_content_type(
                    data_file_handle, data_file_handle.read(100),
                    self.id, content_type or self.content_type)
            data_file_handle.seek(0)
            self._setFileSchema(data_file_handle)

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

    def _get_content_type(self, file, body, id, content_type=None):
        """ Determine the mime-type """
        if hasattr(file, 'filename'):
            if file.filename[-4:] == '.gml':
                return 'text/xml'
            elif file.filename[-4:] == '.rar':
                return 'application/x-rar-compressed'
        elif id[-4:] == '.gml':
            return 'text/xml'
        headers = getattr(file, 'headers', None)
        if headers and headers.has_key('content-type'):
            content_type = headers['content-type']
        else:
            if type(body) is not type(''): body = body.data
            content_type, enc = guess_content_type(getattr(file,'filename',id),
                                                   body, content_type)
        return content_type

    def _bytetostring (self, value):
        """ Convert an int-value (file-size in bytes) to an String
            with the file-size in Byte, KB or MB
        """
        bytes = float(value)
        if bytes >= 1000:
            bytes = bytes/1024
            typ = 'KB'
            if bytes >= 1000:
                bytes = bytes/1024
                typ = 'MB'
            strg = '%4.2f' % bytes
            strg = strg[:4]
            if strg[3]=='.': strg = strg[:3]
        else:
            typ = 'Bytes'
            strg = '%4.0f' % bytes
        strg = strg+ ' ' + typ
        return strg


Globals.InitializeClass(Document)
