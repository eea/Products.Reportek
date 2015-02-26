#this is meant to be run from instance debug
#>>> from Products.Reportek.updates import blob_compression; blob_compression.update(app)

import sys
import transaction


#
#
# remove content_type from Document
# change FileContainer (Report Document, File(Blob))
# zip the report documents
#
#

from time import strftime

def update(app, outName='blob_compression.log'):
    out = sys.stderr
    if outName:
        out = open(outName, 'a')
        out.write(" --- Begin log (%s) ---\n" % strftime("%a, %d %b %Y %H:%M:%S"))
    for brain in app.Catalog(meta_type=['Report Document', 'File (Blob)']):
        try:
            ob = brain.getObject()
            # just making sure we populate the aquisition wrapper for later operation on __dict__
            repr(ob)
            data_file = ob.data_file
            # get rid of unreliable fs_path
            if getattr(data_file, 'fs_path', None) is not None:
                delattr(data_file, 'fs_path')
                transaction.commit()

            old_FileContainer = not hasattr(data_file, 'compressed')
            skipped_FileContainer = False
            if old_FileContainer:

                setattr(data_file, 'compressed', False)
                if ob.meta_type == 'Report Document':
                    setattr(data_file, '_toCompress', 'auto')
                else:
                    setattr(data_file, '_toCompress', 'no')
                setattr(data_file, 'compressed_size', None)
                data_file._p_changed = 1
            if ob.meta_type == 'Report Document':
                # should remove old content_type atribute and let the property take over
                if 'content_type' in ob.__dict__:
                    doc_ct = ob.__dict__.pop('content_type')
                    # run through the new setter property
                    ob.content_type = doc_ct
                    ob._p_changed = 1

            # new type of object that was created with no compression while solving #20539
            if (not old_FileContainer
                and ob.meta_type == 'Report Document'
                and data_file._toCompress == 'no'):
                data_file._toCompress = 'auto'
                skipped_FileContainer = True
                out.write("Reactivating new type object %s \n" % ob.absolute_url())

            # new type of objects that were set to deferred compression
            if (not old_FileContainer
                and ob.meta_type == 'Report Document'
                and data_file._toCompress == 'deferred'):
                data_file._toCompress = 'auto'
                skipped_FileContainer = True
                out.write("Setting deferred new type object to auto-compress %s \n" % ob.absolute_url())

            # keep changes so far
            transaction.commit()

            # zip the report doc
            if (old_FileContainer or skipped_FileContainer) and data_file._shouldCompress():
                path = data_file.get_fs_path()
                file_handle = data_file.open('rb')
                content = file_handle.read()
                file_handle.close()
                with data_file.open('wb', orig_size=data_file.size, preserve_mtime=True) as file_handle:
                    file_handle.write(content)
                print "Compressing %s, path: %s (%d:%d)" % (ob.absolute_url(), path, data_file.size, data_file.compressed_size)
                out.write("Compressing %s, path: %s (%d:%d)\n" % (ob.absolute_url(), path, data_file.size, data_file.compressed_size))

            transaction.commit()
        except Exception as e:
            try:
                out.write("On %s\n" % ob.absolute_url())
            except:
                pass
            out.write(repr(e) + '\n' + '(%s: %s)\n' % (str(e), str(e.args)))
            transaction.abort()
    if outName:
        out.write(" --- End log (%s) ---\n" % strftime("%a, %d %b %Y %H:%M:%S"))
        out.close()
