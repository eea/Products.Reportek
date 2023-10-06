from Products.Reportek.interfaces import IReportekContent
from DateTime import DateTime
from RepUtils import datify
from zope.interface import implements


class ReportekContent(object):
    """Base class that implements a bobobase_modification_time since
       bobobase_modification_time has been removed from Persistence.
       This should be a temporary workaround until we can replace this
       functionality
    """
    implements(IReportekContent)

    def __init__(self):
        self.modification_date = DateTime()

    def bobobase_modification_time(self):
        date = getattr(self, 'modification_date', None)
        if date is None:
            # Upgrade.
            date = DateTime(self._p_mtime)
            self.modification_date = date
        date = datify(date)
        return date