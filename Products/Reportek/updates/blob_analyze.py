#this is meant to be run from instance debug
#>>> from Products.Reportek.updates import blob_analyze
#>>> blob_analyze.report(app, 'report.name')
from ZODB.POSException import POSKeyError
from Products.Reportek.blob import FileContainer

from collection import defaultdict

__all__ = ['update']


class DocStats(object):
    def __init__(self):
        self.nr = 0
        self.size = 0

    def add(self, size):
        self.nr += 1
        self.size += size

def report(app, out):
    byDocumentType = defaultdict(DocStats)
    blob_dir = FileContainer.get_blob_dir()
    for brain in app.Catalog(meta_type='Report Document'):
        ob = brain.getObject()
        data_file = getattr(ob, 'data_file', None)

