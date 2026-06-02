from zope.interface import implementer

from Products.Reportek.interfaces import IReportekContent
from Products.Reportek.modification_date import (
    get_reportek_modification_date,
    mark_modified,
    set_reportek_modification_date,
)


@implementer(IReportekContent)
class ReportekContent(object):
    """Base class that implements a bobobase_modification_time since
    bobobase_modification_time has been removed from Persistence.
    This should be a temporary workaround until we can replace this
    functionality
    """

    def __init__(self):
        set_reportek_modification_date(self)

    def bobobase_modification_time(self):
        return get_reportek_modification_date(self)

    def notifyModified(self):
        mark_modified(self, cascade=True, reindex=True)
