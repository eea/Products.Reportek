from collections import defaultdict
from operator import itemgetter
from Products.Five import BrowserView
import Zope2


class BaseAdmin(BrowserView):
    """ Base view for users administration """

    def get_view(self, view_name):
        """Returns the view coresponding to the view_name"""
        if self.context.REQUEST.QUERY_STRING:
            return view_name + '?' + self.context.REQUEST.QUERY_STRING
        else:
            return view_name

    def get_roles(self):
        app = Zope2.bobo_application()
        return sorted(list(app.userdefined_roles()))

    def get_rod_obligations(self):
        """ Get activities from ROD """
        data = sorted(self.context.dataflow_rod(),
                      key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        return {'legal_instruments': sorted(obligations.keys()),
                'obligations': obligations}


