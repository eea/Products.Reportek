# this is meant to be run from instance debug
# >>> from Products.Reportek.updates import blob_size_correction
# >>> blob_size_correction.update(app)

import transaction


def update(app):
    for brain in app.Catalog(meta_type=['Report Document', 'File (Blob)']):
        try:
            ob = brain.getObject()
            # just making sure we populate the aquisition wrapper for
            # later operation on __dict__
            repr(ob)
            data_file = ob.data_file

            old_FileContainer = not hasattr(data_file, 'compressed')
            if (not old_FileContainer and data_file.compressed
                    and data_file.size == data_file.compressed_size):
                with data_file.open() as df:
                    data_file.size = len(df.read())

                print("On %s" % ob.absolute_url())
                print "Correcting size %d to %d" % (data_file.compressed_size,
                                                    data_file.size)
                transaction.commit()
        except Exception as e:
            try:
                print("On %s" % ob.absolute_url())
            except Exception:
                pass
            print(repr(e) + '\n' + '(%s: %s)' % (str(e), str(e.args)))
            transaction.abort()
