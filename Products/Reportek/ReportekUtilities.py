from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo
import Products
from zope.interface import implementer

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl.Permissions import view_management_screens
from interfaces import IReportekUtilities


@implementer(IReportekUtilities)
class ReportekUtilities(Folder):

    security = ClassSecurityInfo()

    def __init__(self, id, title):
        self.id = id
        self.title = title

    security.declareProtected(view_management_screens, 'search')
    search = PageTemplateFile('zpt/utilities/search', globals())

    security.declareProtected(view_management_screens, 'search_by_person')
    search_by_person = PageTemplateFile('zpt/utilities/search_by_person', globals())

    def all_meta_types(self):
        types = ['Script (Python)', 'Folder', 'Page Template']
        return [ t for t in Products.meta_types if t['name'] in types ]

    def obligation_groups(self):
        return self.ReportekEngine.dataflow_table_grouped()[0]

    def obligations(self, group):
        return self.ReportekEngine.dataflow_table_grouped()[1][group]

    def obligation_src_title(self, obligation):
        return obligation['SOURCE_TITLE']

    def is_terminated(self, obligation):
        return obligation.get('terminated', '0') == '1'

    def is_selected(self, obligation):
        return obligation['uri'] in map(self.get_obligation_uri,
                                        self.obligations_filter())

    def source_title_prefix(self, obligation):
        return ' '.join(obligation['SOURCE_TITLE'].split()[0:2])

    def shortened_obligation_title(self, obligation, max_len=80):
        title = obligation['TITLE']
        if len(title) <= max_len:
            return title

        return "%s..." % title[:max_len-3]

    def obligation_id(self, obligation_uri):
        return obligation_uri[obligation_uri.rfind('/')+1:]

    def get_obligation_uri(self, obligation_id):
        return 'http://rod.eionet.europa.eu/obligations/%s' % obligation_id

    def obligation_title(self, obligation_uri):
        return self.dataflow_lookup(obligation_uri)['TITLE']

    def get_brains(self):
        query = {'meta_type': 'Report Collection'}
        obligations_filter = self.obligations_filter()
        if obligations_filter:
            query['dataflow_uris'] = map(self.get_obligation_uri,
                                         obligations_filter)
        if self.countries_filter():
            filtered_countries = [c['uri'] for c in self.localities_rod()
                                  if c['iso'] in self.countries_filter()]
            query['country'] = filtered_countries

        return self.Catalog(query)

    def get_data(self):
        def path_compare(p1, p2):
            return cmp(p1['path_prefix'], p2['path_prefix'])

        role = self.selected_role()
        brains = self.get_brains()
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

    def get_data_by_person(self):
        brains = self.get_brains()

        role = self.selected_role()
        results = {}
        for brain in brains:
            obj = brain.getObject()
            persons = obj.users_with_local_role(role)
            for person in persons:
                paths = results.get(person, [])
                paths.append(obj.absolute_url(1))
                results[person] = paths

        return results

    def has_common_elements(self, l1, l2):
        return bool(set(l1) & set(l2))

    def person_uri(self, person):
        return 'http://www.eionet.europa.eu/directory/user?uid=%s' % person

    def obligations_filter(self):
        return self._get_filter('obligations')

    def countries_filter(self):
        return self._get_filter('countries')

    def selected_role(self):
        return self.REQUEST.get('role', self.get_roles()[0])

    def _get_filter(self, filter_name):
        req_filter = self.REQUEST.get(filter_name, [])
        if not isinstance(req_filter, list):
            req_filter = [req_filter]
        return req_filter

    def get_roles(self):
        roles = list(self.valid_roles())
        filter(roles.remove,
                ['Authenticated', 'Anonymous', 'Manager', 'Owner'])
        return sorted(roles)

