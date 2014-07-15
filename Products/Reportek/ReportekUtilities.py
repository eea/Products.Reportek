from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo
import Products
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

    search = PageTemplateFile('zpt/admin/search', globals())
    security.declareProtected(view_management_screens, 'search')

    def all_meta_types(self, interfaces=None):
        """
            What can you put inside me? Checks if the legal products are
            actually installed in Zope
        """
        types = ['Script (Python)', 'Folder', 'Page Template']

        return [type for type in Products.meta_types if type['name'] in types]

    def obligation_groups(self):
        return self.ReportekEngine.dataflow_table_grouped()[0]

    def obligations(self, group):
        return self.ReportekEngine.dataflow_table_grouped()[1][group]

    def obligation_src_title(self, obligation):
        return obligation['SOURCE_TITLE']

    def is_terminated(self, obligation):
        return obligation.get('terminated', '0') == '1'

    def is_selected(self, obligation):
        return obligation['uri'] in self.get_obligations_filter()

    def source_title_prefix(self, obligation):
        return ' '.join(obligation['SOURCE_TITLE'].split()[0:2])

    def shortened_obligation_title(self, obligation, max_len=80):
        title = obligation['TITLE']
        if len(title) <= max_len:
            return title

        return "%s..." % title[:max_len-3]

    def get_obligation_title(self, obligation_uri):
        return self.dataflow_lookup(obligation_uri)['TITLE']

    def get_data(self, role):
        def path_compare(p1, p2):
            return cmp(p1['path_prefix'], p2['path_prefix'])

        query = {'meta_type': 'Report Collection'}
        obligations_filter = self.get_obligations_filter()
        if obligations_filter:
            query['dataflow_uris'] = obligations_filter

        brains = self.Catalog(query)
        results = []
        for brain in brains:
            obj = brain.getObject()

            results.append({
                'path_prefix': obj.absolute_url(0),
                'path_suffix': '/' + obj.absolute_url(1),
                'last_change': obj.bobobase_modification_time().Date(),
                'persons': obj.users_with_local_role(role),
                'obligation_uris': list(obj.dataflow_uris)
            })

        results.sort(path_compare)
        return results

    def has_common_elements(self, l1, l2):
        return bool(set(l1) & set(l2))

    def get_person_uri(self, person):
        return 'http://www.eionet.europa.eu/directory/user?uid=%s' % person

    def get_obligations_filter(self):
        obligations_filter = self.REQUEST.get('obligations', [])
        if not isinstance(obligations_filter, list):
            obligations_filter = [obligations_filter]
        return obligations_filter

