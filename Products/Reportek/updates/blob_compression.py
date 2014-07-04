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

def update(app):
    for brain in app.Catalog(meta_type=['Report Document', 'File (Blob)']):
        ob = brain.getObject()
        # just making sure we populate the aquisition wrapper for later operation on __dict__
        repr(ob)

        try:
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
                    del ob.__dict__['content_type']
                    ob._p_changed = 1

            # keep changes so far
            transaction.commit()

            # zip the report doc
            if old_FileContainer and data_file._shouldCompress():
                    path = data_file.get_fs_path()
                    print "Compressing %s (%d)" % (path, data_file.size)
                    file_handle = data_file.open('rb')
                    content = file_handle.read()
                    file_handle.close()
                    with data_file.open('wb', orig_size=data_file.size) as file_handle:
                        file_handle.write(content)

            transaction.commit()
        except Exception as e:
            try:
                sys.stderr.write("On %s\n" % ob.absolute_url())
            except:
                pass
            sys.stderr.write(str(e.args) + '\n')
            transaction.abort()
