from collections import defaultdict
import json

from data_source_base import DataSourceBase


class ByPersonDataSource(DataSourceBase):

    def get_brains(self):
        country_codes = [c['uri'] for c in self.context.localities_rod()
                         if c['iso'] in self.countries_filter()]
        query = {
            'meta_type': 'Report Collection'
        }
        if self.selected_role():
            query['roles'] = self.selected_role()
        if country_codes:
            query['country'] = country_codes
        if self.obligations_filter():
            dataflow_uris = [self.obligation_uri[obl_id] for obl_id in
                             self.obligations_filter()]
            query['dataflow_uris'] = dataflow_uris

        return self.context.Catalog(query)

    def process_data(self):
        results = []
        paths = defaultdict(list)
        brains = self.get_brains()

        for brain in brains:
            obj = brain.getObject()
            if self.selected_role():
                users = obj.users_with_local_role(self.selected_role())
            else:
                users = []
                for user in self.get_roles():
                    users.extend(obj.users_with_local_role(user))

            for user in users:
                full_path = obj.absolute_url(0)
                short_path = '/' + obj.absolute_url(1)
                paths[user].append((full_path, short_path))

        for user in paths.keys():
            results.append({
                'user': user,
                'paths': paths[user]
            })

        json_res = json.dumps({
            'draw': self.get_draw(),
            'data': results
        })

        return json_res
