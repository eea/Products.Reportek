#this is meant to be run from instance debug
#>>> from Products.Reportek.updates import blob_analyze
#>>> blob_analyze.report(app, 'report.name')
from ZODB.POSException import POSKeyError
#from Products.Reportek.blob import FileContainer

from collections import defaultdict
import pprint

__all__ = ['update']


class RepDocStats(object):
    def __init__(self):
        self.count = 0
        self.size = 0

    def add(self, size):
        self.count += 1
        self.size += size

    UNITS = ['B', 'KB', 'MB', 'GB', 'TB']
    @classmethod
    def human_readable(cls, size):
        compact_size = size
        step = 0
        while compact_size > 1024 and step < len(cls.UNITS)-1:
            compact_size /= 1024.0
            step += 1
        return "%.2f %s" % (compact_size, cls.UNITS[step])

    def __str__(self):
        return "{count: %d, size: %d (%s)}" % (self.count, self.size,
                                            self.human_readable(self.size))

    def __repr__(self):
        return self.__str__()

def report(app, out):
    try:
        o = open(out, 'w')
    except:
        import sys
        o = sys.stdout
        print "Can't open %s for write. Using stdout instead." % out

    byDocumentType = defaultdict(RepDocStats)
    byBlobType = defaultdict(RepDocStats)
    byDocumentTypeMissingBlob = defaultdict(RepDocStats)
    #blob_dir = FileContainer.get_blob_dir()
    for brain in app.Catalog(meta_type='Report Document'):
        missing = False

        try:
            doc = brain.getObject()

            data_file = getattr(doc, 'data_file')
            try:
                file_handle = data_file._blob.open('r')
                file_handle.close()
            except POSKeyError:
                missing = True


            byDocumentType[doc.content_type].add(data_file.size)
            byBlobType[data_file.content_type].add(data_file.size)
            if missing:
                byDocumentTypeMissingBlob[doc.content_type].add(data_file.size)
        except Exception as e:
            print str(e.args)

    prn = pprint.PrettyPrinter(stream=o)
    prn.pprint('byDocumentType:')
    prn.pprint(dict(byDocumentType))
    prn.pprint('byDocumentTypeMissingBlob:')
    prn.pprint(dict(byDocumentTypeMissingBlob))
    prn.pprint('byBlobType:')
    prn.pprint(dict(byBlobType))
    o.close()

