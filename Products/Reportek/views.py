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

    def obligation_groups(self):
        return self.context.ReportekEngine.dataflow_table_grouped()[0]

    def obligations(self, group):
        return self.context.ReportekEngine.dataflow_table_grouped()[1][group]

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
        return self.context.dataflow_lookup(obligation_uri)['TITLE']

    def get_brains(self):
        query = {'meta_type': 'Report Collection'}
        obligations_filter = self.obligations_filter()
        if obligations_filter:
            query['dataflow_uris'] = map(self.get_obligation_uri,
                                         obligations_filter)
        if self.countries_filter():
            filtered_countries = [c['uri'] for c in self.context.localities_rod()
                                  if c['iso'] in self.countries_filter()]
            query['country'] = filtered_countries

        return self.context.Catalog(query)

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
        return self.context.REQUEST.get('role', self.get_roles()[0])

    def _get_filter(self, filter_name):
        req_filter = self.context.REQUEST.get(filter_name, [])
        if not isinstance(req_filter, list):
            req_filter = [req_filter]
        return req_filter

    def by_person_url(self):
        base_url = 'list_users_by_person'
        if self.context.REQUEST.QUERY_STRING:
            return base_url + '?' + self.context.REQUEST.QUERY_STRING
        else:
            return base_url

    def by_path_url(self):
        base_url = 'list_users'
        if self.context.REQUEST.QUERY_STRING:
            return base_url + '?' + self.context.REQUEST.QUERY_STRING
        else:
            return base_url

    def get_roles(self):
        roles = list(self.context.valid_roles())
        filter(roles.remove,
                ['Authenticated', 'Anonymous', 'Manager', 'Owner'])
        return sorted(roles)
