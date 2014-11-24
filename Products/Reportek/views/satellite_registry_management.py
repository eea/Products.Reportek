from base_admin import BaseAdmin
from Products.Reportek.constants import ENGINE_ID
import json


class SatelliteRegistryManagement(BaseAdmin):
    """ RegistryManagement view """
    def __call__(self, *args, **kwargs):
        super(SatelliteRegistryManagement, self).__call__(*args, **kwargs)
        if self.request.method == "POST" and self.request.get("verify.btn"):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi.authMiddlewareApi
            candidateId = self.request.get("cid")
            newId = self.request.get("fid")
            if candidateId and newId:
                isForMatch = api.verifyCandidate(newId, candidateId)
                if isForMatch:
                    return self.request.response.redirect("matching_companies")
        return self.index()

    def get_companies(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi.authMiddlewareApi
        return api.getCompanies()

    def get_company_alldetails(self):
        self.request.response.setHeader('Content-Type', 'application/json')
        if self.request.get('id'):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi.authMiddlewareApi
            companyId = self.request.get('id')
            details = api.getCompanyDetails(companyId)
            return json.dumps(details, indent=2)
        return json.dumps({})

    def get_company_details(self):
        if self.request.get('id'):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi.authMiddlewareApi
            companyId = self.request.get('id')
            return api.getCompanyDetails(companyId)


    def get_candidates(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi.authMiddlewareApi
        return api.getCandidates()
