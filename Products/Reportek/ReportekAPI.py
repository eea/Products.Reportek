import Products
from zope.interface import implementer
from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo

from interfaces import IReportekAPI


@implementer(IReportekAPI)
class ReportekAPI(Folder):

    security = ClassSecurityInfo()

    def __init__(self, id, title):
        self.id = id
        self.title = title

    def all_meta_types(self):
        types = ['Script (Python)']
        y = []

        for x in Products.meta_types:
            if x['name'] in types:
                y.append(x)

        return y
