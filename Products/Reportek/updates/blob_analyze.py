# this is meant to be run from instance debug
# >>> from Products.Reportek.updates import blob_analyze
# >>> blob_analyze.report(app, 'report.name')
try:
    from ZODB.POSException import POSKeyError
except Exception:
    pass
# from Products.Reportek.blob import FileContainer

from collections import defaultdict, OrderedDict
import pprint
import re
import json

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

    SIZE_PATTERN = re.compile(r'(?P<size>[\d.]+) (?P<unit>[A-Z]{1,2})', re.I)

    @classmethod
    def computer_readable(cls, size_str):
        m = cls.SIZE_PATTERN.match(size_str)
        if not m:
            return None
        size = float(m.group('size'))
        unit = m.group('unit').upper()
        try:
            power = cls.UNITS.index(unit)
        except ValueError:
            return None
        return int(size * 1024**power)

    def __str__(self):
        return "{count: %d, size: %d, hrSize: %s}" % (
            self.count, self.size, self.human_readable(self.size))

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return {'count': self.count,
                'size': self.size,
                'hrSize': self.human_readable(self.size)
                }


def report(app, out):
    try:
        o = open(out, 'w')
        oj = open(out + '.json', 'w')
    except Exception:
        import sys
        o = sys.stdout
        print "Can't open %s for write. Using stdout instead." % out

    byDocumentType = defaultdict(RepDocStats)
    byBlobType = defaultdict(RepDocStats)
    byDocumentTypeMissingBlob = defaultdict(RepDocStats)
    # blob_dir = FileContainer.get_blob_dir()
    total_count = 0
    total = 0
    total_blob = 0
    total_missing = 0
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
            total_count += 1
            total += data_file.size
            byBlobType[data_file.content_type].add(data_file.size)
            total_blob += data_file.size
            if missing:
                byDocumentTypeMissingBlob[doc.content_type].add(data_file.size)
                total_missing += data_file.size
        except Exception as e:
            print str(e.args)

    def sort_by_size(t):
        return t[1]['size']

    prn = pprint.PrettyPrinter(stream=o)
    prn.pprint('byDocumentType:')
    prn.pprint(dict(byDocumentType))
    prn.pprint('total: %d: %s' %
               (total_count, RepDocStats.human_readable(total)))
    prn.pprint('byDocumentTypeMissingBlob:')
    prn.pprint(dict(byDocumentTypeMissingBlob))
    prn.pprint('total: %s' % RepDocStats.human_readable(total_missing))
    prn.pprint('byBlobType:')
    prn.pprint(dict(byBlobType))
    prn.pprint('total: %s' % RepDocStats.human_readable(total_blob))
    o.close()

    j = {'byDocumentType': OrderedDict(
            sorted(((k, v.to_dict()) for k, v in byDocumentType.iteritems()),
                   key=sort_by_size, reverse=True)),
         'byDocumentTypeMissingBlob': OrderedDict(
            sorted(((k, v.to_dict())
                    for k, v in byDocumentTypeMissingBlob.iteritems()),
                   key=sort_by_size, reverse=True)),
         'byBlobType': OrderedDict(
            sorted(((k, v.to_dict()) for k, v in byBlobType.iteritems()),
                   key=sort_by_size, reverse=True)),
         }
    json.dump(j, oj, indent=2)
    oj.close()
