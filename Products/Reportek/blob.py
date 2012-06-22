import os.path
from time import time
from ZODB.blob import Blob, POSKeyError
from persistent import Persistent
import Globals
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view
import OFS.SimpleItem as _SimpleItem
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
    content_type = 'application/octet-stream'
    security = ClassSecurityInfo()

    def __init__(self, name=''):
        self.__name__ = name
        self.data_file = FileContainer()

    security.declareProtected(view, 'index_html')
    def index_html(self, REQUEST, RESPONSE):
        """ download file content """
        with self.data_file.open() as data_file_handle:
            RepUtils.http_response_with_file(
                REQUEST, RESPONSE, data_file_handle,
                self.content_type, self.data_file.size, self.data_file.mtime)

    def manage_edit(self, REQUEST, RESPONSE):
        """ change properties and file content """
        upload = REQUEST.form.get('file')
        if upload:
            with self.data_file.open('wb') as stored:
                for chunk in RepUtils.iter_file_data(upload):
                    stored.write(chunk)
        RESPONSE.redirect(self.absolute_url() + '/manage_workspace')

Globals.InitializeClass(OfsBlobFile)


def add_OfsBlobFile(parent, name):
    ob = OfsBlobFile(name)
    parent[name] = ob
    return parent[name]
