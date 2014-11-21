from base_admin import BaseAdmin
import requests
import json


class SatelliteRegistryManagement(BaseAdmin):
    """ RegistryManagement view """
    def __call__(self, *args, **kwargs):
        super(SatelliteRegistryManagement, self).__call__(*args, **kwargs)
        if self.request.method == "POST" and self.request.get("verify.btn"):
            cid = self.request.get("cid")
            fid = self.request.get("fid")
            if cid and fid:
                response = requests.get("http://localhost:5000/candidate/verify/{0}/{1}".format(fid, cid), verify=False)
                if response.status_code == requests.codes.ok:
                    return self.request.response.redirect("matching_companies")
        return self.index()

    def get_companies(self):
        response = requests.get("http://localhost:5000/undertaking/list", verify=False)
        if response.status_code == requests.codes.ok:
            return response.json()
        return []

    def get_company_alldetails(self):
        if self.request.get('id'):
            id = self.request.get('id')
            response = requests.get("http://localhost:5000/undertaking/full-detail/%s" % id, verify=False)
            if response.status_code == requests.codes.ok:
                return json.dumps(response.json(), indent=2)
        return {}

    def get_company_details(self):
        if self.request.get('id'):
            id = self.request.get('id')
            response = requests.get("http://localhost:5000/undertaking/detail/%s" % id, verify=False)
            if response.status_code == requests.codes.ok:
                return response.json()
        return {}

    def get_candidates(self):
        response = requests.get("http://localhost:5000/candidate/list", verify=False)
        if response.status_code == requests.codes.ok:
            return response.json()
        return []
