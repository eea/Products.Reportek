import json
import logging
from time import time

import requests
from AccessControl import ClassSecurityInfo
from interfaces import IRegistryManagement
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from plone.memoize import ram
from requests.exceptions import HTTPError
from zope.interface import implementer

import Products

logger = logging.getLogger("Reportek")


@implementer(IRegistryManagement)
class RegistryManagement(Folder):
    security = ClassSecurityInfo()

    def __init__(self, id, title):
        self.id = id
        self.title = title

    def all_meta_types(self):
        types = ["Script (Python)", "Folder", "Page Template"]
        return [t for t in Products.meta_types if t["name"] in types]


class BaseRegistryAPI(SimpleItem):
    TIMEOUT = 120

    def __init__(self, registry_name, url, token=None):
        self.registry_name = registry_name
        self.baseUrl = url
        self.token = token

    def set_base_url(self, url, token=None):
        self.baseUrl = url
        self.token = token

    def do_api_request(
        self,
        url,
        method="get",
        data=None,
        files=None,
        cookies=None,
        headers=None,
        params=None,
        timeout=None,
        raw=None,
    ):
        api_req = requests.get
        if method == "post":
            api_req = requests.post

        if not timeout:
            timeout = self.TIMEOUT

        try:
            response = api_req(
                url,
                data=data,
                files=files,
                cookies=cookies,
                headers=headers,
                params=params,
                verify=False,
                timeout=timeout,
            )
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            logger.warning(
                """Retrieved a %s status code when contacting """
                """SatelliteRegistry's url: %s """
                % (response.status_code, url)
            )
            if raw:
                return response
            return None

        return response


class FGASRegistryAPI(BaseRegistryAPI):
    DOMAIN_TO_OBLIGATION_FOLDER = {"FGAS": "fgases", "ODS": "ods"}
    COUNTRY_TO_FOLDER = {
        "uk": "gb",
        "uk_gb": "gb",
        "el": "gr",
        "non_eu": "non-eu",
    }

    def get_registry_companies(self, domain="FGAS", detailed=False):
        page = "list-small"
        if detailed:
            page = "list"
        url_prefix = "/".join([self.baseUrl, "undertaking", domain])
        url = "/".join([url_prefix, page])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )

        if response:
            return response.json()

    def get_auditors(self):
        page = "list"
        url_prefix = "/".join([self.baseUrl, "auditors"])
        url = "/".join([url_prefix, page])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )

        if response:
            return response.json()

    def check_auditor(self, **kwargs):
        # /undertaking/[domain]/[company_id]/auditor/[auditor_uid]/check
        url = "/".join(
            [
                self.baseUrl,
                "undertaking",
                kwargs.get("domain"),
                kwargs.get("company_id"),
                "auditor",
                kwargs.get("auditor_uid"),
                "check",
            ]
        )
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def get_audit_envelopes(self, src_env):
        # /auditors/verification_envelopes/?reporting_envelope_url=/reporting/envelope/url
        url = "/".join(
            [
                self.baseUrl,
                "auditors/verification_envelopes",
            ]
        )
        params = {"reporting_envelope_url": src_env}
        response = self.do_api_request(
            url, headers={"Authorization": self.token}, params=params
        )
        if response:
            return response.json()

    def assign(self, data):
        # /undertaking/[domain]/[company_id]/auditor/[auditor_uid]/assign/
        url = "/".join(
            [
                self.baseUrl,
                "undertaking",
                data.get("domain"),
                data.get("company_id"),
                "auditor",
                data.get("auditor_uid"),
                "assign/",
            ]
        )
        p_data = {
            "email": data.get("lead_auditor"),
            "reporting_envelope_url": data.get("reporting_envelope_url"),
            "verification_envelope_url": data.get("verification_envelope_url"),
        }

        response = self.do_api_request(
            url,
            data=json.dumps(p_data),
            method="post",
            headers={
                "Authorization": self.token,
                "Content-Type": "application/json",
            },
            raw=True,
        )
        if response is None:
            raise Exception(
                "API request failed: No response received from the server."
            )

        try:
            response.raise_for_status()  # Raise HTTPError for bad responses
        except HTTPError as e:
            msg = (
                "API request failed with status code: {},"
                "reason: {}, content: {}. ({})".format(
                    response.status_code, response.reason, response.text, e
                )
            )
            raise Exception(msg)

        return response.json()

    def unassign(self, data):
        # /undertaking/[domain]/[company_id]/auditor/[auditor_uid]/unassign/
        url = "/".join(
            [
                self.baseUrl,
                "undertaking",
                data.get("domain"),
                data.get("company_id"),
                "auditor",
                data.get("auditor_uid"),
                "unassign/",
            ]
        )
        p_data = {
            "email": data.get("lead_auditor"),
            "reporting_envelope_url": data.get("reporting_envelope_url"),
            "verification_envelope_url": data.get("verification_envelope_url"),
        }

        response = self.do_api_request(
            url,
            data=json.dumps(p_data),
            method="post",
            headers={
                "Authorization": self.token,
                "Content-Type": "application/json",
            },
            raw=True,
        )
        if response is None:
            raise Exception(
                "API request failed: No response received from the server."
            )

        try:
            response.raise_for_status()  # Raise HTTPError for bad responses
        except HTTPError as e:
            msg = (
                "API request failed with status code: {},"
                "reason: {}, content: {}. ({})".format(
                    response.status_code, response.reason, response.text, e
                )
            )
            raise Exception(msg)

        return response.json()

    def get_stocks(self):
        page = "stocks"
        url = "/".join([self.baseUrl, page])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def get_stocks_dummy(self):
        page = "stocks/import"
        url = "/".join([self.baseUrl, page])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def get_company_details(self, company_id, domain="FGAS"):
        url = "/".join(
            [self.baseUrl, "undertaking", domain, company_id, "details"]
        )
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def get_auditor_details(self, auditor_id):
        url = "/".join([self.baseUrl, "auditors", auditor_id, "details"])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def get_company_details_short(self, company_id, domain="FGAS"):
        url = "/".join(
            [self.baseUrl, "undertaking", domain, company_id, "details-short"]
        )
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def get_company_licences(self, company_id, year, data, domain="FGAS"):
        if year:
            url = "/".join(
                [
                    self.baseUrl,
                    "undertaking",
                    domain,
                    company_id,
                    "licences",
                    year,
                    "aggregated",
                ]
            )
        else:
            url = "/".join(
                [
                    self.baseUrl,
                    "undertaking",
                    domain,
                    company_id,
                    "licences",
                    "aggregated",
                ]
            )
        response = self.do_api_request(
            url,
            method="post",
            data=data,
            headers={"Authorization": self.token},
            raw=True,
        )
        return response

    def get_company_stocks(self, company_id):
        url = "/".join([self.baseUrl, "stocks", company_id])
        response = self.do_api_request(
            url, method="post", headers={"Authorization": self.token}, raw=True
        )
        return response

    def get_company_paus(self, company_id, domain="ODS"):
        url = "/".join(
            [self.baseUrl, "undertaking", domain, company_id, "pau"]
        )
        response = self.do_api_request(
            url, method="post", headers={"Authorization": self.token}, raw=True
        )
        return response

    def sync_company(self, company_id, domain):
        d_map = {"FGAS": "fgases", "ODS": "ods"}
        url = "/".join([self.baseUrl, "sync", d_map.get(domain)])
        response = self.do_api_request(
            url,
            params={"id": company_id},
            headers={"Authorization": self.token},
        )
        if response:
            return response.json()

    def sync_auditor(self, auditor_id):
        url = "/".join([self.baseUrl, "sync", "auditors"])
        response = self.do_api_request(
            url,
            params={"uid": auditor_id},
            headers={"Authorization": self.token},
        )
        if response:
            return response.json()

    def getCompanyDetailsById(self, companyId, domain="FGAS"):
        details = self.get_company_details(companyId, domain=domain)
        keysToVerify = ["domain", "address", "company_id", "collection_id"]
        if details:
            if reduce(lambda i, x: i and x in details, keysToVerify, True):
                country_code = details.get("country_code")
                # If we have a NONEU_TYPE or AMBIGUOUS_TYPE company with a
                # legal representative, use the country_code from the
                # legal representative
                c_type = (
                    details.get("address", {}).get("country", {}).get("type")
                )
                rep = details.get("representative")
                previous_paths = []
                for representative in details.get("represent_history", []):
                    address = representative.get("address")
                    if address:
                        country = address.get("country")
                        if country:
                            rep_country_code = country.get("code")
                            path = self.buildCollectionPath(
                                details["domain"],
                                rep_country_code,
                                str(details["company_id"]),
                                details["collection_id"],
                            )
                            if self.unrestrictedTraverse(path, None):
                                previous_paths.append(path)
                for c_hist in details.get("country_history", []):
                    path = self.buildCollectionPath(
                        details["domain"],
                        c_hist,
                        str(details["company_id"]),
                        details["collection_id"],
                    )
                    if self.unrestrictedTraverse(path, None):
                        previous_paths.append(path)
                details["previous_paths"] = previous_paths
                if c_type in ["NONEU_TYPE", "AMBIGUOUS_TYPE"] and rep:
                    address = rep.get("address")
                    if address:
                        country = address.get("country")
                        if country:
                            country_code = country.get("code")
                path = self.buildCollectionPath(
                    details["domain"],
                    country_code,
                    str(details["company_id"]),
                    details["collection_id"],
                )
                if path:
                    details["path"] = "/{}".format(path)
                    details["licences_path"] = (
                        "/{}/aggregated_licences_listing".format(path)
                    )
                    details["stocks_path"] = "/{}/stock_listing".format(path)
                    details["paus_path"] = (
                        "/{}/process_agent_uses_listing".format(path)
                    )

            return details

    def getCollectionPaths(self, username, userdata=None):
        """Get all collection paths for a username or userdata.
        The username request is in the process of being deprecated.
        The userdata request is the preferred method which should match
        either the ecas_id or the username(e-mail) in the ecr."""
        # <ecr_host>/user/companies/v2/?username=<username>&ecas_id=<ecas_id>
        url = "{}/user/companies/v2/".format(self.baseUrl)
        headers = {"Authorization": self.token}
        if userdata:
            response = self.do_api_request(
                url, params=userdata, headers=headers
            )
        else:
            url = self.baseUrl + "/user/" + username + "/companies"
            response = self.do_api_request(url, headers=headers)
        rep_paths = {}
        paths = []
        prev_paths = []
        audit_paths = []

        def build_paths(c, c_code):
            path = None
            try:
                path = self.buildCollectionPath(
                    c["domain"],
                    c_code,
                    str(c["company_id"]),
                    c["collection_id"],
                )
                if not path:
                    raise ValueError(
                        "Cannot form path with company data: %s" % str(c)
                    )
            except Exception as e:
                logger.warning(
                    """Error in company data received from """
                    """SatelliteRegistry: %s""" % repr(e)
                )

            return path

        if response:
            data = response.json()
            if isinstance(data, list):
                data = {"reporter": data, "auditor": []}
            if data.get("auditor", []):
                for auditor in data["auditor"]:
                    ver = auditor.get("verification_envelope_url")
                    if ver:
                        if ver.startswith("/"):
                            ver = ver.lstrip("/")
                        if isinstance(ver, unicode):
                            ver = ver.encode("utf-8")
                        audit_paths.append(ver)
            else:
                authpaths = data["reporter"]
                for c in authpaths:
                    c_code = c.get("country")
                    if c.get("representative_country"):
                        c_code = c.get("representative_country")
                    path = build_paths(c, c_code)
                    if path:
                        paths.append(path)
                    for lr in c.get("represent_history", []):
                        lr_address = lr.get("address", {})
                        lr_c = lr_address.get("country")
                        if lr_c:
                            lr_c_code = lr_c.get("code")
                            prev_path = build_paths(c, lr_c_code)
                            prev_paths.append(prev_path)
                    for c_hist in c.get("country_history", []):
                        path = build_paths(c, c_hist)
                        prev_paths.append(path)

        rep_paths["paths"] = paths
        rep_paths["prev_paths"] = prev_paths
        rep_paths["audit_paths"] = audit_paths

        return rep_paths

    def existsCompany(self, params, domain="FGAS"):
        url = "/".join([self.baseUrl, "undertaking", domain, "filter"])
        response = self.do_api_request(
            url, params=params, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def verifyCandidate(
        self, companyId, userId, candidateId=None, domain="FGAS"
    ):
        # use the right pattern for Api url
        verify_endpoint = "/".join(
            ["candidate", domain, "verify-none", companyId]
        )
        if candidateId:
            verify_endpoint = "/".join(
                ["candidate", domain, "verify", companyId, candidateId]
            )

        api_url = "/".join([self.baseUrl, verify_endpoint])

        response = self.do_api_request(
            api_url,
            data={"user": userId},
            method="post",
            headers={"Authorization": self.token},
        )
        if response:
            if response.status_code == requests.codes.ok:
                data = response.json()
                if "verified" in data and data["verified"]:
                    return True
            return False

    def getCandidates(self, domain="FGAS"):
        url = "/".join([self.baseUrl, "candidate", domain, "list"])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )

        if response:
            return response.json()

        return []

    def getUsers(self, domain="FGAS"):
        url = "/".join([self.baseUrl, "user", domain, "list"])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def getMatchingLog(self, domain="FGAS"):
        url = "/".join([self.baseUrl, "log", "matching", domain])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def getDataSyncLog(self, domain="FGAS"):
        url = self.baseUrl + "/log/sync"
        url = "/".join([self.baseUrl, "log", "sync", domain])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def companyNewOldIdCheck(self, companyId="", oldCompanyId=""):
        url = "/".join(
            [
                self.baseUrl,
                "candidate/verify-matching-ids/{0}/{1}".format(
                    companyId, oldCompanyId
                ),
            ]
        )
        response = self.do_api_request(
            url, method="get", headers={"Authorization": self.token}
        )
        return response.json()

    def unverifyCompany(self, companyId, userId, domain="FGAS"):
        co = self.get_company_details(companyId, domain)
        if co:
            url = "/".join(
                [
                    self.baseUrl,
                    "candidate",
                    domain,
                    "unverify/{0}/".format(companyId),
                ]
            )
            data = {"user": userId}
            response = self.do_api_request(
                url,
                data=data,
                method="post",
                headers={"Authorization": self.token},
            )
            if response:
                unverifyResponse = response.json()
                if not unverifyResponse:
                    return None
                # unverify succeeded; proceed with unLock an email alerts
                path = self._unlockCompany(
                    str(companyId),
                    co["oldcompany_account"],
                    co["country_code"],
                    co["domain"],
                    userId,
                )
                email_sending_failed = False
                url = self.baseUrl + "/alert_lockdown/unmatch"
                data = {
                    "company_id": companyId,
                    "user": userId,
                    "oldcollection_path": path,
                }
                response = self.do_api_request(
                    url,
                    data=data,
                    method="post",
                    headers={"Authorization": self.token},
                )
                if not response:
                    email_sending_failed = True
                if email_sending_failed:
                    logger.warning(
                        "Lockdown notification emails of %s not sent" % path
                    )

                return unverifyResponse

    def updateCompanyStatus(self, company_id, status, domain="FGAS"):
        url = "/".join(
            [self.baseUrl, "undertaking", domain, company_id, "statusupdate"]
        )
        data = {"status": status}
        response = self.do_api_request(
            url,
            data=data,
            method="post",
            headers={"Authorization": self.token},
        )

        return response

    def getCompaniesExcelExport(self, domain="FGAS"):
        url = "/".join([self.baseUrl, "export", "undertaking", domain])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )

        return response

    def getUsersExcelExport(self, domain="FGAS"):
        url = "/".join([self.baseUrl, "export", "user", "list", domain])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}, timeout=120
        )

        return response

    def getSettings(self):
        url = self.baseUrl + "/settings"
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def getAllEmails(self):
        url = self.baseUrl + "/mail/list"
        response = self.do_api_request(
            url, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def addEmail(self, first_name, last_name, email):
        url = self.baseUrl + "/mail/add"
        data = {
            "mail": email,
            "first_name": first_name,
            "last_name": last_name,
        }
        response = self.do_api_request(
            url,
            data=data,
            method="post",
            headers={"Authorization": self.token},
        )
        if response:
            return response.json()

    def delEmail(self, email):
        url = self.baseUrl + "/mail/delete"
        data = {"mail": email}
        response = self.do_api_request(
            url,
            data=data,
            method="post",
            headers={"Authorization": self.token},
        )
        if response:
            return response.json()

    def lockDownCompany(
        self, company_id, old_collection_id, country_code, domain, user
    ):
        path = self.buildCollectionPath(
            domain, country_code, str(company_id), old_collection_id
        )
        bdrAuth = self.authMiddleware
        bdrAuth.lockDownCollection(path, user)
        email_sending_failed = False
        url = "/".join([self.baseUrl, "alert_lockdown", "wrong_match", domain])
        data = {"company_id": company_id, "user": user}
        response = self.do_api_request(
            url,
            data=data,
            method="post",
            headers={"Authorization": self.token},
        )
        if not response:
            email_sending_failed = True
        if email_sending_failed:
            logger.warning(
                "Lockdown notification emails of %s not sent" % path
            )

    def _unlockCompany(
        self, company_id, old_collection_id, country_code, domain, user
    ):
        path = self.buildCollectionPath(
            domain, country_code, str(company_id), old_collection_id
        )
        bdrAuth = self.authMiddleware
        bdrAuth.unlockCollection(path, user)
        return path

    def unlockCompany(
        self, company_id, old_collection_id, country_code, domain, user
    ):
        path = self._unlockCompany(
            company_id, old_collection_id, country_code, domain, user
        )

        email_sending_failed = False
        url = "/".join(
            [self.baseUrl, "alert_lockdown", "wrong_lockdown", domain]
        )
        data = {"company_id": company_id, "user": user}
        response = self.do_api_request(
            url,
            data=data,
            method="post",
            headers={"Authorization": self.token},
        )
        if not response:
            email_sending_failed = True

        if email_sending_failed:
            logger.warning(
                "Lockdown notification emails of %s not sent" % path
            )

    def lockedCompany(
        self, company_id, old_collection_id, country_code, domain
    ):
        path = self.buildCollectionPath(
            domain, country_code, str(company_id), old_collection_id
        )
        bdrAuth = self.authMiddleware
        return bdrAuth.lockedCollection(path)

    @classmethod
    def getCountryFolder(cls, country_code):
        country_code = country_code.lower()
        return cls.COUNTRY_TO_FOLDER.get(country_code, country_code)

    @classmethod
    def buildCollectionPath(
        cls, domain, country_code, company_id, old_collection_id=None
    ):
        obligation_folder = cls.DOMAIN_TO_OBLIGATION_FOLDER.get(domain)
        if not obligation_folder or not country_code:
            return None
        country_folder = cls.getCountryFolder(country_code)
        collection_folder = (
            old_collection_id if old_collection_id else company_id
        )

        return "/".join(
            [
                str(obligation_folder),
                str(country_folder),
                str(collection_folder),
            ]
        )


class BDRRegistryAPI(BaseRegistryAPI):
    def get_registry_companies(self):
        """Get the list of companies from the Registry"""
        url = self.baseUrl + "/management/companies/export/json"

        response = self.do_api_request(
            url, headers={"Authorization": self.bdr_registry_token}
        )
        if response:
            return response.json()

    @ram.cache(lambda *args, **kwargs: args[2] + str(time() // (60 * 60)))
    def get_company_details(self, company_id, domain=None):
        """Get company details from Registry"""
        url = self.baseUrl + "/management/companies/account/{0}/{1}".format(
            company_id, domain
        )
        response = self.do_api_request(
            url, headers={"Authorization": self.bdr_registry_token}
        )

        if response:
            return response.json()

    @ram.cache(lambda *args, **kwargs: args[2] + str(time() // (10 * 60)))
    def get_user_details(self, username):
        """Get details for username"""
        url = self.baseUrl + "/management/username/companies/"
        params = {"username": username}
        response = self.do_api_request(
            url,
            params=params,
            headers={"Authorization": self.bdr_registry_token},
        )
        if response and response.status_code == requests.codes.ok:
            return response.json()
        return []

    def getCollectionPaths(self, username):
        """Get collections accessible by the user"""
        usr_details = self.get_user_details(username)
        rep_paths = {"paths": [], "prev_paths": [], "audit_paths": []}
        if usr_details:
            for res in usr_details:
                if res.get("has_reporting_folder"):
                    rep_paths["paths"].append(res.get("reporting_folder"))

        return rep_paths
