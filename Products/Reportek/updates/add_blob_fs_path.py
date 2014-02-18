#this is meant to be run from instance debug
#>>> from Products.Reportek.updates import add_blob_fs_path
#>>> add_blob_fs_path.update(app)
import transaction
from ZODB.POSException import POSKeyError

__all__ = ['update']

def do_update(app):
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
                else:
                    print 'Skipping new version/already patched object at %s' % ob.absolute_url(1)
                    print "fs_path was %s" % ob.fs_path
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
