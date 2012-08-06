import os.path
from time import time, strftime, localtime
from ZODB.blob import Blob, POSKeyError
from persistent import Persistent
import Globals
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view
import OFS.SimpleItem as _SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
import RepUtils


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

    def __init__(self):
        self._blob = Blob()
        self.mtime = time()
        self.size = 0
        self.content_type = 'application/octet-stream'

    def open(self, mode='rb'):
        ok_modes = ['rb', 'wb']
        if mode not in ok_modes:
            raise ValueError("Can't open file with mode %r, only %r allowed"
                             % (mode, ok_modes))
        try:
            file_handle = self._blob.open(mode[0])
            if mode[0] == 'w':
                orig_close = file_handle.close
                def close_and_update_metadata():
                    orig_close()
                    self._update_metadata(file_handle.name)
                file_handle.close = close_and_update_metadata
            return file_handle
        except (IOError, POSKeyError):
            raise StorageError

    def _update_metadata(self, fs_path):
        self.mtime = os.path.getmtime(fs_path)
        self.size = os.path.getsize(fs_path)


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
        self.data_file = FileContainer()

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
        if upload:
            with self.data_file.open('wb') as stored:
                for chunk in RepUtils.iter_file_data(upload):
                    stored.write(chunk)
            self.data_file.content_type = upload.headers['Content-Type']
        if form.get('content_type'):
            self.data_file.content_type = form['content_type']
        RESPONSE.redirect(self.absolute_url() + '/manage_workspace')

Globals.InitializeClass(OfsBlobFile)


def add_OfsBlobFile(parent, name, data_file=None, content_type=None):
    ob = OfsBlobFile(name)
    parent[name] = ob
    if data_file is not None:
        with ob.data_file.open('wb') as f:
            for chunk in RepUtils.iter_file_data(data_file):
                f.write(chunk)
    if content_type is not None:
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
