from base_admin import BaseAdmin
import requests

class SatelliteRegistryManagement(BaseAdmin):
    """ RegistryManagement view """

    def get_companies(self):
        #response = requests.get("https://bdr-test.eionet.europa.eu/_cache/undertaking/list", verify=False)
        response = requests.get("http://eftimie.ro/fapi/undertaking/list")
        if response.status_code == requests.codes.ok:
            return response.json()
        return []

    def get_company_details(self):
        if self.request.get('id'):
            id = self.request.get('id')
            #response = requests.get("https://bdr-test.eionet.europa.eu/_cache/undertaking/detail/" + str(id), verify=False)
            response = requests.get("http://eftimie.ro/fapi/undertaking/list")
            if response.status_code == requests.codes.ok:
                return response.json()[int(id) - 1]
        return {}
