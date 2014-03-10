#this is meant to be run from instance debug
#>>> from Products.Reportek.updates import add_blob_fs_path
#>>> add_blob_fs_path.update(app)
import transaction
from ZODB.POSException import POSKeyError
from Products.Reportek.blob import FileContainer

__all__ = ['update']

def do_update(app):
    blob_dir = FileContainer.get_blob_dir()
    for brain in app.Catalog(meta_type='Report Document'):
        ob = brain.getObject()
        data_file = getattr(ob, 'data_file', None)
        if data_file is not None:
            try:
                if getattr(data_file, 'fs_path', None) is None:
                    file_handle = data_file._blob.open('r')
                    setattr(data_file, 'fs_path', file_handle.name)
                    file_handle.close()
                    print ob.absolute_url(1)
                elif data_file.fs_path.startswith('/tmp/') or data_file.fs_path is '':
                    old_path = data_file.fs_path
                    file_handle = data_file._blob.open('r')
                    data_file.fs_path = file_handle.name[len(blob_dir)+1:]
                    print "Correcting bad tmp path: %s to good path: %s" % (old_path, data_file.fs_path)
                elif data_file.fs_path.startswith('/'):
                    data_file.fs_path = data_file.fs_path[len(blob_dir)+1:]
                    print "Correcting absolute path to blob-only path %s" % data_file.fs_path
                else:
                    print "Skipping new version/already patched object with path %s" % data_file.fs_path
            except POSKeyError:
                print "No blob file for %s" % ob.absolute_url(1)

def update(app):
    trans = transaction.begin()
    try:
        do_update(app)
        trans.note('Update site %s' % app.absolute_url(1))
        trans.commit()
    except:
        trans.abort()
        raise
