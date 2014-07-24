from data_source_base import DataSourceBase
import json


class ByPathDataSource(DataSourceBase):
    def get_brains(self):
        """Makes the query in catalog and returns the total number of hits and
        the hits
        """
        country_codes = [c['uri'] for c in self.context.localities_rod()
                         if c['iso'] in self.countries_filter()]
        query = {
            'meta_type': 'Report Collection',
            'roles': self.selected_role()
        }
        if country_codes:
            query['country'] = country_codes
        search_value = self.get_search_value()
        if search_value:
            query['path'] = self.get_search_value()


#       Get the total numbers of brains
        brains_number = len(self.context.Catalog(query))

        if self.obligations_filter():
            dataflow_uris = [self.obligation_uri[obl_id] for obl_id in
                             self.obligations_filter()]
            query['dataflow_uris'] = dataflow_uris

#       Added to query parameters for the specific page
        query['b_size'] = self.get_length()
        query['b_start'] = self.get_start()
        query['sort_order'] = self.get_order_direction()
        query['sort_on'] = self.get_order_column()

        brains = self.context.Catalog(query)

        return (brains_number, brains)

    def process_data(self):
        if self.context.REQUEST['REQUEST_METHOD'] == 'GET':
            results = []
            brains_number, brains = self.get_brains()

            for brain in brains:
                obj = brain.getObject()
                uris = list(obj.dataflow_uris)
                # TODO: Find out why uri is not always in dataflow_uris
                obligations = [
                    (uri, self.obligation_title.get(uri, '')) for uri in uris
                ]
                short_path = '/' + obj.absolute_url(1)
                full_path = obj.absolute_url(0)
                users = obj.users_with_local_role(self.selected_role())
                users_with_uri = [(self.user_uri(user), user) for user in users]
                results.append({
                    'path': [full_path, short_path],
                    'last_change': obj.bobobase_modification_time().Date(),
                    'obligations': obligations,
                    'users':  users_with_uri})

            data_to_return = {
                "recordsFiltered": brains_number,
                "draw": self.get_draw(),
                "data": results
            }
            return json.dumps(data_to_return)
