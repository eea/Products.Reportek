import json
from operator import itemgetter
from collections import defaultdict

from Products.Five import BrowserView


class DataSources(BrowserView):
    @staticmethod
    def format_row(path, url_path, last_change, obl, clients):
        """
        Format one datatable row.
        """
        return {"path": path,
                "url_path": url_path,
                "last_change": last_change,
                "obl": obl,
                "clients": clients}

    @staticmethod
    def get_obligations(obj):
        """TODO:
        """
        return "obl1 obl2"

    @staticmethod
    def get_clients(obj):
        """TODO:
        """
        return "cl1 cl2"

    @staticmethod
    def get_index_by_column(order_column):
        if order_column == 0:
            return ""
        elif order_column == 1:
            return ""
        elif order_column == 2:
            return ""
        elif order_column == 3:
            return ""
        else:
            return ""

    @staticmethod
    def get_order_dir(order_dir):
        if order_dir == "desc":
            order_dir = "reverse"
        else:
            return ""


    def get_hits(self, obligation, role, country, start,
                 length, global_search, order_column, order_dir):
        """
        Makes the query in catalog and returns the hits
        """
        if global_search:
            """TODO
            """
            pass
        else:
            hits = self.context.Catalog(
                meta_type='Report Collection',
                getCountryName=country,
                b_size=length,
                b_start=start,
                sort_on=DataSources.get_index_by_column(order_column),
                sort_order=DataSources.get_order_dir(order_dir))

        return hits

    def process_data(self):
        if self.context.REQUEST['REQUEST_METHOD'] == 'GET':
            """ form parameters
            """
            obligations = self.context.REQUEST.get('obligations', None)
            role = self.context.REQUEST.get('role', None)
            countries = self.context.REQUEST.get('countries[]')

            """datatables parameters
            """
            draw = self.context.REQUEST.get('draw')
            start = self.context.REQUEST.get('start', 0)
            length = self.context.REQUEST.get('length', 10)
            global_search = self.context.REQUEST.get('search[value]')
            order_column = self.context.REQUEST.get('order[0][column]')
            order_dir = self.context.REQUEST.get('order[0][dir]')

            results = []
            hits = self.get_hits(obligations, role, countries, start, length,
                                 global_search, order_column, order_dir)
            for hit in hits:
                obj = hit.getObject()

                results.append(
                    DataSources.format_row(
                        '/' + obj.absolute_url(1),
                        obj.absolute_url(0),
                        obj.bobobase_modification_time().Date(),
                        DataSources.get_obligations(obj),
                        DataSources.get_clients(obj)))

            data_to_return = {"recordsTotal": 90, "draw": draw, "data": results}
            return json.dumps(data_to_return)


class ListUsers(BrowserView):

    def get_rod_obligations(self):
        """ Get activities from ROD """

        data = sorted(self.context.dataflow_rod(),
                    key=itemgetter('SOURCE_TITLE'))

        obligations = defaultdict(list)
        for obl in data:
            obligations[obl['SOURCE_TITLE']].append(obl)

        return {
            'legal_instruments': sorted(obligations.keys()),
            'obligations': obligations }


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
