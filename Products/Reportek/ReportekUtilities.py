from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo
import Products
from zope.interface import Interface
from zope.interface import implementer

from constants import REPORTEK_UTILITIES
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl.Permissions import view_management_screens
from interfaces import IReportekUtilities


@implementer(IReportekUtilities)
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


    def get_obligation_title(self, obligation_uri):
        return self.dataflow_lookup(obligation_uri)['TITLE']


    def get_data(self, role):
        def path_compare(p1, p2):
            return cmp(p1['path_prefix'], p2['path_prefix'])

        hits = self.Catalog(meta_type='Report Collection')
        results = []
        for hit in hits:


            obj = hit.getObject()
            results.append({
                'path_prefix': obj.absolute_url(0),
                'path_suffix': '/' + obj.absolute_url(1),
                'last_change': obj.bobobase_modification_time().Date(),
                'persons': obj.users_with_local_role(role),
                'obligation_uris': list(obj.dataflow_uris)
            })
        root_obj = self.restrictedTraverse(['', ])
        results.append({
            'path_prefix': root_obj.absolute_url(0),
            'path_suffix': '/' + root_obj.absolute_url(1),
            'last_change': root_obj.bobobase_modification_time().Date(),
            'persons': root_obj.users_with_local_role(role),
            'obligation_uris': []
        })

        results.sort(path_compare)
        return results[0:4]

    def get_person_uri(self, person):
        return 'http://www.eionet.europa.eu/directory/user?uid=%s' % person

    list_reporters = PageTemplateFile('zpt/admin/list_reporters', globals())
    security.declareProtected(view_management_screens, 'list_reporters')
