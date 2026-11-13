import copy
import json
import logging
import threading
from concurrent.futures import Future
from time import time
from types import SimpleNamespace

import requests
from AccessControl import ClassSecurityInfo
from .interfaces import IRegistryManagement
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from plone.memoize import ram
from requests.exceptions import HTTPError
from zope.globalrequest import getRequest
from zope.interface import implementer

import Products
from functools import reduce

LOCKDOWN_EMAILS_NOT_SENT = "Lockdown notification emails of %s not sent"

logger = logging.getLogger("Reportek")


FAILED_LOOKUPS = "_reportek_registry_failed_lookups"
# answers that say that the registry cannot answer now, besides the 5xx
RETRY_LATER_STATUS = (408, 429)


def failed_in_this_request(key):
    """Did the lookup fail already in the current request?

    A page asks for the same lookup many times (a check for every envelope of a
    list), and a registry that is down must not be asked again for each. Only
    the current request remembers it: the next request asks the registry again.
    """
    request = getRequest()
    return request is not None and key in request.other.get(FAILED_LOOKUPS, ())


def remember_failure_in_this_request(key):
    request = getRequest()
    if request is not None:
        request.other.setdefault(FAILED_LOOKUPS, set()).add(key)


PREFETCHED = "_reportek_registry_prefetched"
# module and name of the cached function, as plone.memoize names it
USER_DETAILS = (__name__, "_get_user_details")
# the requests that wait for the answer in a thread at the same time
_prefetching = threading.BoundedSemaphore(16)


def _user_details_key(username):
    return username + str(time() // (10 * 60))


_MISSING = object()


def is_cold(function, key):
    """Does the cache of the function miss the key?

    function is the cached function as plone.memoize names it: its module and
    its name, key is what its key function gives.
    """
    holder = SimpleNamespace(__module__=function[0], __name__=function[1])
    cache = ram.store_in_cache(holder)
    return cache.get("%s.%s:%s" % (function + (key,)), _MISSING) is _MISSING


def send_request(method, url, kwargs):
    """The HTTP request alone, no persistent object is used: it may run in a thread.

    Returns the response or None when the registry cannot be contacted."""
    api_req = requests.post if method == "post" else requests.get
    try:
        return api_req(url, **kwargs)
    except Exception as e:
        logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
        return None


def _prefetch_key(url, params):
    return (url, tuple(sorted((params or {}).items())))


def prefetch_requests(requests_to_send):
    """Send the registry requests at the same time, for the lookups that follow.

    requests_to_send is a list of (url, kwargs) of the requests that would be
    sent one after the other. The lookup that follows takes the answer of its
    request instead of sending it (see BaseRegistryAPI._lookup). Nothing is
    started for less than two requests, there is nothing to overlap, nor when
    there is no current request or too many threads are waiting: the lookups
    then send their requests as always.
    """
    request = getRequest()
    if request is None or len(requests_to_send) < 2:
        return
    started = request.other.setdefault(PREFETCHED, {})
    for url, kwargs in requests_to_send:
        key = _prefetch_key(url, kwargs.get("params"))
        if key in started or not _prefetching.acquire(blocking=False):
            continue
        future = Future()

        def run(future=future, url=url, kwargs=kwargs):
            try:
                future.set_result(send_request("get", url, kwargs))
            except BaseException as e:
                future.set_exception(e)
            finally:
                _prefetching.release()

        try:
            threading.Thread(target=run, daemon=True).start()
        except Exception:
            # no thread to start: the lookup sends its request as always
            _prefetching.release()
            logger.warning("Cannot start a thread for a registry request")
            continue
        started[key] = future


def take_prefetched(url, params):
    request = getRequest()
    if request is None:
        return None
    return request.other.get(PREFETCHED, {}).pop(_prefetch_key(url, params), None)


class LookupStats:
    """How often the registry caches of this process keep an answer.

    A lookup is a call of a cached registry lookup, a miss is a call that went
    to the registry (the answer was not kept), a failure is a miss that the
    registry did not answer. A summary of the window is logged when a lookup
    finds the window over, per process (pod): it tells how often a pod has to
    ask the registry again for what another pod asked a moment ago.
    """

    WINDOW = 300

    def __init__(self):
        self._lock = threading.Lock()
        self._counts = {}
        self._since = time()

    def record(self, name, outcome, seconds=0.0):
        done = None
        with self._lock:
            counts = self._counts.setdefault(
                name, {"lookup": 0, "miss": 0, "failure": 0, "seconds": 0.0}
            )
            if outcome == "miss":
                counts["seconds"] += seconds
            counts[outcome] += 1
            if time() - self._since >= self.WINDOW:
                done, self._counts, self._since = self._counts, {}, time()
        if done:
            for name, counts in sorted(done.items()):
                lookups = counts["lookup"]
                logger.info(
                    "Registry cache %s, last %s s: %s lookups, %s asked the "
                    "registry (%.0f%% kept), %s failed, %.1f s waiting for it",
                    name,
                    self.WINDOW,
                    lookups,
                    counts["miss"],
                    100.0 * (lookups - counts["miss"]) / max(lookups, 1),
                    counts["failure"],
                    counts["seconds"],
                )

    def snapshot(self):
        with self._lock:
            return {name: dict(counts) for name, counts in self._counts.items()}


lookup_stats = LookupStats()


class RegistryUnavailable(Exception):
    """The registry did not answer, or answered with a server error.

    Raised by the lookups whose result is cached, so a failure is not stored:
    the next request asks the registry again.
    """


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
    # seconds to connect to the registry
    CONNECT_TIMEOUT = 5
    # seconds to wait for the answer of an administration call
    TIMEOUT = 120
    # seconds to wait for the answer of the lookups that decide what a user can access
    LOOKUP_TIMEOUT = 30

    def __init__(self, registry_name, url, token=None):
        self.registry_name = registry_name
        self.baseUrl = url
        self.token = token

    def set_base_url(self, url, token=None):
        self.baseUrl = url
        self.token = token

    def _request_kwargs(self, data, files, cookies, headers, params, timeout):
        if not timeout:
            timeout = self.TIMEOUT
        if isinstance(timeout, (int, float)):
            timeout = (self.CONNECT_TIMEOUT, timeout)
        return dict(
            data=data,
            files=files,
            cookies=cookies,
            headers=headers,
            params=params,
            verify=False,
            timeout=timeout,
        )

    def _answer(self, response, url, raw=None):
        """What do_api_request gives for the response of a request."""
        if response is None:
            return None
        if response.status_code != requests.codes.ok:
            logger.warning(
                """Retrieved a %s status code when contacting """
                """SatelliteRegistry's url: %s """ % (response.status_code, url)
            )
            if raw:
                return response
            return None

        return response

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
        kwargs = self._request_kwargs(data, files, cookies, headers, params, timeout)
        return self._answer(send_request(method, url, kwargs), url, raw)

    def lookup_request(self, url, headers=None, params=None, timeout=None):
        """The (url, kwargs) that _lookup sends, to send it before with prefetch."""
        timeout = timeout or self.LOOKUP_TIMEOUT
        return url, self._request_kwargs(None, None, None, headers, params, timeout)

    def _lookup(self, url, **kwargs):
        """Request for a lookup whose result is cached or decides access.

        A registry that cannot be reached, or that answers with a server error,
        raises RegistryUnavailable. Other answers are returned, the caller checks
        the status.
        """
        kwargs.setdefault("timeout", self.LOOKUP_TIMEOUT)
        sent = take_prefetched(url, kwargs.get("params"))
        if sent is None:
            response = self.do_api_request(url, raw=True, **kwargs)
        else:
            response = self._answer(sent.result(), url, raw=True)
        if response is None or (
            response.status_code >= 500 or response.status_code in RETRY_LATER_STATUS
        ):
            raise RegistryUnavailable(url)
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
        response = self.do_api_request(url, headers={"Authorization": self.token})

        if response:
            return response.json()

    def get_auditors(self):
        page = "list"
        url_prefix = "/".join([self.baseUrl, "auditors"])
        url = "/".join([url_prefix, page])
        response = self.do_api_request(url, headers={"Authorization": self.token})

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
        response = self.do_api_request(url, headers={"Authorization": self.token})
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
            raise Exception("API request failed: No response received from the server.")

        response.raise_for_status()  # Raise HTTPError for bad responses

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
            raise Exception("API request failed: No response received from the server.")

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

    def get_multi_year_licences(self, params=None):
        page = "multi_year_licences"
        url = "/".join([self.baseUrl, page])
        response = self.do_api_request(
            url, params=params, headers={"Authorization": self.token}
        )
        if response:
            return response.json()

    def get_stocks(self):
        page = "stocks"
        url = "/".join([self.baseUrl, page])
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def get_stocks_dummy(self):
        page = "stocks/import"
        url = "/".join([self.baseUrl, page])
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def get_company_details(self, company_id, domain="FGAS"):
        url = "/".join([self.baseUrl, "undertaking", domain, company_id, "details"])
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def get_auditor_details(self, auditor_id):
        url = "/".join([self.baseUrl, "auditors", auditor_id, "details"])
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def get_company_details_short(self, company_id, domain="FGAS"):
        url = "/".join(
            [self.baseUrl, "undertaking", domain, company_id, "details-short"]
        )
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def _get_aggregated_licences(
        self, company_id, year, data, licence_type, domain="FGAS"
    ):
        """Helper method to fetch aggregated licence data from registry API"""
        url_parts = [
            self.baseUrl,
            "undertaking",
            domain,
            company_id,
            licence_type,
        ]
        if year:
            url_parts.append(year)
        url_parts.append("aggregated")

        url = "/".join(url_parts)
        response = self.do_api_request(
            url,
            method="post",
            data=data,
            headers={"Authorization": self.token},
            raw=True,
        )
        return response

    def get_aggregated_multi_year_licences(self, company_id, year, data, domain="FGAS"):
        return self._get_aggregated_licences(
            company_id, year, data, "multi_year_licences", domain
        )

    def get_company_licences(self, company_id, year, data, domain="FGAS"):
        return self._get_aggregated_licences(company_id, year, data, "licences", domain)

    def get_company_stocks(self, company_id):
        url = "/".join([self.baseUrl, "stocks", company_id])
        response = self.do_api_request(
            url, method="post", headers={"Authorization": self.token}, raw=True
        )
        return response

    def get_company_paus(self, company_id, domain="ODS"):
        url = "/".join([self.baseUrl, "undertaking", domain, company_id, "pau"])
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
                c_type = details.get("address", {}).get("country", {}).get("type")
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
                    details["licences_path"] = "/{}/aggregated_licences_listing".format(
                        path
                    )
                    details["stocks_path"] = "/{}/stock_listing".format(path)
                    details["paus_path"] = "/{}/process_agent_uses_listing".format(path)

            return details

    def getCollectionPaths(self, username, userdata=None):
        """Get all collection paths for a username or userdata.

        A registry that cannot be reached gives no paths: nobody gets access
        that the registry did not confirm.
        """
        try:
            return self._fetchCollectionPaths(username, userdata=userdata)
        except RegistryUnavailable:
            return {"paths": [], "prev_paths": [], "audit_paths": []}

    def _paths_url(self, username, userdata=None):
        # <ecr_host>/user/companies/v2/?username=<username>&ecas_id=<ecas_id>
        if userdata:
            return "{}/user/companies/v2/".format(self.baseUrl), userdata
        return self.baseUrl + "/user/" + username + "/companies", None

    def paths_request(self, username, userdata=None):
        """The (url, kwargs) of the request of _fetchCollectionPaths."""
        url, params = self._paths_url(username, userdata)
        return self.lookup_request(
            url, headers={"Authorization": self.token}, params=params
        )

    def _fetchCollectionPaths(self, username, userdata=None):
        """Get all collection paths for a username or userdata.
        The username request is in the process of being deprecated.
        The userdata request is the preferred method which should match
        either the ecas_id or the username(e-mail) in the ecr.

        Raises RegistryUnavailable when the registry does not answer."""
        url, params = self._paths_url(username, userdata)
        response = self._lookup(
            url, params=params, headers={"Authorization": self.token}
        )
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
                    raise ValueError("Cannot form path with company data: %s" % str(c))
            except Exception as e:
                logger.warning(
                    """Error in company data received from """
                    """SatelliteRegistry: %s""" % repr(e)
                )

            return path

        if response.status_code == requests.codes.ok:
            data = response.json()
            if isinstance(data, list):
                data = {"reporter": data, "auditor": []}
            if data.get("auditor", []):
                for auditor in data["auditor"]:
                    ver = auditor.get("verification_envelope_url")
                    if ver:
                        if ver.startswith("/"):
                            ver = ver.lstrip("/")
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

    def verifyCandidate(self, companyId, userId, candidateId=None, domain="FGAS"):
        # use the right pattern for Api url
        verify_endpoint = "/".join(["candidate", domain, "verify-none", companyId])
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
        response = self.do_api_request(url, headers={"Authorization": self.token})

        if response:
            return response.json()

        return []

    def getUsers(self, domain="FGAS"):
        url = "/".join([self.baseUrl, "user", domain, "list"])
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def getMatchingLog(self, domain="FGAS"):
        url = "/".join([self.baseUrl, "log", "matching", domain])
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def getDataSyncLog(self, domain="FGAS"):
        url = self.baseUrl + "/log/sync"
        url = "/".join([self.baseUrl, "log", "sync", domain])
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def companyNewOldIdCheck(self, companyId="", oldCompanyId=""):
        url = "/".join(
            [
                self.baseUrl,
                "candidate/verify-matching-ids/{0}/{1}".format(companyId, oldCompanyId),
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
                    logger.warning(LOCKDOWN_EMAILS_NOT_SENT % path)

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
        response = self.do_api_request(url, headers={"Authorization": self.token})

        return response

    def getUsersExcelExport(self, domain="FGAS"):
        url = "/".join([self.baseUrl, "export", "user", "list", domain])
        response = self.do_api_request(
            url, headers={"Authorization": self.token}, timeout=120
        )

        return response

    def getSettings(self):
        url = self.baseUrl + "/settings"
        response = self.do_api_request(url, headers={"Authorization": self.token})
        if response:
            return response.json()

    def getAllEmails(self):
        url = self.baseUrl + "/mail/list"
        response = self.do_api_request(url, headers={"Authorization": self.token})
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
            logger.warning(LOCKDOWN_EMAILS_NOT_SENT % path)

    def _unlockCompany(self, company_id, old_collection_id, country_code, domain, user):
        path = self.buildCollectionPath(
            domain, country_code, str(company_id), old_collection_id
        )
        bdrAuth = self.authMiddleware
        bdrAuth.unlockCollection(path, user)
        return path

    def unlockCompany(self, company_id, old_collection_id, country_code, domain, user):
        path = self._unlockCompany(
            company_id, old_collection_id, country_code, domain, user
        )

        email_sending_failed = False
        url = "/".join([self.baseUrl, "alert_lockdown", "wrong_lockdown", domain])
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
            logger.warning(LOCKDOWN_EMAILS_NOT_SENT % path)

    def lockedCompany(self, company_id, old_collection_id, country_code, domain):
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
        collection_folder = old_collection_id if old_collection_id else company_id

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

    def get_company_details(self, company_id, domain=None):
        """Get company details from Registry"""
        failed = ("company_details", self.baseUrl, company_id, domain)
        if failed_in_this_request(failed):
            return None
        try:
            # a copy: the cached details are shared, a caller may change them
            return copy.deepcopy(self._get_company_details(company_id, domain))
        except RegistryUnavailable:
            remember_failure_in_this_request(failed)
            return None

    # A failure is not cached: the exception leaves nothing in the cache.
    @ram.cache(
        lambda fun, self, company_id, domain=None: (
            company_id,
            domain,
            time() // (60 * 60),
        )
    )
    def _get_company_details(self, company_id, domain=None):
        url = self.baseUrl + "/management/companies/account/{0}/{1}".format(
            company_id, domain
        )
        # not a lookup that decides access: it keeps the long timeout
        response = self._lookup(
            url,
            headers={"Authorization": self.bdr_registry_token},
            timeout=self.TIMEOUT,
        )
        if response.status_code == requests.codes.ok:
            return response.json()

    def _user_details_url(self, username):
        return (
            self.baseUrl + "/management/username/companies/",
            {"username": username},
        )

    def user_details_request(self, username):
        """The (url, kwargs) of the request for the details of a user, when cold."""
        if failed_in_this_request(
            ("user_details", self.baseUrl, username)
        ) or not is_cold(USER_DETAILS, _user_details_key(username)):
            return None
        url, params = self._user_details_url(username)
        return self.lookup_request(
            url, headers={"Authorization": self.bdr_registry_token}, params=params
        )

    def get_user_details(self, username):
        """Get details for username"""
        failed = ("user_details", self.baseUrl, username)
        if failed_in_this_request(failed):
            return []
        lookup_stats.record("user_details", "lookup")
        try:
            return self._get_user_details(username)
        except RegistryUnavailable:
            lookup_stats.record("user_details", "failure")
            remember_failure_in_this_request(failed)
            return []

    # A failure is not cached: the exception leaves nothing in the cache.
    @ram.cache(lambda *args, **kwargs: _user_details_key(args[2]))
    def _get_user_details(self, username):
        url, params = self._user_details_url(username)
        started = time()
        try:
            response = self._lookup(
                url, params=params, headers={"Authorization": self.bdr_registry_token}
            )
        finally:
            lookup_stats.record("user_details", "miss", time() - started)
        if response.status_code == requests.codes.ok:
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
