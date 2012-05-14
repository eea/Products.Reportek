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

## Document
## Add in changes to PrincipiaSearchSource, quickview as needed.
## This Python is meant to be modified.
##
## Here's a few potential candidates and the tools to convert:
## extension: tool - URL : content_type
## PDF: xPDF - www.foolabs.com/xpdf : application/pdf
## Word: wvWare - www.wvware.com : application/msword
## Word: Try also catdoc - forgot where I found it.
## html2txt at http://pandora.inf.uni-jena.de/p/d/noo/html2txt.html
##

__doc__ = """
      Document product module.
      The Document-Product works like the Zope File-product, but stores
      the uploaded file externally in a repository-direcory.

      $Id$
"""
__version__='$Rev$'[6:-2]

import Globals, IconShow
from __main__ import *
from AccessControl import getSecurityManager, ClassSecurityInfo
from Products.ZCatalog.CatalogAwareness import CatalogAware
from OFS.SimpleItem import SimpleItem
from zExceptions import Forbidden
from Globals import DTMLFile, MessageDialog, package_home
try: from zope.contenttype import guess_content_type # Zope 2.10 and newer
except: from zope.app.content_types import guess_content_type # Zope 2.9 and older
from webdav.common import rfc1123_date
from DateTime import DateTime
from webdav.WriteLockInterface import WriteLockInterface
from mimetools import choose_boundary
from ZPublisher import HTTPRangeSupport
import urllib, os, types, string
from os.path import join, isfile
import stat
from zope.interface import implements
from zope.app.container.interfaces import IObjectRemovedEvent, IObjectAddedEvent
from time import time
try: from cStringIO import StringIO
except: from StringIO import StringIO

# Product imports
import RepUtils
from XMLInfoParser import XMLInfoParser, SearchElementParser
from constants import CONVERTERS_ID, QAREPOSITORY_ID
from interfaces import IDocument

FLAT = 0
SYNC_ZODB = 1
SLICED = 2
REPOSITORY = SYNC_ZODB

# The suffix for PrincipiaSearchSource cache files
PSS = '+pss'

# format for the files in the repository:
# %u=user, %p=path, %n=file name, %e=file extension, %c=counter, %t=time
FILE_FORMAT = "%n%c%e"

BACKUP_ON_DELETE = 0
ALWAYS_BACKUP = 1
UNDO_POLICY = BACKUP_ON_DELETE

manage_addDocumentForm = DTMLFile('dtml/documentAdd',globals())

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
        obj.reindex_object()
        if restricted:
            obj.manage_restrictDocument()
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
    "An External Document allows indexing and conversions."

    implements(IDocument)
    __implements__ = (WriteLockInterface,)
    icon = 'misc_/Reportek/document_gif'

    # what management options are there?
    manage_options = (
        {'label':'Edit',                'action': 'manage_main'       },
        {'label':'View/Download',       'action': ''                  },
        {'label':'Upload',              'action': 'manage_uploadForm' },
        {'label':'Security',            'action': 'manage_access'     },
    )

    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()

#    security.declareProtected('Change Envelopes', 'manage_cutObjects')
#    security.declareProtected('Change Envelopes', 'manage_copyObjects')
#    security.declareProtected('Change Envelopes', 'manage_pasteObjects')
#    security.declareProtected('Change Envelopes', 'manage_renameForm')
#    security.declareProtected('Change Envelopes', 'manage_renameObject')
#    security.declareProtected('Change Envelopes', 'manage_renameObjects')

    security.declareProtected('Change permissions', 'manage_access')

    security.declareProtected('Change Envelopes', 'manage_editDocument')
    security.declareProtected('Change Envelopes', 'manage_main')
    security.declareProtected('Change Envelopes', 'manage_uploadForm')
    security.declareProtected('Change Envelopes', 'manage_file_upload')
    security.declareProtected('Change Envelopes', 'PUT')

    security.declareProtected('FTP access', 'manage_FTPstat')
    security.declareProtected('FTP access', 'manage_FTPget')
    security.declareProtected('FTP access', 'manage_FTPlist')

    security.declareProtected('View', 'index_html')
    security.declareProtected('View', 'link')
    security.declareProtected('View', 'is_broken')
    security.declareProtected('View', 'get_size')
    security.declareProtected('View', 'getContentType')
    security.declareProtected('View', 'PrincipiaSearchSource')
    security.declareProtected('View', 'physicalpath')
    security.declareProtected('View', '__str__')

    # what do people think they're adding?
    meta_type = 'Report Document'

    # location of the file-repository
    _repository = ['var','reposit']

    ################################
    # Init method                  #
    ################################

    def __init__(self, id, title='', content_type='', parent_path=None):
        """ Initialize a new instance of Document
            If a document is created through FTP, self.absolute_url doesn't work.
        """
        self.id = id
        self.title = title
        self.__version__ = __version__
        self.filename = []
        self.file_uploaded = 0
        self.content_type = content_type
        self._v_parent_path = parent_path
        self.xml_schema_location = '' #needed for XML files
        self._upload_time = time()
        self.accept_time = None

    ################################
    # Public methods               #
    ################################

    def __str__(self): return self.index_html()

    def __len__(self): return 1

    def upload_time(self):
        """ Return the upload time
        """
        return DateTime(self._upload_time)

    def get_accept_time(self):
        """ """
        if self.accept_time:
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
        """ """
        filename = self.physicalpath()
        try:
            filesize =  os.path.getsize(filename)
            filemtime = os.path.getmtime(filename)
        except: raise cant_read_exc, ("%s (%s)" %(self.id, filename))

        RESPONSE.setHeader('Last-Modified', rfc1123_date(filemtime))
        RESPONSE.setHeader('Content-Length', filesize)
        RESPONSE.setHeader('Content-Type', self.content_type)
        return ''

    def __setstate__(self,state):
        Document.inheritedAttribute('__setstate__')(self, state)
        if not hasattr(self, '_upload_time'):
            filename = self.physicalpath()
            try:
                self._upload_time = os.path.getmtime(filename)
            except: self._upload_time = 0
        if not hasattr(self, 'file_uploaded'):
            self.file_uploaded = 1
        if not hasattr(self, 'accept_time'):
            self.accept_time = None

    security.declarePublic('getMyOwner')
    def getMyOwner(self):
        """ """
        for a, b in self.get_local_roles():
            if 'Owner' in b:
                return a
        return ''

    security.declarePublic('getMyOwnerName')
    def getMyOwnerName(self):
        """ """
        return self.getLDAPUserCanonicalName(self.getLDAPUser(self.getMyOwner()))

    def logUpload(self):
        """ Log file upload and reupload in the envelope history
            The workitems' event logs are used since these are displayed
            on the envelope's history tab
        """
        for l_w in self.getWorkitemsActiveForMe(self.REQUEST):
            l_w.addEvent('file upload', 'File: %s' % self.id)

    def index_html(self, REQUEST, RESPONSE, icon=0):
        """
            Returns the contents of the file.  Also, sets the
            Content-Type HTTP header to the objects content type.
        """
        if icon:
            filename = join(package_home(globals()), self.getIconPath())
            content_type = 'image/gif'
        else:
            filename = self.physicalpath()
            content_type = self.content_type
            if not isfile(filename): self._undo()
            if not isfile(filename):
                filename = join(package_home(globals()),
                    'icons', 'broken.gif')
                content_type = 'image/gif'

        self._output_file(REQUEST, RESPONSE, filename, content_type)

    security.declarePublic('isGML')
    def isGML(self):
        """ Checks whether or not this is a GML file
        """
        return self.content_type == 'text/xml' and self.id[-4:] == '.gml'

    security.declareProtected('View', 'getQAScripts')
    def getQAScripts(self):
        """ Returns a list of QA script labels
            which can be manually run against the contained XML files
        """
        return getattr(self, QAREPOSITORY_ID).canRunQAOnFiles([self])

    def _output_file(self, REQUEST, RESPONSE, filename, content_type):
        """
            Write the necesary header information for
            (possibly) chunked output
        """
        cant_read_exc = "Can't read: "
        try:
            filesize =  os.path.getsize(filename)
            filemtime = os.path.getmtime(filename)
        except: raise cant_read_exc, ("%s (%s)" %(self.id, filename))

        # HTTP If-Modified-Since header handling.
        header=REQUEST.get_header('If-Modified-Since', None)
        if header is not None:
            header=string.split(header, ';')[0]
            # Some proxies seem to send invalid date strings for this
            # header. If the date string is not valid, we ignore it
            # rather than raise an error to be generally consistent
            # with common servers such as Apache (which can usually
            # understand the screwy date string as a lucky side effect
            # of the way they parse it).
            # This happens to be what RFC2616 tells us to do in the face of an
            # invalid date.
            try:    mod_since=long(DateTime(header).timeTime())
            except: mod_since=None
            if mod_since is not None:
                last_mod = long(filemtime)
                if last_mod > 0 and last_mod <= mod_since:
                    # Set header values since apache caching will return Content-Length
                    # of 0 in response if size is not set here
                    RESPONSE.setHeader('Last-Modified', rfc1123_date(filemtime))
                    RESPONSE.setHeader('Content-Type', content_type)
                    RESPONSE.setHeader('Content-Length', filesize)
                    RESPONSE.setHeader('Accept-Ranges', 'bytes')
                    RESPONSE.setStatus(304)
                    return ''

        # HTTP Range header handling. Typical header line (folded):
        # Range:bytes=265089-266112, 257921-265088, 119720-121023,
        #             121024-151023, 151024-181023, 181024-211023,
        #             211024-241023, 241024-257920
        range = REQUEST.get_header('Range', None)
        if_range = REQUEST.get_header('If-Range', None)
        if range is not None:
            ranges = HTTPRangeSupport.parseRange(range)

            if if_range is not None:
                # Only send ranges if the data isn't modified, otherwise send
                # the whole object. Support both ETags and Last-Modified dates!
                if len(if_range) > 1 and if_range[:2] == 'ts':
                    # ETag:
                    if if_range != self.http__etag():
                        # Modified, so send a normal response. We delete
                        # the ranges, which causes us to skip to the 200
                        # response.
                        ranges = None
                else:
                    # Date
                    date = string.split(if_range, ';')[0]
                    try: mod_since=long(DateTime(date).timeTime())
                    except: mod_since=None
                    if mod_since is not None:
                        last_mod = long(filemtime)
                        if last_mod > mod_since:
                            # Modified, so send a normal response. We delete
                            # the ranges, which causes us to skip to the 200
                            # response.
                            ranges = None

            if ranges:
                # Search for satisfiable ranges.
                satisfiable = 0
                for start, end in ranges:
                    if start < filesize:
                        satisfiable = 1
                        break

                if not satisfiable:
                    RESPONSE.setHeader('Content-Range',
                        'bytes */%d' % filesize)
                    RESPONSE.setHeader('Accept-Ranges', 'bytes')
                    RESPONSE.setHeader('Last-Modified',
                        rfc1123_date(filemtime))
                    RESPONSE.setHeader('Content-Type', content_type)
                    RESPONSE.setHeader('Content-Length', filesize)
                    RESPONSE.setStatus(416)
                    return ''

                # Can we optimize?
                #ranges = HTTPRangeSupport.optimizeRanges(ranges, filesize)

                if len(ranges) == 1:
                    # Easy case, set extra header and return partial set.
                    start, end = ranges[0]
                    size = end - start

                    RESPONSE.setHeader('Last-Modified',
                        rfc1123_date(filemtime))
                    RESPONSE.setHeader('Content-Type', content_type)
                    RESPONSE.setHeader('Content-Length', size)
                    RESPONSE.setHeader('Accept-Ranges', 'bytes')
                    RESPONSE.setHeader('Content-Range',
                        'bytes %d-%d/%d' % (start, end - 1, filesize))
                    RESPONSE.setStatus(206) # Partial content

                    fd = open(filename,'rb')
                    self._writesegment(fd, RESPONSE,start,size)
                    fd.close()
                    return ''

                else:
                    # Ignore multi-part ranges for now, pretend we don't know
                    # about ranges at all.
                    # When we get here, ranges have been optimized, so they are
                    # in order, non-overlapping, and start and end values are
                    # positive integers.
                    boundary = choose_boundary()

                    # Calculate the content length
                    size = (8 + len(boundary) + # End marker length
                        len(ranges) * (         # Constant lenght per set
                            49 + len(boundary) + len(content_type) +
                            len('%d' % filesize)))
                    for start, end in ranges:
                        # Variable length per set
                        size = (size + len('%d%d' % (start, end - 1)) +
                            end - start)


                    RESPONSE.setHeader('Content-Length', size)
                    RESPONSE.setHeader('Accept-Ranges', 'bytes')
                    RESPONSE.setHeader('Last-Modified', rfc1123_date(filemtime))
                    RESPONSE.setHeader('Content-Type',
                        'multipart/byteranges; boundary=%s' % boundary)
                    RESPONSE.setStatus(206) # Partial content

                    pos = 0

                    fd = open(filename,'rb')
                    for start, end in ranges:
                        RESPONSE.write('\r\n--%s\r\n' % boundary)
                        RESPONSE.write('Content-Type: %s\r\n' % content_type)
                        RESPONSE.write(
                            'Content-Range: bytes %d-%d/%d\r\n\r\n' % (
                                start, end - 1, filesize))

                        self._writesegment(fd, RESPONSE,start,end-start)

                    RESPONSE.write('\r\n--%s--\r\n' % boundary)
                    fd.close()
                    return ''

        RESPONSE.setHeader('Last-Modified', rfc1123_date(filemtime))
        RESPONSE.setHeader('Content-Type', content_type)
        RESPONSE.setHeader('Content-Length', filesize)
        RESPONSE.setHeader('Accept-Ranges', 'bytes')

        self._copy(filename, RESPONSE)
        return ''

    def view_image_or_file(self):
        """ The default view of the contents of the File or Image. """
        raise 'Redirect', self.absolute_url()

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
        """ return an icon for the file's MIME-Type """
        filename = join(package_home(globals()),
              self.getIconPath())
        content_type = 'image/gif'
        self._output_file(REQUEST, RESPONSE, filename, content_type)

    security.declarePublic('icon_html')
    def icon_html(self):
        """ The icon embedded in html with a link to the real file """
        return '<img src="%s/icon_gif" alt="" />' % self.absolute_url()

    def is_broken(self):
        """ Check if external file exists and return true (1) or false (0) """
        fn = self.physicalpath()
        if not isfile(fn):
            self._undo()
            if not isfile(fn):
                return 1
        return 0

    def get_size(self):
        """ Returns the size of the file or image """
        if not self.file_uploaded:
            return 0
        fn = self.physicalpath()
        if not isfile(fn): self._undo()
        if isfile(fn): size = os.stat(fn)[6]
        else: size = 0
        return size

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

    def PrincipiaSearchSource(self):
        """ PrincipiaSearchSource is used by the ZCatalog, so we just
            convert data to raw text (don't bother formatting)
            Since ZCatalog can reindex everything, it will take time
            to run all those conversions, therefore we cache it.
        """

        if not self.file_uploaded:
            return ''

        filename = self.physicalpath()
        pssname = filename + PSS
        try:
            datastat = os.stat(filename)
        except:
            return '' # If there's no datafile, there's no source.

        mustregenerate = 1
        try:
            pssstat = os.stat(pssname)
            if pssstat[stat.ST_MTIME] >= datastat[stat.ST_MTIME]:
                mustregenerate = 0
        except:
            pass
        conv_list = self.unrestrictedTraverse(CONVERTERS_ID, None).displayPossibleConversions(self.content_type, self.xml_schema_location, self.id)
        if mustregenerate:
            if self.content_type[0:5] == 'text/':
                self._copy(filename, pssname,maxblocks=1)
            elif self.content_type == '' or not conv_list:
                pssfd = open(pssname,'wb')
                pssfd.close()
            else:
                c = conv_list[0]    #if are more than one converters which accept this content_type take the first one!
                if hasattr(c,'convert_url') and c.convert_url:
                    self._copy(os.popen(c.convert_url % filename),pssname,maxblocks=1)
                else:
                    pssfd = open(pssname,'wb')
                    pssfd.close()

        f = open(pssname)
        filedata = f.read()
        f.close()
        return filedata

    def physicalpath(self, filename=None):
        """ Generate the full filename, including directories from
            self._repository and self.filename
        """
        if filename == None: filename=self.filename
        path = INSTANCE_HOME
        for item in self._repository:
            path = join(path,item)
        if type(filename)==types.ListType:
            for item in filename:
                path = join(path,item)
        elif filename!='':
            path = join(path,filename)
        return path

    def canHaveOnlineQA(self, upper_limit=None):
        #determines whether a HTTP QA can be done during Draft, based on file size
        if not upper_limit:
            upper_limit = 4
        if self.get_size() > int(upper_limit) * 1000 * 1024: #bytes
            return False
        return True

    # Below there are the two forms for the document operations
    # The second one contains links to the file editing (regular upload 
    # or editing with external editors e.g. XForms)
    security.declareProtected('View', 'manage_document')
    manage_document = DTMLFile('dtml/documentManage', globals())

    security.declareProtected('View', 'flash_document')
    flash_document = DTMLFile('dtml/documentFlashView', globals())

    security.declareProtected('View', 'manage_edit_document')
    manage_edit_document = DTMLFile('dtml/documentManageAndEdit', globals())

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

    ################################
    # Protected management methods #
    ################################

    # Management Interface
    manage_main = DTMLFile('dtml/documentEdit', globals())

    def manage_editDocument(self, title='', content_type='application/octet-stream', xml_schema_location='', applyRestriction='', restricted='', REQUEST=None):
        """ Manage the edited values """
        self.content_type = content_type
        self.xml_schema_location = xml_schema_location
        if self.title!=title:
            self.title = title
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

    def _setFileSchema(self, p_content):
        """ If it is an XML file, then extract structure information
        """
        self.xml_schema_location = ''
        if self.content_type == 'text/xml':
            l_info_handler = XMLInfoParser().ParseXmlFile(p_content)
            if l_info_handler is not None:
                if l_info_handler.xsi_info:
                    #XML Schema information
                    if l_info_handler.xsi_schema_location:
                        self.xml_schema_location = l_info_handler.xsi_schema_location
                elif l_info_handler.xdi_info:
                    #DTD information
                    if l_info_handler.xdi_public_id is not None:
                        self.xml_schema_location = l_info_handler.xdi_public_id
                    elif l_info_handler.xdi_system_id is not None:
                        self.xml_schema_location = l_info_handler.xdi_system_id

    # File upload Interface
    manage_uploadForm = DTMLFile('dtml/docUpload', globals())

    def manage_file_upload(self, file='', content_type='', REQUEST=None):
        """ Upload file from local directory """
        new_fn = self._get_ufn(self.filename)
        if hasattr(file, 'filename'):
            self._copy(file, self.physicalpath(new_fn))
            try: file.seek(0)
            except: pass
            content = file.read()
            self.content_type = self._get_content_type(file, content[:100],
                                self.id, content_type or self.content_type)
            self.filename = new_fn
            self._setFileSchema(content)
        else:
            self._copy(infile=file, outfile=self.physicalpath(new_fn), isString=1)
            self.content_type = self._get_content_type(file, file[:100],
                                self.id, content_type or self.content_type)
            #self.content_type = content_type
            self.filename = new_fn
            self._setFileSchema(file)
        self.file_uploaded = 1
        self._upload_time = time()
        self.accept_time = None
        self.logUpload()
        # update ZCatalog
        self._p_changed = 1
        self.reindex_object()
        if REQUEST is not None:
            return self.messageDialog(
                            message="The file was uploaded successfully!",
                            action=REQUEST['HTTP_REFERER'])

    manage_FTPget = index_html

    def PUT(self, REQUEST, RESPONSE):
        """ Handle HTTP/FTP PUT requests """
        self.dav__init(REQUEST, RESPONSE)
        self.dav__simpleifhandler(REQUEST, RESPONSE)
        content_type = REQUEST.get_header('content-type', None)
        instream = REQUEST['BODYFILE']
        new_fn = self._get_ufn(self.filename)
        self._copy(instream, self.physicalpath(new_fn))
        try: instream.seek(0)
        except: pass
        self.file_uploaded = 1
        self.logUpload()
        try:
            self.content_type = self._get_content_type(instream,
                        instream.read(100),
                        self.id, content_type or self.content_type)
        except:
            if UNDO_POLICY==ALWAYS_BACKUP:
                os.remove(self.physicalpath(new_fn))
                self.file_uploaded = 0
        else:
            self.filename = new_fn
            self._upload_time = time()
            self.accept_time = None
        RESPONSE.setStatus(204)
        return RESPONSE

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

    def _writesegment(self, instream, outstream, start, length):
        """ Write a segment of the file. The file is already open. """
        instream.seek(start)
        blocksize = 2<<16

        if length < blocksize:
            nextsize = length
        else:
            nextsize = blocksize

        try:
            while length > 0:
                block = instream.read(nextsize)
                outstream.write(block)
                length = length - len(block)
                if length < blocksize:
                    nextsize = length
                else:
                    nextsize = blocksize
        except IOError:
            raise IOError, ("%s (%s)" %(self.id, filename))

    def _copy(self, infile, outfile, maxblocks=16384, isString=0):
        """ Read binary data from infile and write it to outfile
            infile and outfile may be strings, in which case a file with that
            name is opened, or filehandles, in which case they are accessed
            directly.
            A block is 131072 bytes. maxblocks prevents it from >2GB
            !New!
            The isString parameter is not 0, the file is not a handler, but string.
            However, it is not the name of another object to copy, but the content 
            of the file itself.
        """
        if isString:
            from cStringIO import StringIO
            instream = StringIO(infile)
            close_in = 0
        elif type(infile) is types.StringType:
            try:
                instream = open(infile, 'rb')
            except IOError:
                self._undo()
                try:
                    instream = open(infile, 'rb')
                except IOError:
                    raise IOError, ("%s (%s)" %(self.id, infile))
            close_in = 1
        else:
            instream = infile
            close_in = 0

        if type(outfile) is types.StringType:
            try:
                outstream = open(outfile, 'wb')
            except IOError:
                raise IOError, ("%s (%s)" %(self.id, outfile))
            close_out = 1
        else:
            outstream = outfile
            close_out = 0
        try:
            blocksize = 2<<16
            block = instream.read(blocksize)
            outstream.write(block)
            maxblocks = maxblocks - 1
            while len(block)==blocksize and maxblocks > 0:
                maxblocks = maxblocks - 1
                block = instream.read(blocksize)
                outstream.write(block)
        except IOError:
            raise IOError, ("%s (%s)" %(self.id, filename))
        if close_in: instream.close()
        if close_out: outstream.close()

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

    def _undo (self):
        """ restore filename after undo or copy-paste """
        if self.filename == []:
            return
        fn = self.physicalpath()
        if not isfile(fn) and isfile(fn+'.undo'):
            self._restorefile(fn)
            self.file_uploaded = 1

    def _deletefile(self, filename):
        """ Move the file to the undo file """
        if self.filename == []:
            return
        fn = self.physicalpath()
        if isfile(fn):
            try: os.rename(filename, filename + '.undo')
            except: pass
            try: os.rename(filename + PSS, filename + PSS + '.undo')
            except: pass
            self.file_uploaded = 0

    def _copyfile(self, old_fn, new_fn):
        """ Copy a file in the repository
            This actually involves copying two files """
        self._copy(old_fn, new_fn)
        if isfile(old_fn + PSS):
            try: self._copy(old_fn + PSS, new_fn + PSS)
            except: pass

    def _restorefile(self, filename):
        """ Recover the file from undo """
        try: os.rename(filename + '.undo', filename)
        except: pass
        try: os.rename(filename + '.undo' + PSS, filename + PSS)
        except: pass


    def _get_ufn(self, filename):
        """ If no unique filename has been generated, generate one
            otherwise, return the existing one.
        """
        if UNDO_POLICY==ALWAYS_BACKUP or filename==[]:
            new_fn = self._get_new_ufn()
        else:
            new_fn = filename[:]
        if filename:
            old_fn = self.physicalpath(filename)
            if UNDO_POLICY==ALWAYS_BACKUP:
                self._deletefile(old_fn)
            else:
                self._restorefile(old_fn)
        return new_fn

    def _get_new_ufn(self):
        """ Create a new unique filename """
        # We can get in the situation that the object is floating in memory
        # when the upload is taking place. In that case we don't have a
        # absolute_url, and must rely on _v_parent_path - set in __init__
        if hasattr(self,'_v_parent_path') and self._v_parent_path:
            rel_url_list = string.split(self._v_parent_path, '/')
        else:
            rel_url_list = string.split(self.absolute_url(1), '/')[:-1]
        rel_url_list = filter(None, rel_url_list)
        pos = string.rfind(self.id, '.')
        if (pos+1):
            id_name = self.id[:pos]
            id_ext = self.id[pos:]
        else:
            id_name = self.id
            id_ext = ''

        # generate directory structure
        dirs = []
        if REPOSITORY==SYNC_ZODB:
            dirs = rel_url_list
        elif REPOSITORY==SLICED:
            slice_depth = 2 # modify here, if you want a different slice depth
            slice_width = 1 # modify here, if you want a different slice width
            temp = id_name
            for i in range(slice_depth):
                if len(temp)<slice_width*(slice_depth-i):
                    dirs.append(slice_width*'_')
                else:
                    dirs.append(temp[:slice_width])
                    temp=temp[slice_width:]

        # generate file format
        # time/counter (%t)
        fileformat = FILE_FORMAT
        if string.find(fileformat, "%t")>=0:
            fileformat = string.replace(fileformat, "%t", "%c")
            counter = int(DateTime().strftime('%m%d%H%M%S'))
        else:
            counter = 0
        invalid_format_exc = "Invalid file format: "
        if string.find(fileformat, "%c")==-1:
            raise invalid_format_exc, FILE_FORMAT
        # user (%u)
        if string.find(fileformat, "%u")>=0:
            if (hasattr(self, "REQUEST") and
               self.REQUEST.has_key('AUTHENTICATED_USER')):
                user = self.REQUEST['AUTHENTICATED_USER'].name
                fileformat = string.replace(fileformat, "%u", user)
            else:
                fileformat = string.replace(fileformat, "%u", "")
        # path (%p)
        if string.find(fileformat, "%p") >= 0:
            temp = string.joinfields (rel_url_list, "_")
            fileformat = string.replace(fileformat, "%p", temp)
        # file and extension (%n and %e)
        if string.find(fileformat,"%n") >= 0 or string.find(fileformat,"%e") >= 0:
            fileformat = string.replace(fileformat, "%n", id_name)
            fileformat = string.replace(fileformat, "%e", id_ext)

        # make the directories
        path = self.physicalpath(dirs)
        if not os.path.isdir(path):
            mkdir_exc = "Can't create directory: "
            try:
                os.makedirs(path)
            except:
                raise mkdir_exc, path

        # search for unique filename
        if counter:
            fn = join(path, string.replace(fileformat, "%c", `counter`))
        else:
            fn = join(path, string.replace(fileformat, "%c", ''))
        while (isfile(fn) or isfile(fn+'.undo')):
            counter = counter+1
            fn = join(path, string.replace(fileformat, "%c", `counter`))
        if counter: fileformat = string.replace(fileformat, "%c", `counter`)
        else: fileformat = string.replace(fileformat, "%c", '')
        dirs.append(fileformat)
        return dirs

    def getXMLAttribute(self, p_element):
        """ """
        if self.content_type == 'text/xml':
            filename = self.physicalpath()
            l_handler = SearchElementParser().parse_and_search(open(filename).read(), p_element)
            return l_handler


Globals.InitializeClass(Document)

def addedDocument(ob, event):
    """ This event is triggered when a Reportek Document was added to a container.
        This is the case after a normal add and if the object is a
        result of cut-paste- or rename-operation. In the first case, the
        external files doesn't exist yet, otherwise it was renamed to .undo
        by manage_beforeDelete before and must be restored by _undo().

        A copy of the external file is created and the property 'filename' is changed.
    """
    if ob.file_uploaded == 0 and ob.filename != []:
        old_fn = ob.physicalpath()
        new_fn = ob._get_new_ufn()
        if isfile(old_fn):
            ob._copyfile(old_fn, ob.physicalpath(new_fn))
        else:
            if isfile(old_fn + '.undo'):
                ob._copyfile(old_fn + '.undo', ob.physicalpath(new_fn))
            if isfile(old_fn + PSS + '.undo'):
                ob._copyfile(old_fn + PSS + '.undo', ob.physicalpath(new_fn) + PSS)
        ob.filename = new_fn
        ob.file_uploaded = 1

def cloneDocument(ob, event):
    """ A Reportek Document was copied. """
    old_fn = ob.physicalpath()
    new_fn = ob._get_new_ufn()
    if isfile(old_fn):
        ob._copyfile(old_fn, ob.physicalpath(new_fn))
    ob.filename = new_fn
    ob.file_uploaded = 1

def removedDocument(ob, event):
    """ A Reportek Document was removed.
        If the attribute 'can_move_released' is found in a parent folder,
        and is true, then it it legal to move the envelope
    """
    if getattr(ob, 'can_move_released', False) == True:
        return
    if event.oldParent:
        if(hasattr(event.oldParent,'released') and event.oldParent.released):
            raise Forbidden, "Envelope is released"
        fn = ob.physicalpath()
        ob._deletefile(fn) # Make room for a new file
        ob.file_uploaded = 0

def movedDocument(ob, event):
    """A Reportek Document was moved."""
    if not IObjectAddedEvent.providedBy(event):
        removedDocument(ob, event)
    if not IObjectRemovedEvent.providedBy(event):
        if ob.file_uploaded == 0 and ob.filename != []:
            addedDocument(ob, event)
        elif ob.file_uploaded == 1 and ob.filename != []:
            cloneDocument(ob, event)
