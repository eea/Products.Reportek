import os.path
from time import time
from ZODB.blob import Blob, POSKeyError
from persistent import Persistent
import OFS.SimpleItem as _SimpleItem


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


class OfsBlobFile(_SimpleItem.SimpleItem, _SimpleItem.Item_w__name__):
    """ OFS object, similar to Image, that stores its data as a Blob. """

    meta_type = "File (Blob)"

    def __init__(self):
        self.data_file = FileContainer()
