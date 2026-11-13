"""A failed call to the registry or to ROD is not cached.

The answers are cached for minutes (the registry) or hours (ROD). A call that
failed must not be kept: a registry that was down for a moment would hide the
collections of a user until the cache expires, even if the registry is back.
The files and the answers are dummy.
"""

import logging
import threading
import unittest
from unittest.mock import Mock, patch

from ZODB.POSException import ConflictError

import requests
from plone.memoize import ram

from Products.Reportek import BdrAuthorizationMiddleware as middleware_module
from Products.Reportek import RegistryManagement
from Products.Reportek.BdrAuthorizationMiddleware import BdrAuthorizationMiddleware
from Products.Reportek.CountriesManager import CountriesManager
from Products.Reportek.DataflowsManager import (
    DataflowsManager,
    ServiceTemporarilyUnavailableException,
)
from Products.Reportek.RegistryManagement import (
    PREFETCHED,
    BaseRegistryAPI,
    BDRRegistryAPI,
    FGASRegistryAPI,
    LookupStats,
    RegistryUnavailable,
    prefetch_requests,
)

REGISTRY_GET = "Products.Reportek.RegistryManagement.requests.get"
DOWN = requests.exceptions.ConnectTimeout("registry down")


def answer(status_code=200, payload=None):
    response = Mock()
    response.status_code = status_code
    response.ok = status_code < 400
    response.__bool__ = lambda self: status_code < 400
    response.json = Mock(return_value=payload)
    return response


class FakeRequest:
    def __init__(self):
        self.other = {}


def in_request(request):
    return patch(
        "Products.Reportek.RegistryManagement.getRequest", return_value=request
    )


class CacheTest(unittest.TestCase):
    def setUp(self):
        ram.global_cache.invalidateAll()
        self.addCleanup(ram.global_cache.invalidateAll)


class BDRRegistryTest(CacheTest):
    def setUp(self):
        super().setUp()
        self.api = BDRRegistryAPI("BDR", "http://registry")
        self.api.bdr_registry_token = "token"
        self.companies = [
            {"has_reporting_folder": True, "reporting_folder": "ods/xx/c1"},
        ]

    @patch(REGISTRY_GET)
    def test_user_details_are_kept(self, get):
        get.return_value = answer(200, self.companies)
        self.assertEqual(self.api.get_user_details("a"), self.companies)
        self.assertEqual(self.api.get_user_details("a"), self.companies)
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_company_details_changed_by_a_caller_are_not_changed_for_others(self, get):
        get.return_value = answer(200, {"name": "c", "address": {"city": "x"}})
        first = self.api.get_company_details("1", domain="ODS")
        first["registry"] = "changed"
        first["address"]["city"] = "changed"
        second = self.api.get_company_details("1", domain="ODS")
        self.assertEqual(second, {"name": "c", "address": {"city": "x"}})
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_registry_that_does_not_answer_is_not_kept(self, get):
        get.side_effect = [DOWN, answer(200, self.companies)]
        self.assertEqual(self.api.get_user_details("a"), [])
        self.assertEqual(self.api.get_user_details("a"), self.companies)
        self.assertEqual(get.call_count, 2)

    @patch(REGISTRY_GET)
    def test_server_error_is_not_kept(self, get):
        get.side_effect = [answer(503), answer(200, self.companies)]
        self.assertEqual(self.api.get_user_details("a"), [])
        self.assertEqual(self.api.get_user_details("a"), self.companies)
        self.assertEqual(get.call_count, 2)

    @patch(REGISTRY_GET)
    def test_too_many_requests_and_timeout_answers_are_not_kept(self, get):
        get.side_effect = [answer(429), answer(408), answer(200, self.companies)]
        self.assertEqual(self.api.get_user_details("a"), [])
        self.assertEqual(self.api.get_user_details("a"), [])
        self.assertEqual(self.api.get_user_details("a"), self.companies)
        self.assertEqual(get.call_count, 3)

    @patch(REGISTRY_GET)
    def test_the_rest_of_the_request_does_not_ask_a_registry_that_failed(self, get):
        get.side_effect = DOWN
        with in_request(FakeRequest()):
            for _ in range(20):
                self.assertEqual(self.api.get_user_details("a"), [])
                self.assertIsNone(self.api.get_company_details("c1", "ods"))
        self.assertEqual(get.call_count, 2)

    @patch(REGISTRY_GET)
    def test_the_next_request_asks_the_registry_again(self, get):
        get.side_effect = [DOWN, answer(200, self.companies)]
        with in_request(FakeRequest()):
            self.assertEqual(self.api.get_user_details("a"), [])
        with in_request(FakeRequest()):
            self.assertEqual(self.api.get_user_details("a"), self.companies)
        self.assertEqual(get.call_count, 2)

    @patch(REGISTRY_GET)
    def test_a_failure_for_a_user_is_not_a_failure_for_another(self, get):
        get.side_effect = [DOWN, answer(200, self.companies)]
        with in_request(FakeRequest()):
            self.assertEqual(self.api.get_user_details("a"), [])
            self.assertEqual(self.api.get_user_details("b"), self.companies)

    @patch(REGISTRY_GET)
    def test_user_that_the_registry_does_not_know_is_kept(self, get):
        get.return_value = answer(404)
        self.assertEqual(self.api.get_user_details("a"), [])
        self.assertEqual(self.api.get_user_details("a"), [])
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_collections_of_a_user_after_the_registry_is_back(self, get):
        get.side_effect = [DOWN, answer(200, self.companies)]
        self.assertEqual(self.api.getCollectionPaths("a")["paths"], [])
        self.assertEqual(self.api.getCollectionPaths("a")["paths"], ["ods/xx/c1"])

    @patch(REGISTRY_GET)
    def test_company_details_are_kept(self, get):
        get.return_value = answer(200, {"name": "Dummy"})
        self.assertEqual(self.api.get_company_details("c1", "ods"), {"name": "Dummy"})
        self.assertEqual(self.api.get_company_details("c1", "ods"), {"name": "Dummy"})
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_company_details_of_another_domain_are_not_the_ones_of_the_first(self, get):
        get.side_effect = [
            answer(200, {"name": "In ODS"}),
            answer(200, {"name": "In FGAS"}),
        ]
        self.assertEqual(self.api.get_company_details("c1", "ods")["name"], "In ODS")
        self.assertEqual(self.api.get_company_details("c1", "fgas")["name"], "In FGAS")
        self.assertEqual(self.api.get_company_details("c1", "ods")["name"], "In ODS")
        self.assertEqual(get.call_count, 2)

    @patch(REGISTRY_GET)
    def test_company_details_that_failed_are_not_kept(self, get):
        get.side_effect = [DOWN, answer(500), answer(200, {"name": "Dummy"})]
        self.assertIsNone(self.api.get_company_details("c1", "ods"))
        self.assertIsNone(self.api.get_company_details("c1", "ods"))
        self.assertEqual(self.api.get_company_details("c1", "ods"), {"name": "Dummy"})
        self.assertEqual(get.call_count, 3)


class FGASRegistryTest(CacheTest):
    def setUp(self):
        super().setUp()
        self.api = FGASRegistryAPI("FGAS", "http://registry", "token")
        self.empty = {"paths": [], "prev_paths": [], "audit_paths": []}

    @patch(REGISTRY_GET)
    def test_a_registry_that_does_not_answer_gives_no_access(self, get):
        get.side_effect = DOWN
        self.assertEqual(self.api.getCollectionPaths("a"), self.empty)
        self.assertEqual(
            self.api.getCollectionPaths("a", userdata={"username": "a"}), self.empty
        )

    def test_the_lookup_that_raises_cannot_be_published_from_the_web(self):
        for name in ("_fetchCollectionPaths", "fetchCollectionPaths"):
            with self.assertRaises(Exception):
                self.api.restrictedTraverse(name)

    @patch(REGISTRY_GET)
    def test_fetch_says_that_the_registry_is_unavailable(self, get):
        for failure in (DOWN, answer(502)):
            get.side_effect = [failure]
            with self.assertRaises(RegistryUnavailable):
                self.api._fetchCollectionPaths("a")

    @patch(REGISTRY_GET)
    def test_user_without_companies_is_not_a_failure(self, get):
        get.return_value = answer(200, [])
        self.assertEqual(self.api._fetchCollectionPaths("a"), self.empty)

    @patch(REGISTRY_GET)
    def test_unknown_user_is_not_a_failure(self, get):
        get.return_value = answer(404)
        self.assertEqual(self.api._fetchCollectionPaths("a"), self.empty)


class MiddlewareTest(CacheTest):
    def setUp(self):
        super().setUp()
        self.middleware = BdrAuthorizationMiddleware("http://middleware")
        self.middleware.FGASRegistryAPI = FGASRegistryAPI(
            "FGAS", "http://registry", "token"
        )
        self.companies = [
            {
                "company_id": 1,
                "country": "RO",
                "domain": "FGAS",
                "collection_id": "fgas30001",
            }
        ]

    def paths(self, user="a"):
        return self.middleware.getUserCollectionPaths(
            user, userdata={"username": user}, recheck_interval=300
        )

    @patch(REGISTRY_GET)
    def test_the_paths_are_kept(self, get):
        get.return_value = answer(200, self.companies)
        self.assertEqual(self.paths()["paths"], self.paths()["paths"])
        self.assertTrue(self.paths()["paths"])
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_the_user_has_no_paths_while_the_registry_is_down(self, get):
        get.side_effect = DOWN
        self.assertEqual(
            self.paths(), {"paths": [], "prev_paths": [], "audit_paths": []}
        )

    @patch(REGISTRY_GET)
    def test_the_user_gets_the_paths_as_soon_as_the_registry_is_back(self, get):
        get.side_effect = [DOWN, answer(503), answer(200, self.companies)]
        self.assertEqual(self.paths()["paths"], [])
        self.assertEqual(self.paths()["paths"], [])
        self.assertTrue(self.paths()["paths"])
        self.assertEqual(get.call_count, 3)

    @patch(REGISTRY_GET)
    def test_the_same_question_is_kept(self, get):
        get.return_value = answer(200, self.companies)
        for _ in range(3):
            self.middleware.getUserCollectionPaths(
                "id1",
                userdata={"username": "a", "ecas_id": "id1"},
                recheck_interval=300,
            )
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_another_question_for_the_same_id_is_not_answered_from_the_first(self, get):
        get.return_value = answer(200, self.companies)
        ask = self.middleware.getUserCollectionPaths
        ask("id1", userdata={"username": "a", "ecas_id": "id1"}, recheck_interval=300)
        # the username changed
        ask("id1", userdata={"username": "b", "ecas_id": "id1"}, recheck_interval=300)
        # the question by username only
        ask("id1", userdata=None, recheck_interval=300)
        self.assertEqual(get.call_count, 3)
        self.assertIn("id1", get.call_args[0][0])

    @patch(REGISTRY_GET)
    def test_the_order_of_the_userdata_does_not_matter(self, get):
        get.return_value = answer(200, self.companies)
        ask = self.middleware.getUserCollectionPaths
        ask("id1", userdata={"username": "a", "ecas_id": "id1"}, recheck_interval=300)
        ask("id1", userdata={"ecas_id": "id1", "username": "a"}, recheck_interval=300)
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_a_list_of_checks_asks_a_registry_that_is_down_once(self, get):
        get.side_effect = DOWN
        with in_request(FakeRequest()):
            for i in range(227):
                self.assertFalse(
                    self.middleware.authorizedUser(
                        "a", "ods/xx/env%d" % i, userdata={"username": "a"}
                    )
                )
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_the_next_request_asks_the_registry_again(self, get):
        get.side_effect = [DOWN, answer(200, self.companies)]
        with in_request(FakeRequest()):
            self.assertEqual(self.paths()["paths"], [])
            self.assertEqual(self.paths()["paths"], [])
        with in_request(FakeRequest()):
            self.assertTrue(self.paths()["paths"])
        self.assertEqual(get.call_count, 2)

    @patch(REGISTRY_GET)
    def test_a_user_without_companies_is_kept(self, get):
        get.return_value = answer(200, [])
        self.paths()
        self.paths()
        self.assertEqual(get.call_count, 1)


class TimeoutsTest(unittest.TestCase):
    @patch(REGISTRY_GET)
    def test_the_lookups_that_decide_access_have_short_timeouts(self, get):
        get.return_value = answer(200, [])
        FGASRegistryAPI("FGAS", "http://registry", "token")._fetchCollectionPaths("a")
        self.assertEqual(
            get.call_args[1]["timeout"],
            (BaseRegistryAPI.CONNECT_TIMEOUT, BaseRegistryAPI.LOOKUP_TIMEOUT),
        )

    @patch(REGISTRY_GET)
    def test_the_other_calls_connect_fast_and_wait_as_before(self, get):
        get.return_value = answer(200, [])
        FGASRegistryAPI("FGAS", "http://registry", "token").do_api_request("http://x")
        self.assertEqual(
            get.call_args[1]["timeout"],
            (BaseRegistryAPI.CONNECT_TIMEOUT, BaseRegistryAPI.TIMEOUT),
        )

    @patch(REGISTRY_GET)
    def test_a_timeout_of_the_caller_is_the_one_to_wait_for_the_answer(self, get):
        get.return_value = answer(200, [])
        api = FGASRegistryAPI("FGAS", "http://registry", "token")
        api.do_api_request("http://x", timeout=7)
        self.assertEqual(
            get.call_args[1]["timeout"], (BaseRegistryAPI.CONNECT_TIMEOUT, 7)
        )
        api.do_api_request("http://x", timeout=(2, 3))
        self.assertEqual(get.call_args[1]["timeout"], (2, 3))


class Rod(DataflowsManager):
    _dfm_type = "dfm_rest"
    _dfm_rest_url = "http://rod/obligations"
    _dfm_obl_url_prefix = "http://rod"

    def get_custom_dataflows(self):
        return [{"uri": "custom", "TITLE": "Custom", "terminated": "0"}]


class Countries(CountriesManager):
    _cm_type = "cm_rest"
    _cm_rest_url = "http://rod/countries"


ROD_DATAFLOWS_GET = "Products.Reportek.DataflowsManager.requests.get"
ROD_COUNTRIES_GET = "Products.Reportek.CountriesManager.requests.get"


def obligation(obligation_id):
    return {"obligationId": obligation_id, "oblTitle": "Dummy", "terminate": "N"}


class DataflowsTest(CacheTest):
    def setUp(self):
        super().setUp()
        self.rod = Rod()

    @patch(ROD_DATAFLOWS_GET)
    def test_the_dataflows_are_kept(self, get):
        get.return_value = answer(200, [obligation(1)])
        self.assertEqual(len(self.rod.dataflow_rod()), 2)
        self.assertEqual(len(self.rod.dataflow_rod()), 2)
        self.assertEqual(get.call_count, 1)

    @patch(ROD_DATAFLOWS_GET)
    def test_a_rest_call_without_timeout_gets_one(self, get):
        get.return_value = answer(200, [obligation(1)])
        with patch.object(Rod, "dfm_timeout", None):
            self.rod.dataflow_rod()
        self.assertEqual(get.call_args[1]["timeout"], (5, 30))

    @patch(ROD_DATAFLOWS_GET)
    def test_an_error_status_gives_the_custom_dataflows_and_is_not_kept(self, get):
        get.side_effect = [answer(503), answer(200, [obligation(1)])]
        self.assertEqual([d["uri"] for d in self.rod.dataflow_rod()], ["custom"])
        self.assertEqual(len(self.rod.dataflow_rod()), 2)
        self.assertEqual(get.call_count, 2)

    @patch(ROD_DATAFLOWS_GET)
    def test_the_dictionary_of_dataflows_is_kept(self, get):
        get.return_value = answer(200, [obligation(1)])
        self.assertEqual(len(self.rod.dataflow_dict()), 2)
        self.assertEqual(len(self.rod.dataflow_dict()), 2)
        self.assertEqual(get.call_count, 1)

    @patch(ROD_DATAFLOWS_GET)
    def test_the_dictionary_after_an_error_status_is_not_kept(self, get):
        get.side_effect = [answer(500), answer(200, [obligation(1)])]
        self.assertEqual(list(self.rod.dataflow_dict()), ["custom"])
        self.assertEqual(len(self.rod.dataflow_dict()), 2)

    @patch(ROD_DATAFLOWS_GET)
    def test_a_rod_that_does_not_answer_is_not_kept(self, get):
        get.side_effect = [DOWN, answer(200, [obligation(1)])]
        with self.assertRaises(ServiceTemporarilyUnavailableException):
            self.rod.dataflow_dict()
        self.assertEqual(len(self.rod.dataflow_dict()), 2)


class CountriesTest(CacheTest):
    def setUp(self):
        super().setUp()
        self.rod = Countries()
        self.countries = [{"twoLetter": "RO", "name": "Romania", "spatialId": 7}]

    @patch(ROD_COUNTRIES_GET)
    def test_the_countries_are_kept(self, get):
        get.return_value = answer(200, self.countries)
        self.assertEqual(self.rod.localities_rod()[0]["iso"], "RO")
        self.assertEqual(self.rod.localities_rod()[0]["iso"], "RO")
        self.assertEqual(get.call_count, 1)

    @patch(ROD_COUNTRIES_GET)
    def test_an_error_status_is_not_kept(self, get):
        get.side_effect = [answer(500), answer(200, self.countries)]
        self.assertEqual(self.rod.localities_rod(), [])
        self.assertEqual(self.rod.localities_rod()[0]["iso"], "RO")
        self.assertEqual(get.call_count, 2)

    @patch(ROD_COUNTRIES_GET)
    def test_the_dictionary_is_kept(self, get):
        get.return_value = answer(200, self.countries)
        self.assertEqual(len(self.rod.localities_dict()), 1)
        self.assertEqual(len(self.rod.localities_dict()), 1)
        self.assertEqual(get.call_count, 1)

    @patch(ROD_COUNTRIES_GET)
    def test_the_dictionary_after_a_failure_is_not_kept(self, get):
        get.side_effect = [DOWN, answer(500), answer(200, self.countries)]
        self.assertEqual(self.rod.localities_dict(), {})
        self.assertEqual(self.rod.localities_dict(), {})
        self.assertEqual(len(self.rod.localities_dict()), 1)

    @patch(ROD_COUNTRIES_GET)
    def test_a_country_is_looked_up_or_unknown(self, get):
        get.return_value = answer(200, self.countries)
        uri = "http://rod/spatial/7"
        self.assertEqual(self.rod.localities_dict(uri)["name"], "Romania")
        self.assertEqual(self.rod.localities_dict("other")["name"], "Unknown")
        self.assertEqual(self.rod.localities_dict(uri)["name"], "Romania")

    @patch(ROD_COUNTRIES_GET)
    def test_every_country_is_answered_from_one_kept_dictionary(self, get):
        get.return_value = answer(200, self.countries)
        for country in ("a", "b", "c", None, "http://rod/spatial/7"):
            self.rod.localities_dict(country)
        self.assertEqual(get.call_count, 1)

    def test_a_conflict_is_not_hidden(self):
        with patch.object(Countries, "_localities_rod", side_effect=ConflictError()):
            with self.assertRaises(ConflictError):
                self.rod.localities_dict()

    @patch(ROD_COUNTRIES_GET)
    def test_a_rest_call_without_timeout_gets_one(self, get):
        get.return_value = answer(200, self.countries)
        self.rod.cm_timeout  # the timeout of the xmlrpc settings
        with patch.object(Countries, "cm_timeout", None):
            self.rod.localities_rod()
        self.assertEqual(get.call_args[1]["timeout"], (5, 30))

    @patch(ROD_COUNTRIES_GET)
    def test_the_table_is_empty_when_rod_does_not_answer(self, get):
        get.side_effect = DOWN
        self.assertEqual(self.rod.localities_table(), [])


class PrefetchTest(CacheTest):
    """The requests that both miss are sent at the same time."""

    def setUp(self):
        super().setUp()
        self.middleware = BdrAuthorizationMiddleware("http://middleware")
        self.middleware.FGASRegistryAPI = FGASRegistryAPI(
            "FGAS", "http://registry", "token"
        )
        self.bdr = BDRRegistryAPI("BDR", "http://bdr")
        self.bdr.bdr_registry_token = "token"
        self.userdata = {"username": "a", "ecas_id": "e1"}
        self.fgas = [
            {
                "company_id": 1,
                "country": "RO",
                "domain": "FGAS",
                "collection_id": "fgas30001",
            }
        ]
        self.request = FakeRequest()

    def wait_for_the_requests(self):
        for future in list(self.request.other.get(PREFETCHED, {}).values()):
            future.result(timeout=5)

    def requests(self):
        return [
            self.middleware.paths_request("e1", userdata=self.userdata),
            self.bdr.user_details_request("a"),
        ]

    def lookups(self):
        paths = self.middleware.getUserCollectionPaths(
            "e1", userdata=self.userdata, recheck_interval=300
        )
        return paths, self.bdr.get_user_details("a")

    def test_both_requests_are_in_flight_together(self):
        both_started = threading.Barrier(2, timeout=5)

        def get(url, **kwargs):
            both_started.wait()  # a sequential lookup would never get past here
            if "/user/companies/v2/" in url:
                return answer(200, self.fgas)
            return answer(200, [{"has_reporting_folder": True}])

        with in_request(self.request), patch(REGISTRY_GET, side_effect=get) as mock:
            prefetch_requests(self.requests())
            paths, details = self.lookups()
        self.assertEqual(mock.call_count, 2)
        self.assertTrue(paths["paths"])
        self.assertEqual(details, [{"has_reporting_folder": True}])

    def test_the_lookups_are_cached_as_always(self):
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.side_effect = lambda url, **kw: (
                answer(200, self.fgas) if "v2" in url else answer(200, [])
            )
            prefetch_requests(self.requests())
            self.lookups()
            self.lookups()
            self.assertEqual(get.call_count, 2)
            self.assertEqual(self.requests(), [None, None])

    def test_nothing_is_sent_when_one_of_them_is_kept(self):
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.return_value = answer(200, [])
            self.bdr.get_user_details("a")
            self.assertEqual(get.call_count, 1)
            pending = self.requests()
            self.assertIsNone(pending[1])
            self.assertIsNotNone(pending[0])
            prefetch_requests([r for r in pending if r])
            self.assertEqual(self.request.other.get(PREFETCHED, {}), {})
            self.assertEqual(get.call_count, 1)

    def test_nothing_is_sent_without_a_request(self):
        with in_request(None), patch(REGISTRY_GET) as get:
            prefetch_requests(self.requests())
            self.assertEqual(get.call_count, 0)

    def test_a_registry_that_does_not_answer_gives_no_access_and_is_not_kept(
        self,
    ):
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.side_effect = DOWN
            prefetch_requests(self.requests())
            paths, details = self.lookups()
            self.assertEqual(paths, {"paths": [], "prev_paths": [], "audit_paths": []})
            self.assertEqual(details, [])
        # the next request asks again
        with in_request(FakeRequest()), patch(REGISTRY_GET) as get:
            get.side_effect = lambda url, **kw: (
                answer(200, self.fgas) if "v2" in url else answer(200, [])
            )
            paths, _ = self.lookups()
            self.assertTrue(paths["paths"])

    def test_the_request_waits_at_most_as_the_lookup_does(self):
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.return_value = answer(200, [])
            prefetch_requests(self.requests())
            self.wait_for_the_requests()
            self.assertEqual(get.call_count, 2)
            for kwargs in (c.kwargs for c in get.call_args_list):
                self.assertEqual(kwargs["timeout"], (5, 30))

    def test_a_lookup_does_not_take_the_answer_of_another_request(self):
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.return_value = answer(200, [])
            prefetch_requests(self.requests())
            self.wait_for_the_requests()
            self.bdr.get_user_details("other")
            self.assertEqual(get.call_count, 3)

    def test_without_threads_available_the_lookups_send_their_requests(self):
        with patch.object(
            RegistryManagement._prefetching, "acquire", return_value=False
        ):
            with in_request(self.request), patch(REGISTRY_GET) as get:
                get.side_effect = lambda url, **kw: (
                    answer(200, self.fgas) if "v2" in url else answer(200, [])
                )
                prefetch_requests(self.requests())
                self.assertEqual(get.call_count, 0)
                paths, _ = self.lookups()
                self.assertTrue(paths["paths"])
                self.assertEqual(get.call_count, 2)

    def test_a_registry_that_is_down_is_not_prefetched_again_in_the_request(self):
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.side_effect = DOWN
            prefetch_requests(self.requests())
            self.lookups()
            self.assertEqual(get.call_count, 2)
            # the lookups failed: a later check of the same request does not ask
            self.assertEqual(self.requests(), [None, None])
            prefetch_requests([r for r in self.requests() if r])
            self.assertEqual(get.call_count, 2)

    def test_a_thread_that_cannot_be_started_leaves_the_lookups_as_they_were(self):
        permits = RegistryManagement._prefetching
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.side_effect = lambda url, **kw: (
                answer(200, self.fgas) if "v2" in url else answer(200, [])
            )
            with patch.object(threading.Thread, "start", side_effect=RuntimeError):
                for _ in range(20):
                    prefetch_requests(self.requests())
            self.assertEqual(self.request.other.get(PREFETCHED, {}), {})
            paths, _ = self.lookups()
            self.assertTrue(paths["paths"])
        # every permit is back
        taken = [permits.acquire(blocking=False) for _ in range(16)]
        self.assertTrue(all(taken))
        for _ in taken:
            permits.release()

    def one_registry_is_down(self, down):
        def get(url, **kwargs):
            fgas = "v2" in url
            if (down == "fgas") == fgas:
                raise DOWN
            return answer(200, self.fgas if fgas else [{"has_reporting_folder": True}])

        return get

    def test_the_fgas_registry_is_down_the_bdr_one_answers(self):
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.side_effect = self.one_registry_is_down("fgas")
            prefetch_requests(self.requests())
            paths, details = self.lookups()
            self.assertEqual(paths, {"paths": [], "prev_paths": [], "audit_paths": []})
            self.assertEqual(details, [{"has_reporting_folder": True}])
            self.assertEqual(get.call_count, 2)
        # the answer of the one that worked is kept, the failure is not
        pending = self.requests()
        self.assertIsNotNone(pending[0])
        self.assertIsNone(pending[1])

    def test_the_bdr_registry_is_down_the_fgas_one_answers(self):
        with in_request(self.request), patch(REGISTRY_GET) as get:
            get.side_effect = self.one_registry_is_down("bdr")
            prefetch_requests(self.requests())
            paths, details = self.lookups()
            self.assertTrue(paths["paths"])
            self.assertEqual(details, [])
            self.assertEqual(get.call_count, 2)
        pending = self.requests()
        self.assertIsNone(pending[0])
        self.assertIsNotNone(pending[1])


class LookupStatsTest(CacheTest):
    """The caches count how often they keep an answer."""

    def setUp(self):
        super().setUp()
        self.stats = LookupStats()
        for module in (RegistryManagement, middleware_module):
            patcher = patch.object(module, "lookup_stats", self.stats)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.middleware = BdrAuthorizationMiddleware("http://middleware")
        self.middleware.FGASRegistryAPI = FGASRegistryAPI(
            "FGAS", "http://registry", "token"
        )
        self.bdr = BDRRegistryAPI("BDR", "http://bdr")
        self.bdr.bdr_registry_token = "token"

    def paths(self):
        return self.middleware.getUserCollectionPaths(
            "e1", userdata={"username": "a", "ecas_id": "e1"}, recheck_interval=300
        )

    @patch(REGISTRY_GET)
    def test_the_paths_count_the_lookups_that_asked_the_registry(self, get):
        get.return_value = answer(200, [])
        for _ in range(3):
            self.paths()
        counts = self.stats.snapshot()["paths"]
        self.assertEqual((counts["lookup"], counts["miss"]), (3, 1))
        self.assertEqual(counts["failure"], 0)

    @patch(REGISTRY_GET)
    def test_the_details_of_the_user_count_the_lookups_that_asked_the_registry(
        self, get
    ):
        get.return_value = answer(200, [])
        for _ in range(4):
            self.bdr.get_user_details("a")
        counts = self.stats.snapshot()["user_details"]
        self.assertEqual((counts["lookup"], counts["miss"]), (4, 1))

    @patch(REGISTRY_GET)
    def test_a_failure_is_counted_and_a_check_that_follows_in_the_request_is_not(
        self, get
    ):
        get.side_effect = DOWN
        with in_request(FakeRequest()):
            for _ in range(5):
                self.paths()
        counts = self.stats.snapshot()["paths"]
        self.assertEqual(
            (counts["lookup"], counts["miss"], counts["failure"]), (1, 1, 1)
        )

    def test_a_summary_is_logged_when_the_window_is_over(self):
        # the test layers switch the logging off
        previous = logging.root.manager.disable
        logging.disable(logging.NOTSET)
        self.addCleanup(logging.disable, previous)
        with patch.object(RegistryManagement, "time") as clock:
            clock.return_value = 1000
            stats = LookupStats()
            stats.record("paths", "lookup")
            stats.record("paths", "miss", 1.5)
            stats.record("paths", "lookup")
            clock.return_value = 1000 + LookupStats.WINDOW
            with self.assertLogs("Reportek", "INFO") as logged:
                stats.record("paths", "lookup")
        self.assertEqual(len(logged.records), 1)
        message = logged.records[0].getMessage()
        self.assertIn("3 lookups, 1 asked the registry (67% kept)", message)
        self.assertIn("1.5 s", message)
        # the next window starts empty
        self.assertEqual(stats.snapshot(), {})
