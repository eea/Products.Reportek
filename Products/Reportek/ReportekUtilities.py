from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo
import Products

from constants import REPORTEK_UTILITIES


class ReportekUtilities(Folder):

    meta_type = 'ReportekUtilities'
    security = ClassSecurityInfo()

    def __init__(self):
        self.id = REPORTEK_UTILITIES

    def all_meta_types( self, interfaces=None ):
        """
            What can you put inside me? Checks if the legal products are
            actually installed in Zope
        """
        types = ['Script (Python)', 'Folder', 'Page Template']

        return [type for type in Products.meta_types if type['name'] in types]

    def manage_properties(self):
        """ Manage the edited values """
        if self.REQUEST['REQUEST_METHOD'] == 'GET':
            return self._manage_properties()

        return self._manage_properties(manage_tabs_message="Properties changed")
