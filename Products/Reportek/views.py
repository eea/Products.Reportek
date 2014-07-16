from Products.Five import BrowserView
import json


class DataSources(BrowserView):
    def process_data(self):
        def format_row(path, url_path, last_change, obl, clients):
            """
            Format one datatable row.
            """
            return {"path": path,
                    "url_path": url_path,
                    "last_change": last_change,
                    "obl": obl,
                    "clients": clients}

        if self.context.REQUEST['REQUEST_METHOD'] == 'GET':
            """ form parameters
            """
#            obligation = self.context.REQUEST.get('obligation', None)
#            role = self.context.REQUEST.get('role', None)
#            default for country is Romania only for test
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
                results.append(
                    format_row(
                        obj.absolute_url(0),
                        '/' + obj.absolute_url(1),
                        obj.bobobase_modification_time().Date(),
                        "xxx", "yyy"))

            data_to_return = {"recordsTotal": 90, "draw": draw, "data": results}
            return json.dumps(data_to_return)


class ListUsers(BrowserView):

    pass
