from base_admin import BaseAdmin
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.RepUtils import fix_json_from_id
import json
import re


class SatelliteRegistryManagement(BaseAdmin):
    """ RegistryManagement view """
    def __call__(self, *args, **kwargs):
        super(SatelliteRegistryManagement, self).__call__(*args, **kwargs)

        api = None
        if self.request.method == "POST":
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
            if not api:
                return None
            api = api.authMiddlewareApi

        if self.request.method == "POST" and self.request.get("verify.btn"):
            candidateId = self.request.form.get("cid")
            newId = self.request.form.get("fid")
            userId = self.request.form.get("user")
            if candidateId and newId and userId:
                if candidateId == "none":
                    candidateId = None
                if api.verifyCandidate(newId, candidateId, userId):
                    return self.request.response.redirect('{0}/{1}?done=1'.format(
                        self.context.absolute_url(), "organisation_matching"))

            return self.index(error=True)

        if self.request.method == "POST" and self.request.get("add.btn"):
            fname = self.request.form.get("fname")
            lname = self.request.form.get("lname")
            email = self.request.form.get("email")

            if fname and lname and email:

                if not re.match('[\.\w]{1,}[@]\w+[.]\w+', email):
                    return self.index(error="Please use a valid email address.")

                response = api.addEmail(fname, lname, email)
                if response['success']:
                    return self.request.response.redirect('{0}/{1}?done=1'.format(
                            self.context.absolute_url(), "notifications_settings"))
                else:
                    return self.index(error=response['message'])

            return self.index(error="Please complete all fields.")

        if self.request.method == "POST" and self.request.get("del.btn"):
            email = self.request.form.get("email")

            if email:
                response = api.delEmail(email)
                if response['success']:
                    return self.request.response.redirect('{0}/{1}?done=1'.format(
                            self.context.absolute_url(), "notifications_settings"))
                else:
                    return self.index(error=response['message'])

            return self.index(error='Specify an email address.')

        return self.index(error=False)

    def get_companies(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        companies = api.getCompaniesAjax()
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(companies, indent=2)

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

        candidates = api.getCandidates()
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(candidates, indent=2)

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

    def unverify(self):
        details = {}
        if self.request.get('id'):
            api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
            if api:
                api = api.authMiddlewareApi
                companyId = self.request.get('id')
                details = api.unverifyCompany(companyId, self.request.AUTHENTICATED_USER.getUserName())
        return json.dumps(details, indent=2)

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
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi

        companies = api.getCompanies()
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

        settings = api.getSettings()
        return settings["AUTO_VERIFY_COMPANIES"]

    def get_url(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi

        settings = api.getSettings()
        return settings["BASE_URL"]

    def get_emails(self):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi

        return api.getAllEmails()

    def lockedCompany(self, company_id, old_collection_id, country_code, domain):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        if old_collection_id == 'None':
            old_collection_id = None
        return api.lockedCompany(str(company_id), old_collection_id,
                                 country_code, domain)

    def lockDownCompany(self, company_id, old_collection_id, country_code, domain, user, came_from):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        if old_collection_id == 'None':
            old_collection_id = None
        api.lockDownCompany(str(company_id), old_collection_id,
                                 country_code, domain, user)
        if came_from:
            return self.request.response.redirect(came_from)

    def unlockCompany(self, company_id, old_collection_id, country_code, domain, user, came_from):
        api = self.context.unrestrictedTraverse('/'+ENGINE_ID).authMiddlewareApi
        if not api:
            return None
        api = api.authMiddlewareApi
        if old_collection_id == 'None':
            old_collection_id = None
        api.unlockCompany(str(company_id), old_collection_id,
                                 country_code, domain, user)
        if came_from:
            return self.request.response.redirect(came_from)
