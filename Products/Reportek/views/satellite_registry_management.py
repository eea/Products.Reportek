from base_admin import BaseAdmin
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.RepUtils import fix_json_from_id
from plone.memoize.ram import global_cache
import json
import re
import logging

logger = logging.getLogger("Reportek")


class SatelliteRegistryManagement(BaseAdmin):
    """ RegistryManagement view """
    def __call__(self, *args, **kwargs):
        super(SatelliteRegistryManagement, self).__call__(*args, **kwargs)

        api = None
        domain = self.request.form.get('domain', 'FGAS')
        if self.request.method == "POST":
            api = self.get_api()
            if not api:
                return None

        if self.request.method == "POST" and self.request.get("verify.btn"):
            candidateId = self.request.form.get("cid")
            newId = self.request.form.get("fid")
            userId = self.request.form.get("user")
            if candidateId and newId and userId:
                if candidateId == "none":
                    candidateId = None
                isForMatch = api.verifyCandidate(newId, userId,
                                                 candidateId=candidateId,
                                                 domain=domain)
                if isForMatch:
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

        if self.request.method == "POST" and self.request.get('orgaction') == 'statusupdate':
            status = self.request.get('newval')
            orgid = self.request.get('orgid')
            if orgid and status:
                if not api.updateCompanyStatus(orgid, status.upper(), domain=domain):
                    return self.index(error='Unable to change company status')
                else:
                    # We need to clear the company_details cache
                    global_cache.invalidate('Products.Reportek.RegistryManagement.get_company_details')
        return self.index(error=False)

    def get_api(self):
        engine = getattr(self.context, ENGINE_ID, None)
        if engine:
            return getattr(engine, 'FGASRegistryAPI', None)

    def get_companies(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get('domain', 'FGAS')
        companies = api.get_registry_companies(domain=domain)
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(companies, indent=2)

    def get_companies_api(self):
        get_params = ['id', 'vat', 'name', 'countrycode', 'OR_vat', 'OR_name']
        params = {}
        domain = self.request.form.get('domain', 'FGAS')
        for param in get_params:
            if self.request.get(param):
                if param == 'countrycode':
                    params[param] = self.request.get(param).upper()
                else:
                    params[param] = self.request.get(param)

        api = self.get_api()
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(api.existsCompany(params, domain=domain), indent=2)

    def get_company_json(self):
        self.request.response.setHeader('Content-Type', 'application/json')
        api = self.get_api()
        domain = self.request.form.get('domain', 'FGAS')
        details = {}
        if self.request.get('id'):
            companyId = self.request.get('id')
            details = fix_json_from_id(api.get_company_details(companyId,
                                                               domain=domain))

        return json.dumps(details, indent=2)

    def get_company_details(self):
        if 'id' not in self.request:
            return None

        api = self.get_api()
        if not api:
            return None

        companyId = self.request.get('id')
        domain = self.request.form.get('domain', 'FGAS')
        data = api.getCompanyDetailsById(companyId, domain=domain)
        if not data:
            return None

        data['warning'] = False
        for user in data['users']:
            if user['username'] == user['email']:
                user['warning'] = True
                data['warning'] = True
            else:
                user['warning'] = False
        return data

    def get_candidates(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get('domain', 'FGAS')
        candidates = api.getCandidates(domain=domain)
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(candidates, indent=2)

    def get_matching_log(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get('domain', 'FGAS')
        m_logs = api.getMatchingLog(domain=domain)
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(m_logs, indent=2)

    def get_datasync_log(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get('domain', 'FGAS')
        sync_logs = api.getDataSyncLog(domain=domain)
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(sync_logs, indent=2)

    def unverify(self):
        details = {}
        if self.request.get('id'):
            api = self.get_api()
            if api:
                companyId = self.request.get('id')
                domain = self.request.form.get('domain', 'FGAS')
                details = api.unverifyCompany(companyId, self.request.AUTHENTICATED_USER.getUserName(), domain=domain)
        return json.dumps(details, indent=2)

    def get_companies_excel(self):
        headers = {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=companies_list.xlsx'
        }
        for key, value in headers.iteritems():
            self.request.response.setHeader(key, value)

        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get('domain', 'FGAS')
        response = api.getCompaniesExcelExport(domain=domain)
        return response.content

    def get_companies_json(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get('domain', 'FGAS')
        companies_original = api.get_registry_companies(detailed=True,
                                                        domain=domain)
        if companies_original is None:
            companies_original = []

        companies = []
        for company in companies_original:
            companies.append(fix_json_from_id(company))

        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(companies, indent=2)

    def get_users_excel(self):
        headers = {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=user_list.xlsx'
        }
        for key, value in headers.iteritems():
            self.request.response.setHeader(key, value)

        api = self.get_api()
        if not api:
            return None
        response = api.getUsersExcelExport()
        return response.content

    def get_url(self):
        api = self.get_api()
        if not api:
            return None

        settings = api.getSettings()
        return settings["BASE_URL"]

    def get_emails(self):
        api = self.get_api()
        if not api:
            return None

        return api.getAllEmails()

    def lockedCompany(self, company_id, old_collection_id, country_code, domain):
        api = self.get_api()
        if not api:
            return None
        if old_collection_id == 'None':
            old_collection_id = None
        return api.lockedCompany(str(company_id), old_collection_id,
                                 country_code, domain)

    def is_company_locked(self):
        company_id = self.request.form.get('company_id')
        old_collection_id = self.request.form.get('old_collection_id')
        country_code = self.request.form.get('country_code')
        domain = self.request.form.get('domain', 'FGAS')
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(self.lockedCompany(company_id, old_collection_id,
                                             country_code, domain))

    def lockDownCompany(self, company_id, old_collection_id, country_code, domain, user, came_from):
        api = self.get_api()
        if not api:
            return None

        if old_collection_id == 'None':
            old_collection_id = None
        api.lockDownCompany(str(company_id), old_collection_id,
                                 country_code, domain, user)
        if came_from:
            return self.request.response.redirect(came_from)

    def unlockCompany(self, company_id, old_collection_id, country_code, domain, user, came_from):
        api = self.get_api()
        if not api:
            return None
        if old_collection_id == 'None':
            old_collection_id = None
        api.unlockCompany(str(company_id), old_collection_id,
                                 country_code, domain, user)
        if came_from:
            return self.request.response.redirect(came_from)
