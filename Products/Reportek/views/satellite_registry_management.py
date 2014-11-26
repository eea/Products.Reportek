from base_admin import BaseAdmin
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.RepUtils import fix_json_format
import json


class SatelliteRegistryManagement(BaseAdmin):
    """ RegistryManagement view """
    def __call__(self, *args, **kwargs):
        super(SatelliteRegistryManagement, self).__call__(*args, **kwargs)
        if self.request.method == "POST" and self.request.get("verify.btn"):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
            if not api:
                return None
            api = api.authMiddlewareApi
            candidateId = self.request.form.get("cid")
            newId = self.request.form.get("fid")
            userId = self.request.form.get("user")
            if candidateId and newId and userId:
                isForMatch = api.verifyCandidate(newId, candidateId, userId)
                if isForMatch:
                    return self.request.response.redirect("organisation_matching")
        return self.index()

    def get_companies(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        return api.getCompanies()

    def get_company_alldetails(self):
        self.request.response.setHeader('Content-Type', 'application/json')
        if self.request.get('id'):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi.authMiddlewareApi
            companyId = self.request.get('id')
            details = api.getCompanyDetails(companyId)
            return json.dumps(fix_json_format(details), indent=2)
        return json.dumps({})

    def get_company_details(self):
        if self.request.get('id'):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
            if not api:
                return None
            api = api.authMiddlewareApi
            companyId = self.request.get('id')
            return api.getCompanyDetails(companyId)
        return None

    def get_candidates(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        return api.getCandidates()
