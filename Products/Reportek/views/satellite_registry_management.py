import json
import logging
import re

import xmltodict
from base_admin import BaseAdmin
from plone.memoize.ram import global_cache

from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.RepUtils import fix_json_from_id, replace_keys

logger = logging.getLogger("Reportek")


class SatelliteRegistryManagement(BaseAdmin):
    """RegistryManagement view"""

    def __call__(self, *args, **kwargs):
        super(SatelliteRegistryManagement, self).__call__(*args, **kwargs)

        api = None
        domain = self.request.form.get("domain", "FGAS")
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
                isForMatch = api.verifyCandidate(
                    newId, userId, candidateId=candidateId, domain=domain
                )
                if isForMatch:
                    r_url = "{0}/{1}?domain={2}&id={3}&done=1".format(
                        self.context.absolute_url(),
                        "organisation_details",
                        domain,
                        newId,
                    )
                    return self.request.response.redirect(r_url)

            return self.index(error=True)

        if self.request.method == "POST" and self.request.get("add.btn"):
            fname = self.request.form.get("fname")
            lname = self.request.form.get("lname")
            email = self.request.form.get("email")

            if fname and lname and email:
                if not re.match("[\.\w]{1,}[@]\w+[.]\w+", email):
                    return self.index(
                        error="Please use a valid email address."
                    )

                response = api.addEmail(fname, lname, email)
                if response["success"]:
                    return self.request.response.redirect(
                        "{0}/{1}?done=1".format(
                            self.context.absolute_url(),
                            "notifications_settings",
                        )
                    )
                else:
                    return self.index(error=response["message"])

            return self.index(error="Please complete all fields.")

        if self.request.method == "POST" and self.request.get("del.btn"):
            email = self.request.form.get("email")

            if email:
                response = api.delEmail(email)
                if response["success"]:
                    return self.request.response.redirect(
                        "{0}/{1}?done=1".format(
                            self.context.absolute_url(),
                            "notifications_settings",
                        )
                    )
                else:
                    return self.index(error=response["message"])

            return self.index(error="Specify an email address.")

        if self.request.method == "POST" and self.request.get("orgaction") in [
            "statusupdate",
            "sync",
            "syncauditor",
        ]:
            status = self.request.get("newval")
            orgid = self.request.get("orgid")
            if orgid and status:
                if not api.updateCompanyStatus(
                    orgid, status.upper(), domain=domain
                ):
                    return self.index(error="Unable to change company status")
                else:
                    # We need to clear the company_details cache
                    global_cache.invalidate("Products.Reportek.RegistryManagement.get_company_details")  # noqa
            if self.request.get("orgaction") == "sync":
                sync_res = api.sync_company(orgid, domain=domain)
                if not sync_res:
                    return self.index(error="Unable to sync company")
                else:
                    # We need to clear the company_details cache
                    global_cache.invalidate("Products.Reportek.RegistryManagement.get_company_details")  # noqa
                    return self.index(
                        info_message=sync_res.get("message"), error=False
                    )
            if self.request.get("orgaction") == "syncauditor":
                sync_res = api.sync_auditor(orgid)
                if not sync_res:
                    return self.index(error="Unable to sync auditor")
                else:
                    # We need to clear the auditor_details cache
                    global_cache.invalidate("Products.Reportek.RegistryManagement.get_auditor_details")  # noqa
                    return self.index(
                        info_message=sync_res.get("message"), error=False
                    )
        return self.index(error=False)

    def get_api(self):
        engine = getattr(self.context, ENGINE_ID, None)
        if engine:
            return getattr(engine, "FGASRegistryAPI", None)

    def is_permitted(self, domain):
        role_mapping = {"FGAS": "ClientFG", "ODS": "ClientODS"}
        user = self.request.AUTHENTICATED_USER
        user_roles = user.getRolesInContext(self.context)
        if (
            role_mapping.get(domain, "") in user_roles
            or "Manager" in user_roles
        ):
            return True
        return False

    def get_companies(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            companies = api.get_registry_companies(
                domain=domain, detailed=True
            )
            self.request.response.setHeader("Content-Type", "application/json")
            return json.dumps(companies, indent=2)

    def get_auditors(self):
        api = self.get_api()
        if not api:
            return None
        auditors = api.get_auditors()
        self.request.response.setHeader("Content-Type", "application/json")
        return json.dumps(auditors, indent=2)

    def get_companies_api(self):
        get_params = ["id", "vat", "name", "countrycode", "OR_vat", "OR_name"]
        params = {}
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            for param in get_params:
                if self.request.get(param):
                    if param == "countrycode":
                        params[param] = self.request.get(param).upper()
                    else:
                        params[param] = self.request.get(param)

            api = self.get_api()
            self.request.response.setHeader("Content-Type", "application/json")
            return json.dumps(
                api.existsCompany(params, domain=domain), indent=2
            )

    def get_company_json(self):
        self.request.response.setHeader("Content-Type", "application/json")
        api = self.get_api()
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            details = {}
            if self.request.get("id"):
                companyId = self.request.get("id")
                details = fix_json_from_id(
                    api.get_company_details(companyId, domain=domain)
                )

            return json.dumps(details, indent=2)

    def prep_company_xml(self, company):
        cc_override = {"UK": "GB", "UK_GB": "GB", "EL": "GR"}
        keys = [
            "account",
            "active",
            "addr_place1",
            "addr_place2",
            "addr_postalcode",
            "addr_street",
            "country",
            "eori",
            "name",
            "obligation",
            "person",
            "pk",
        ]
        replace_keys(
            {
                "users": "person",
            },
            company,
        )
        address = company.get("address", {})
        company["pk"] = "-1"  # We don't have pk from european registry
        street = address.get("street", "") if address.get("street", "") else ""
        number = address.get("number", "") if address.get("number", "") else ""
        city = address.get("city", "") if address.get("city", "") else ""
        company["addr_street"] = " ".join([street, number, city])
        company["addr_postalcode"] = address.get("zipcode", "")
        company["obligation"] = {
            "@name": "Ozone depleting substances",
            "#text": company.get("domain").lower(),
        }
        country = address.get("country")

        company["country"] = {
            "@name": country.get("name"),
            "#text": cc_override.get(country.get("code"), country.get("code")),
        }
        company["eori"] = company.get("vat")
        company["account"] = company["company_id"]
        if company.get("oldcompany_account"):
            company["account"] = company["oldcompany_account"]
        company["addr_place1"] = ""
        company["addr_place2"] = ""
        company["active"] = {"VALID": True, "DISABLED": False}.get(
            company.get("status"), False
        )
        for person in company.get("person"):
            first_name = (
                person.get("first_name", "")
                if person.get("first_name", "")
                else ""
            )
            last_name = (
                person.get("last_name", "")
                if person.get("last_name", "")
                else ""
            )
            person["name"] = " ".join([first_name, last_name])
            person["phone"] = ""
            person["fax"] = ""
            del person["first_name"]
            del person["last_name"]
            del person["username"]

        for key in company.keys():
            if key not in keys:
                del company[key]
        return company

    def get_organisations_xml(self):
        """Return ODS companies in xml format"""
        self.request.response.setHeader("Content-Type", "application/xml")
        api = self.get_api()
        account_uid = self.request.get("account_uid")
        result = []
        companies = api.get_registry_companies(detailed=True, domain="ODS")
        if account_uid:
            # Search for oldcompany_account first
            company = [
                c
                for c in companies
                if str(c.get("oldcompany_account")) == account_uid
            ]
            if not company:
                # Fallback to search for new company id
                company = [
                    c
                    for c in companies
                    if str(c.get("company_id")) == account_uid
                ]
            if company:
                result.append(self.prep_company_xml(company[0]))
        else:
            result = [self.prep_company_xml(company) for company in companies]
        xml = xmltodict.unparse({"organisations": {"organisation": result}})
        return xml

    def get_company_details(self):
        if "id" not in self.request:
            return None

        api = self.get_api()
        if not api:
            return None

        companyId = self.request.get("id")
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            data = api.getCompanyDetailsById(companyId, domain=domain)
            if not data:
                return None

            data["warning"] = False
            for user in data["users"]:
                if user["username"] == user["email"]:
                    user["warning"] = True
                    data["warning"] = True
                else:
                    user["warning"] = False
            return data

    def get_auditor_details(self):
        if "id" not in self.request:
            return None

        api = self.get_api()
        if not api:
            return None

        auditor_id = self.request.get("id")
        data = api.get_auditor_details(auditor_id)
        if not data:
            return None
        return data

    def get_candidates(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            candidates = api.getCandidates(domain=domain)
            self.request.response.setHeader("Content-Type", "application/json")
            return json.dumps(candidates, indent=2)

    def get_matching_log(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            m_logs = api.getMatchingLog(domain=domain)
            self.request.response.setHeader("Content-Type", "application/json")
            for log in m_logs:
                log["locked"] = self.lockedCompany(
                    log.get("company_id"),
                    log.get("oldcompany_account"),
                    log.get("country_code"),
                    log.get("domain"),
                )
            return json.dumps(m_logs, indent=2)

    def get_datasync_log(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            sync_logs = api.getDataSyncLog(domain=domain)
            self.request.response.setHeader("Content-Type", "application/json")
            return json.dumps(sync_logs, indent=2)

    def unverify(self):
        details = {}
        if self.request.get("id"):
            api = self.get_api()
            if api:
                companyId = self.request.get("id")
                domain = self.request.form.get("domain", "FGAS")
                if self.is_permitted(domain):
                    details = api.unverifyCompany(
                        companyId,
                        self.request.AUTHENTICATED_USER.getUserName(),
                        domain=domain,
                    )
        return json.dumps(details, indent=2)

    def get_companies_excel(self):
        headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa
            "Content-Disposition": "attachment; filename=companies_list.xlsx",
        }
        for key, value in headers.iteritems():
            self.request.response.setHeader(key, value)

        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            response = api.getCompaniesExcelExport(domain=domain)
            return response.content

    def get_stocks(self):
        api = self.get_api()
        if not api:
            return None
        stocks = api.get_stocks()
        self.request.response.setHeader("Content-Type", "application/json")
        return json.dumps(stocks, indent=2)

    def stocks_json_dummy(self):
        api = self.get_api()
        if not api:
            return None
        json_dummy = api.get_stocks_dummy()
        self.request.response.setHeader("Content-Type", "application/json")
        return json.dumps(json_dummy, indent=2)

    def stock_export(self):
        api = self.get_api()
        if not api:
            return None
        page = "stocks/import"
        url = "/".join([api.baseUrl, page])
        filename = self.request.file.filename
        response = api.do_api_request(
            url,
            method="post",
            files={"file": (filename, self.request.file.read())},
            headers={"Authorization": api.token},
        )
        if response:
            return response.json()

    def get_companies_json(self):
        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            companies_original = api.get_registry_companies(
                detailed=True, domain=domain
            )
            if companies_original is None:
                companies_original = []

            companies = []
            for company in companies_original:
                company_fixed = fix_json_from_id(company)
                if domain == "ODS":
                    replace_keys({"vat": "eori_number"}, company_fixed)
                companies.append(company_fixed)

            self.request.response.setHeader("Content-Type", "application/json")
            return json.dumps(companies, indent=2)

    def get_users_excel(self):
        headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # noqa
            "Content-Disposition": "attachment; filename=user_list.xlsx",
        }
        for key, value in headers.iteritems():
            self.request.response.setHeader(key, value)

        api = self.get_api()
        if not api:
            return None
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            response = api.getUsersExcelExport(domain)
            return response.content

    def get_url(self):
        api = self.get_api()
        if not api:
            return None

        settings = api.getSettings()
        if settings:
            if self.request.form.get("domain", "") == "FGAS":
                return settings["BASE_URL_FGAS"]
            return settings["BASE_URL"]

    def get_url_ods(self):
        api = self.get_api()
        if not api:
            return None

        settings = api.getSettings()
        if settings:
            return settings["BASE_URL_ODS"]

    def get_url_fgas(self):
        api = self.get_api()
        if not api:
            return None

        settings = api.getSettings()
        if settings:
            return settings["BASE_URL_FGAS"]

    def get_emails(self):
        api = self.get_api()
        if not api:
            return None

        return api.getAllEmails()

    def lockedCompany(
        self, company_id, old_collection_id, country_code, domain
    ):
        api = self.get_api()
        if not api:
            return None
        if old_collection_id == "None":
            old_collection_id = None
        return api.lockedCompany(
            str(company_id), old_collection_id, country_code, domain
        )

    def is_company_locked(self):
        company_id = self.request.form.get("company_id")
        old_collection_id = self.request.form.get("old_collection_id")
        country_code = self.request.form.get("country_code")
        domain = self.request.form.get("domain", "FGAS")
        if self.is_permitted(domain):
            self.request.response.setHeader("Content-Type", "application/json")
            return json.dumps(
                self.lockedCompany(
                    company_id, old_collection_id, country_code, domain
                )
            )

    def lockDownCompany(
        self,
        company_id,
        old_collection_id,
        country_code,
        domain,
        user,
        came_from,
    ):
        api = self.get_api()
        if not api:
            return None

        if old_collection_id == "None":
            old_collection_id = None
        api.lockDownCompany(
            str(company_id), old_collection_id, country_code, domain, user
        )
        if came_from:
            return self.request.response.redirect(came_from)

    def unlockCompany(
        self,
        company_id,
        old_collection_id,
        country_code,
        domain,
        user,
        came_from,
    ):
        api = self.get_api()
        if not api:
            return None
        if old_collection_id == "None":
            old_collection_id = None
        api.unlockCompany(
            str(company_id), old_collection_id, country_code, domain, user
        )
        if came_from:
            return self.request.response.redirect(came_from)
