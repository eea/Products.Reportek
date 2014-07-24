from collections import defaultdict
from operator import itemgetter
from Products.Five import BrowserView


class TemplateUsersAdmin(BrowserView):
    """The view's template for users administration"""

    def get_rod_obligations(self):
        """ Get activities from ROD """
        data = sorted(self.context.dataflow_rod(),
                      key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        return {'legal_instruments': sorted(obligations.keys()),
                'obligations': obligations}

    def obligations_filter(self):
        return self._get_filter('obligations')

    def _get_filter(self, filter_name):
        req_filter = self.context.REQUEST.get(filter_name, [])
        if not isinstance(req_filter, list):
            req_filter = [req_filter]
        return req_filter

    def get_roles(self):
        roles = list(self.context.valid_roles())
        filter(roles.remove,
               ['Authenticated', 'Anonymous', 'Manager', 'Owner'])
        return sorted(roles)
