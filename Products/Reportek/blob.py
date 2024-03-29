import logging
import os.path
from gzip import GzipFile
from StringIO import StringIO
from time import localtime, strftime, time

import Globals
import OFS.SimpleItem as _SimpleItem
import RepUtils
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view
from App.config import getConfiguration
from gzipraw import GzipFileRaw
from persistent import Persistent
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.zip_content import ZZipFile, ZZipFileRaw
from ZODB.blob import Blob, POSKeyError
from zope.contenttype import guess_content_type
from ZPublisher.HTTPRequest import FileUpload

logger = logging.getLogger("Reportek")


class StorageError(Exception):
    pass


class FileContainer(Persistent):
    """ Wrapper around file storage on disk.

    .. py:attribute:: mtime

        modification time, similar to the value returned by
        ``os.path.getmtime``

    .. py:attribute:: size

        file size in bytes
    """

    COMP_TYPES = set([
        'text/x-unknown-content-type',
        'application/octet-stream',
        'text/xml',
        'application/rdf+xml',
        'text/plain',
        'text/html',
        'text/richtext',
        'application/vnd.ms-excel',
        'application/vnd.ms-powerpoint',
        'application/ms-excel',
        'application/ms-word',
        'application/msexcel',
        'application/msword',
        'application/msaccess',
        'application/excel',
        'application/vnd.msexcel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # noqa
        'application/x-msaccess',
        'application/rtf',
    ])

    # FIXME - shouldn't default content_type be None?
    def __init__(self, content_type='application/octet-stream',
                 compress='auto'):
        ''' Initialize an file-like object. see open for usage.
        @param compress decide whether to compress content on write.
        'auto' will decide based on COMP_TYPES
        '''
        self._blob = Blob()
        self.mtime = time()
        self.size = 0
        self.content_type = content_type
        self._toCompress = compress
        self.compressed = False
        self.compressed_size = None

    # Remove this after migration is complete
    @property
    def compressed_safe(self):
        return getattr(self, 'compressed', None)

    @compressed_safe.setter
    def compressed_safe(self, value):
        if hasattr(self, 'compressed'):
            self.compressed = value
    # Remove this after migration is complete

    def open(self, mode='rb', orig_size=0, preserve_mtime=False,
             skip_decompress=False, crc=None):
        '''
        Opens and returns a file-like object with Blob's __enter__ and __exit__
        thus 'with FileContainer.open() as x' will work ok.

        Make sure we know the content_type prior to writing so that
        we shall know whether to compress it or not...
        If content_type not set by caller, assume value already set
         (by __init__)

        @param mode string for read or write modes
        @param orig_size This is the size computed by the caller. used
         in case of compression.

        @return file-like object opened for operation 'mode'
        '''
        # Moreover, this function will act as a closure for concurent calls
        # (all orig_close vars will be bound to their respective objects)

        ok_modes = ['rb', 'wb']
        if mode not in ok_modes:
            raise ValueError("Can't open file with mode %r, only %r allowed"
                             % (mode, ok_modes))
        try:
            file_handle = self._blob.open(mode[0])
            if mode[0] == 'r':
                if self.compressed_safe and not skip_decompress:
                    file_handle = GzipFile(fileobj=file_handle)
                elif self.compressed_safe:
                    logger.debug(
                        "Serving %s compressed as client asked for AE gzip")
            elif mode[0] == 'w':
                # GzipFile will not call fileobj.close() on its own
                # because the user that called open should also handle close...
                orig_close = file_handle.close
                zip_close = None
                # The buffer is already compressed, avoid double compression
                if skip_decompress:
                    file_handle = GzipFileRaw(
                        mode='w', fileobj=file_handle, crc=crc,
                        orig_size=orig_size)
                    zip_close = file_handle.close
                    self.compressed_safe = True
                # The file could have been compressed but we excluded it
                # from COMP_TYPES. So if it shouldn't be compressed no
                # more then it shall become uncompressed on this write
                elif self._shouldCompress():
                    file_handle = GzipFile(fileobj=file_handle)
                    zip_close = file_handle.close
                    self.compressed_safe = True
                else:
                    self.compressed_safe = False

                def close_and_update_metadata():
                    if zip_close:
                        zip_close()
                    orig_close()
                    self._update_metadata(
                        file_handle.name, orig_size, preserve_mtime)
                file_handle.close = close_and_update_metadata
            return file_handle
        except (IOError, POSKeyError):
            raise StorageError

    def _update_metadata(self, fs_path, orig_size, preserve_mtime):
        # Remove this after migration is complete
        if not preserve_mtime:
            self.mtime = os.path.getmtime(fs_path)
        self.size = orig_size if orig_size else os.path.getsize(fs_path)
        if self.compressed_safe:
            self.compressed_size = os.path.getsize(fs_path)

    def _shouldCompress(self):
        # Remove this after migration is complete
        if not hasattr(self, 'compressed'):
            return False
        # Remove this after migration is complete
        if (self._toCompress == 'yes'
                or self._toCompress == 'auto'
                and self.content_type.split(';')[0] in self.COMP_TYPES):
            return True
        return False

    def openAndWrite(self, file_or_content, content_type=None):
        ''' Write given content to blob file. Also open the target blob for
            writing. The idea is to have access to the source, determine
            whether to compress or not and only then open the propper
            file handle.

        @param file_or_content source; either ZPublisher.HTTPRequest.FileUpload
         or already loaded string.
        @param content_type Set object content_type. Based on this the
         compression decision will be made
        '''

        if content_type:
            self.content_type = content_type
        self.size = self._compute_uncompressed_size(file_or_content)

        # open will detect whether to compress or not and open the propper
        # file handle
        with self.open('wb') as data_file_handle:
            if hasattr(file_or_content, 'filename'):
                for chunk in RepUtils.iter_file_data(file_or_content):
                    data_file_handle.write(chunk)
            else:
                data_file_handle.write(file_or_content)

    def get_fs_path(self):
        blob_dir = self.get_blob_dir()
        try:
            this_data_file = self._blob.open('r')
            fs_path = this_data_file.name[len(blob_dir)+1:]
            this_data_file.close()
            return os.path.join(blob_dir, fs_path)
        except Exception:
            return ''

    @classmethod
    def get_blob_dir(cls):
        config = getConfiguration()
        factory = config.dbtab.getDatabaseFactory(
            name=config.dbtab.getName('/'))
        return factory.config.storage.config.blob_dir

    UNITS = ['B', 'KB', 'MB', 'GB', 'TB']

    @classmethod
    def human_readable(cls, size, threeDigitsOnly=True):
        compact_size = size
        step = 0
        # keep the maximum number of significant digits to 3
        while compact_size >= 1000 and step < len(cls.UNITS)-1:
            compact_size /= 1024.0
            step += 1

        if step == 0:
            return "%d %s" % (compact_size, cls.UNITS[step])
        if threeDigitsOnly:
            if compact_size >= 100:
                decimals = 0
            elif compact_size >= 10:
                decimals = 1
            else:
                decimals = 2
            format_str = "%%.%df %%s" % decimals
        else:
            format_str = "%%.2f %%s"
        return format_str % (compact_size, cls.UNITS[step])


class OfsBlobFile(_SimpleItem.Item_w__name__, _SimpleItem.SimpleItem):
    """ OFS object, similar to Image, that stores its data as a Blob. """

    meta_type = "File (Blob)"
    security = ClassSecurityInfo()

    manage_options = (
        {'label': 'Edit', 'action': 'manage_main'},
        {'label': 'View', 'action': 'view'},
    ) + _SimpleItem.SimpleItem.manage_options

    def __init__(self, name=''):
        self.__name__ = name
        self.data_file = FileContainer(compress='no')

    def data_file_mtime(self):
        return strftime("%d %B %Y, %H:%M", localtime(self.data_file.mtime))

    security.declareProtected(view, 'index_html')

    def index_html(self, REQUEST, RESPONSE):
        """ download file content """
        with self.data_file.open() as data_file_handle:
            RepUtils.http_response_with_file(
                REQUEST, RESPONSE, data_file_handle,
                self.data_file.content_type,
                self.data_file.size, self.data_file.mtime)

    _view_tmpl = PageTemplateFile('zpt/blob_view.zpt', globals())

    security.declareProtected(view, 'view')

    def view(self, REQUEST, RESPONSE):
        """ View the content in a web page """
        if self.data_file.content_type.startswith('text/html'):
            with self.data_file.open() as data_file_handle:
                separator = 'HEADER-FOOTER-SPLIT'
                html = self._view_tmpl(content=separator).encode('utf-8')
                header, footer = html.split(separator)
                RESPONSE.setHeader('Content-Type', 'text/html')
                RESPONSE.write(header)
                for chunk in RepUtils.iter_file_data(data_file_handle):
                    RESPONSE.write(chunk)
                RESPONSE.write(footer)

        else:
            link = '<a href="{url}">Download</a>'.format(
                url=self.absolute_url())
            return self._view_tmpl(content=link)

    manage_main = PageTemplateFile('zpt/blob_main.zpt', globals())

    def manage_edit(self, REQUEST, RESPONSE):
        """ change properties and file content """
        form = REQUEST.form
        upload = form.get('file')
        # FIXME use FileContainer.write
        if upload:
            with self.data_file.open('wb') as stored:
                for chunk in RepUtils.iter_file_data(upload):
                    stored.write(chunk)
            self.data_file.content_type = upload.headers['Content-Type']
        if form.get('content_type'):
            self.data_file.content_type = form['content_type']
        RESPONSE.redirect(self.absolute_url() + '/manage_workspace')


Globals.InitializeClass(OfsBlobFile)


def get_content_type(file_or_content):
    """ Determine the mime-type from metadata (file name, headers)
    and eventually the actual content (Note that zope's guess_content_type does
    a poor job detecting from content - it's main detection is based on
    name/ext
    """
    name = None
    headers = None
    if hasattr(file_or_content, 'filename'):
        name = file_or_content.filename
        headers = getattr(file_or_content, 'headers', None)
        readCount = 100
        body = file_or_content.read(readCount)
        is_ZipRaw = isinstance(file_or_content, ZZipFileRaw)
        is_zip = isinstance(file_or_content, ZZipFile)
        if is_ZipRaw or is_zip:
            name = getattr(file_or_content, 'currentFilename', name)
        if (is_ZipRaw and file_or_content.allowRaw
                and (readCount < 0
                     or readCount >= ZZipFileRaw.SKIP_RAW_THRESHOLD)):
            file_or_content.rewindRaw()
        else:
            file_or_content.seek(0)
    else:
        body = file_or_content[:100]

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


def compute_uncompressed_size(file_or_content):
    if (isinstance(file_or_content, FileUpload)
            or isinstance(file_or_content, file)):
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


def add_OfsBlobFile(parent, name, data_file=None, content_type=None):
    ob = OfsBlobFile(name)
    parent[name] = ob
    if isinstance(data_file, ZZipFileRaw) and data_file.allowRaw:
        skip_compress = True
        crc = data_file.CRC
        orig_size = compute_uncompressed_size(data_file)

        with ob.data_file.open('wb', orig_size=orig_size,
                               skip_decompress=skip_compress, crc=crc,
                               preserve_mtime=False) as data_file_handle:
            if hasattr(data_file, 'read'):
                for chunk in RepUtils.iter_file_data(data_file):
                    data_file_handle.write(chunk)
            else:
                data_file_handle.write(data_file)
            if not content_type:
                data_file.seek(0)
                content_type = get_content_type(data_file)
                ob.data_file.content_type = content_type
    else:
        if data_file is not None:
            with ob.data_file.open('wb') as f:
                for chunk in RepUtils.iter_file_data(data_file):
                    f.write(chunk)
            if not content_type:
                try:
                    data_file.seek(0)
                    content_type = get_content_type(data_file)
                    ob.data_file.content_type = content_type
                except Exception:
                    pass
            else:
                ob.data_file.content_type = content_type
    return parent[name]


manage_addOfsBlobFile_html = PageTemplateFile('zpt/blob_add.zpt', globals())


def manage_addOfsBlobFile(ctx, REQUEST, RESPONSE):
    """ add a new OfsBlobFile object to `parent` """
    parent = ctx.Destination()
    data_file = REQUEST.form.get('file') or None
    data_args = ()
    if data_file is not None:
        data_args = (data_file, data_file.headers['Content-Type'])
    ob = add_OfsBlobFile(parent, REQUEST.form['name'], *data_args)
    RESPONSE.redirect(ob.absolute_url() + '/manage_workspace')
