from base_admin import BaseAdmin
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.RepUtils import fix_json_from_id
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
                if candidateId == "none":
                    candidateId = None
                isForMatch = api.verifyCandidate(newId, candidateId, userId)
                if isForMatch:
                    return self.request.response.redirect('{0}/{1}?done=1'.format(
                        self.context.absolute_url(), "organisation_matching"))
                return self.index(error=True)

        return self.index(error=False)

    def get_companies(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        return api.getCompanies()

    def get_companies_api(self):
        get_params = ['id', 'vat', 'name', 'countrycode', 'OR_vat', 'OR_name']
        params = {}

        for param in get_params:
            if self.request.get(param):
                if param == 'countrycode':
                    params[param] = self.request.get(param).upper()
                else:
                    params[param] = self.request.get(param)

        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi.authMiddlewareApi
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(api.existsCompany(params), indent=2)

    def get_company_json(self):
        self.request.response.setHeader('Content-Type', 'application/json')
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi.authMiddlewareApi

        details = {}
        if self.request.get('id'):
            companyId = self.request.get('id')
            details = api.getCompanyDetailsById(companyId)
            fix_json_from_id(details)

        return json.dumps(details, indent=2)

    def get_company_details(self):
        if self.request.get('id'):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
            if not api:
                return None
            api = api.authMiddlewareApi
            companyId = self.request.get('id')
            data = api.getCompanyDetailsById(companyId)
            data['warning'] = False
            for user in data['users']:
                if user['username'] == user['email']:
                    user['warning'] = True
                    data['warning'] = True
                else:
                    user['warning'] = False
            return data
        return None

    def get_candidates(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        return api.getCandidates()

    def get_matching_log(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        return api.getMatchingLog()

    def get_datasync_log(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        return api.getDataSyncLog()

    def get_companies_excel(self):
        headers = {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=companies_list.xlsx'
        }
        for key, value in headers.iteritems():
            self.request.response.setHeader(key, value)

        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        response = api.getCompaniesExcelExport()
        return response.content

    def get_companies_json(self):
        companies = self.get_companies()
        if companies is None:
            companies = []

        for company in companies:
            fix_json_from_id(company)

        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(companies, indent=2)

    def get_users_excel(self):
        headers = {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=user_list.xlsx'
        }
        for key, value in headers.iteritems():
            self.request.response.setHeader(key, value)

        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        response = api.getUsersExcelExport()
        return response.content

    def auto_matching(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi

        auto = api.autoMatching()
        if auto and auto.content == 'true':
            return True
        else:
            return False
