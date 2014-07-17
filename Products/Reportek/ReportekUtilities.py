from operator import itemgetter

from zope.interface import implementer
from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo

from interfaces import IReportekUtilities


@implementer(IReportekUtilities)
class ReportekUtilities(Folder):

    security = ClassSecurityInfo()

    def __init__(self, id, title):
        self.id = id
        self.title = title

    def all_meta_types(self):
        return ['Script (Python)', 'Folder', 'Page Template']

    def get_data(self):
        return []

        def path_compare(p1, p2):
            return cmp(p1['path_prefix'], p2['path_prefix'])

        query = {'meta_type': 'Report Collection'}
        obligations_filter = self.obligations_filter()
        if obligations_filter:
            query['dataflow_uris'] = map(self.get_obligation_uri,
                                         obligations_filter)

        role = self.selected_role()

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

    def person_uri(self, person):
        return 'http://www.eionet.europa.eu/directory/user?uid=%s' % person

    def obligations_filter(self):
        return self._get_filter('obligations')

    def countries_filter(self):
        return self._get_filter('countries')

    def selected_role(self):
        return self.REQUEST.get('role', 'Auditor')

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

