from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo
import Products

from constants import REPORTEK_UTILITIES
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl.Permissions import view_management_screens


class ReportekUtilities(Folder):

    meta_type = 'ReportekUtilities'
    security = ClassSecurityInfo()

    def __init__(self):
        self.id = REPORTEK_UTILITIES

    security.declareProtected(view_management_screens, 'index_html')
    index_html = PageTemplateFile('zpt/admin', globals())

    def all_meta_types(self, interfaces=None):
        """
            What can you put inside me? Checks if the legal products are
            actually installed in Zope
        """
        types = ['Script (Python)', 'Folder', 'Page Template']

        return [type for type in Products.meta_types if type['name'] in types]
