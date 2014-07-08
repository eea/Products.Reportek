from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo
import Products
import string

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

    def get_results(self, role):
        def pathcompare(p1, p2):
            return cmp(p1[0], p2[0])

        hits = self.Catalog(meta_type='Report Collection')
        results = []
        for hit in hits:
            obj = hit.getObject()
            results.append((obj.absolute_url(0), '/' +
                            obj.absolute_url(1),
                            obj.bobobase_modification_time().Date(),
                            obj.users_with_local_role(role),
                            list(obj.dataflow_uris)))
        root_obj = self.restrictedTraverse(['', ])
        results.append((root_obj.absolute_url(0), '/',
                        root_obj.bobobase_modification_time().Date(),
                        root_obj.users_with_local_role(role), []))

        results.sort(pathcompare)
        return results[0:4]

    def get_obl_hover(self, hit):
        obl = ""
        hover = "0"
        if len(hit[4]) > 0:
            ol = []
            for o in hit[4]:
                ol.append(self.dataflow_lookup(o)['TITLE'])
            obl = string.join(ol, '\n')
            hover = str(len(hit[4]))
        return (obl, hover)


    _list_clients = PageTemplateFile('zpt/admin/list_clients', globals())

    security.declareProtected(view_management_screens, 'list_clients')

    def list_clients(self):
        """ Manage the edited values """

        if self.REQUEST['REQUEST_METHOD'] == 'GET':
            return self._list_clients()
        else:
            raise NotImplementedError()
