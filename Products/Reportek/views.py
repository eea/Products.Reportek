from Products.Five import BrowserView
import string
import json


class DataSources(BrowserView):
    def __init__(self, context, request):
        """
        """
        super(DataSources, self).__init__(context, request)

    def process(self):
        if self.context.REQUEST['REQUEST_METHOD'] == 'GET':
            """ form parameters
            """
            obligation = self.context.REQUEST.get('obligation', None)
            role = self.context.REQUEST.get('role', None)
            #default for country is Romania only for test
            country = self.context.REQUEST.get('country', 'Romania')

            """datatables parameters
            """
            draw = self.context.REQUEST.get('draw')
            start = self.context.REQUEST.get('start', 0)
            length = self.context.REQUEST.get('length', 10)

            hits = self.context.Catalog(
                meta_type='Report Collection',
                getCountryName=country,
                b_size=length,
                b_start=start)

            results = []
            for hit in hits:
                obj = hit.getObject()
                results.append((obj.absolute_url(0), '/' +
                                obj.absolute_url(1),
                                obj.bobobase_modification_time().Date(),
                                obj.users_with_local_role(role),
                                list(obj.dataflow_uris)))

            data_to_return = {"recordsTotal": 90,
                "draw":draw,
                "data": results
                }
            return json.dumps(data_to_return)


class ListClients(BrowserView):
    """
    """
    def __init__(self, context, request):
        super(ListClients, self).__init__(context, request)
        self.persons = {}

    def get_results(self, role):
        def pathcompare(p1, p2):
            return cmp(p1[0], p2[0])

        hits = self.context.Catalog(meta_type='Report Collection')
        results = []
        for hit in hits:
            obj = hit.getObject()
            results.append((obj.absolute_url(0), '/' +
                            obj.absolute_url(1),
                            obj.bobobase_modification_time().Date(),
                            obj.users_with_local_role(role),
                            list(obj.dataflow_uris)))
        root_obj = self.context.restrictedTraverse(['', ])
        results.append((root_obj.absolute_url(0), '/',
                        root_obj.bobobase_modification_time().Date(),
                        root_obj.users_with_local_role(role), []))

        results.sort(pathcompare)
        return results

    def get_obl_hover(self, hit):
        obl = ""
        hover = "0"
        if len(hit[4]) > 0:
            ol = []
            for o in hit[4]:
                ol.append(self.context.dataflow_lookup(o)['TITLE'])
            obl = string.join(ol, '\n')
            hover = str(len(hit[4]))
        return (obl, hover)

    def get_members(self, hit):
        members = hit[3]
        for member in members:
            self.persons.setdefault(member, []).append(hit[1])
            yield(self.context.get_person_uri(member), member)

    def get_accounts_paths(self):
        """
        """
        pers_items = self.persons.items()
        pers_items.sort()
        for account, paths in pers_items:
            yield {'account': account,
                   'paths': paths}

    def get_person_uri(self, person):
        return 'http://www.eionet.europa.eu/directory/user?uid=%s' % person


class ListUsers(BrowserView):

    pass
