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

def update(app, outName=None):
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

            old_FileContainer = not hasattr(data_file, 'compressed')
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

            # keep changes so far
            transaction.commit()

            # zip the report doc
            if old_FileContainer and data_file._shouldCompress():
                    path = data_file.get_fs_path()
                    file_handle = data_file.open('rb')
                    content = file_handle.read()
                    file_handle.close()
                    with data_file.open('wb', orig_size=data_file.size) as file_handle:
                        file_handle.write(content)
                    print "Compressing %s, path: %s (%d:%d)" % (ob.absolute_url(), path, data_file.size, data_file.compressed_size)
                    out.write("Compressing %s, path: %s (%d:%d)\n" % (ob.absolute_url(), path, data_file.size, data_file.compressed_size))

            transaction.commit()
        except Exception as e:
            try:
                #sys.stderr.write("On %s\n" % ob.absolute_url())
                out.write("On %s\n" % ob.absolute_url())
            except:
                pass
            #sys.stderr.write(str(e.args) + '\n')
            out.write(str(e) + '\n' + str(e.args) + '\n')
            transaction.abort()
    if outName:
        out.write(" --- End log (%s) ---" % strftime("%a, %d %b %Y %H:%M:%S"))
        out.close()
