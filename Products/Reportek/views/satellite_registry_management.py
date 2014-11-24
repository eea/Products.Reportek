from base_admin import BaseAdmin
from Products.Reportek.constants import ENGINE_ID


class SatelliteRegistryManagement(BaseAdmin):
    """ RegistryManagement view """
    def __call__(self, *args, **kwargs):
        super(SatelliteRegistryManagement, self).__call__(*args, **kwargs)
        if self.request.method == "POST" and self.request.get("verify.btn"):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
            if not api:
                return None
            api = api.authMiddlewareApi
            candidateId = self.request.get("cid")
            newId = self.request.get("fid")
            if candidateId and newId:
                isForMatch = api.verifyCandidate(newId, candidateId)
                if isForMatch:
                    return self.request.response.redirect("matching_companies")
        return self.index()

    def get_companies(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        return api.getCompanies()

    def get_company_alldetails(self):
        return None
    #    if self.request.get('id'):
    #        id = self.request.get('id')
    #        response = requests.get("http://localhost:5000/undertaking/full-detail/%s" % id, verify=False)
    #        if response.status_code == requests.codes.ok:
    #            return json.dumps(response.json(), indent=2)
    #    return {}

    def get_company_details(self):
        if self.request.get('id'):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
            if not api:
                return None
            api = api.authMiddlewareApi
            companyId = self.request.get('id')
            return api.getCompanyDetails(companyId)


    def get_candidates(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        return api.getCandidates()
