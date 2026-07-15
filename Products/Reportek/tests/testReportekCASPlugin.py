import pickle
import unittest
from unittest.mock import patch

from Products.Reportek import config
from Products.Reportek.ReportekCASPlugin import (
    ReportekCASAssertion,
    ReportekCASPlugin,
    ReportekCASPrincipal,
    _TimeoutSession,
)
from Products.Reportek.session import ZopeBeakerSessionWrapper
from Products.Reportek.updates.u20260709_import_ecas_plugin import _set_plugin_properties


class DummyRequest:
    form = {}

    def __init__(self, session=None, ticket=None):
        self.SESSION = session
        self.form = {}
        self._data = {}
        if ticket:
            self.form["ticket"] = ticket
            self._data["ticket"] = ticket

    def get(self, key, default=None):
        return self._data.get(key, default)


class DummyResponse:
    def __init__(self):
        self.redirect_url = None

    def redirect(self, url, lock=0):
        self.redirect_url = url


class DummySession(dict):
    cleared = False

    def set(self, key, value):
        self[key] = value

    def getId(self):
        return "session-1"

    def clear(self):
        self.cleared = True
        super().clear()


class DummyCASClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.url_suffix = "serviceValidate"

    def get_login_url(self):
        return "https://login.example/cas/login"


class TestReportekCASPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = ReportekCASPlugin("eCas")
        self.plugin.serviceUrl = "https://bdr.example/"
        self.plugin.casServerUrlPrefix = "https://webgate.example/cas"
        self.plugin.casServerValidationUrl = "https://ecas.example/cas"
        self.plugin.internalMapping = False

    def test_validation_endpoint_is_explicit_not_protocol_encoded(self):
        self.plugin.ticketValidationSpecification = "CAS 2.0"
        self.plugin.serviceValidationEndpoint = "laxValidate"
        with patch("Products.Reportek.ReportekCASPlugin.CASClient", DummyCASClient):
            client = self.plugin._cas_client(service="https://bdr.example/", validation=True)
        self.assertEqual(client.url_suffix, "laxValidate")
        self.assertEqual(client.kwargs["version"], 2)
        self.assertEqual(client.kwargs["server_url"], "https://ecas.example/cas/")

    def test_cas_client_uses_request_timeout_session(self):
        with patch("Products.Reportek.ReportekCASPlugin.CASClient", DummyCASClient):
            client = self.plugin._cas_client(service="https://bdr.example/", validation=True)
        self.assertIsInstance(client.kwargs["session"], _TimeoutSession)
        self.assertEqual(client.kwargs["session"].timeout, 10)

    def test_parse_ecas_lax_validate_response_prefers_moniker(self):
        xml = b"""
        <cas:serviceResponse xmlns:cas="https://ecas.ec.europa.eu/cas/schemas">
          <cas:authenticationSuccess>
            <cas:user>ecas-id-1</cas:user>
            <cas:moniker>user.one</cas:moniker>
            <cas:authenticationLevel>HIGH</cas:authenticationLevel>
            <cas:email>user.one@example.org</cas:email>
          </cas:authenticationSuccess>
        </cas:serviceResponse>
        """
        user, attributes, pgtiou = self.plugin._parse_validation_response(xml)
        self.assertEqual(user, "ecas-id-1")
        self.assertEqual(attributes["moniker"], "user.one")
        self.assertIsNone(pgtiou)
        principal = self.plugin._principal_from_cas(user, attributes)
        self.assertEqual(principal.id, "user.one")
        self.assertEqual(principal.ecas_id, "ecas-id-1")

    def test_parse_eid_attributes_are_preserved(self):
        xml = b"""
        <cas:serviceResponse xmlns:cas="https://ecas.ec.europa.eu/cas/schemas">
          <cas:authenticationSuccess>
            <cas:user>ecas-id-1</cas:user>
            <cas:attributes>
              <cas:uid>ecas-id-1</cas:uid>
              <cas:moniker>user.one</cas:moniker>
              <cas:authenticationLevel>STRONG</cas:authenticationLevel>
              <cas:assuranceLevel>3</cas:assuranceLevel>
              <cas:storkId>STORK-SANITISED-ID</cas:storkId>
              <cas:domain>external</cas:domain>
              <cas:domainUsername>eid-user</cas:domainUsername>
            </cas:attributes>
          </cas:authenticationSuccess>
        </cas:serviceResponse>
        """
        user, attributes, pgtiou = self.plugin._parse_validation_response(xml)
        principal = self.plugin._principal_from_cas(user, attributes)

        self.assertEqual(user, "ecas-id-1")
        self.assertEqual(principal.id, "user.one")
        self.assertEqual(principal.ecas_id, "ecas-id-1")
        self.assertEqual(principal.meta["authenticationLevel"], "STRONG")
        self.assertEqual(principal.meta["assuranceLevel"], "3")
        self.assertEqual(principal.meta["storkId"], "STORK-SANITISED-ID")
        self.assertEqual(principal.meta["domain"], "external")
        self.assertEqual(principal.meta["domainUsername"], "eid-user")
        self.assertIsNone(pgtiou)

    def test_repeated_eid_attributes_are_preserved_as_lists(self):
        xml = b"""
        <cas:serviceResponse xmlns:cas="https://ecas.ec.europa.eu/cas/schemas">
          <cas:authenticationSuccess>
            <cas:user>ecas-id-1</cas:user>
            <cas:attributes>
              <cas:moniker>user.one</cas:moniker>
              <cas:authenticationLevel>STRONG</cas:authenticationLevel>
              <cas:storkId>STORK-1</cas:storkId>
              <cas:storkId>STORK-2</cas:storkId>
            </cas:attributes>
          </cas:authenticationSuccess>
        </cas:serviceResponse>
        """
        user, attributes, pgtiou = self.plugin._parse_validation_response(xml)

        self.assertEqual(user, "ecas-id-1")
        self.assertEqual(attributes["storkId"], ["STORK-1", "STORK-2"])
        self.assertIsNone(pgtiou)

    def test_extract_credentials_uses_request_session_and_is_pickle_safe(self):
        session = ZopeBeakerSessionWrapper(DummySession())
        request = DummyRequest(session=session, ticket="ST-1")
        assertion = ReportekCASAssertion(
            ReportekCASPrincipal(
                "user.one",
                ecas_id="ecas-unique-id",
                meta={"email": "user.one@example.org"},
                plugin=self.plugin,
            )
        )
        self.plugin.validateServiceTicket = lambda service, ticket: assertion

        credentials = self.plugin.extractCredentials(request)

        self.assertEqual(credentials["login"], "ecas-unique-id")
        self.assertEqual(credentials["display_name"], "user.one@example.org")
        stored = session.get(self.plugin.CAS_ASSERTION)
        self.assertIsInstance(stored, ReportekCASAssertion)
        pickle.dumps(dict(session.items()))

    def test_minimum_authentication_level_defaults_to_basic(self):
        self.assertEqual(self.plugin.minimumAuthenticationLevel, "BASIC")
        self.assertIn("BASIC =", self.plugin.authenticationLevelGuide)
        self.assertIn("MEDIUM =", self.plugin.authenticationLevelGuide)
        self.assertIn("HIGH =", self.plugin.authenticationLevelGuide)
        self.plugin._validateAuthenticationLevel({"authenticationLevel": "BASIC"})
        self.plugin._validateAuthenticationLevel({"authenticationLevel": "MEDIUM"})
        self.plugin._validateAuthenticationLevel({"authenticationLevel": "HIGH"})

    def test_minimum_authentication_level_can_require_medium(self):
        self.plugin.minimumAuthenticationLevel = "MEDIUM"
        self.plugin._validateAuthenticationLevel({"authenticationLevel": "MEDIUM"})
        self.plugin._validateAuthenticationLevel({"authenticationLevel": "HIGH"})
        with self.assertRaises(ValueError):
            self.plugin._validateAuthenticationLevel({"authenticationLevel": "BASIC"})

    def test_minimum_authentication_level_can_require_high(self):
        self.plugin.minimumAuthenticationLevel = "HIGH"
        self.plugin._validateAuthenticationLevel({"authenticationLevel": "HIGH"})
        with self.assertRaises(ValueError):
            self.plugin._validateAuthenticationLevel({"authenticationLevel": "MEDIUM"})

    def test_minimum_authentication_level_rejects_missing_level(self):
        with self.assertRaises(ValueError):
            self.plugin._validateAuthenticationLevel({})

    def test_login_identifier_defaults_to_ecas_unique_id(self):
        principal = ReportekCASPrincipal(
            "user.one",
            ecas_id="ecas-unique-id",
            meta={"email": "user.one@example.org", "uid": "ecas-unique-id"},
        )
        self.assertEqual(self.plugin._getLoginFromPrincipal(principal), "ecas-unique-id")

    def test_authenticate_credentials_returns_display_name(self):
        credentials = {"extractor": "eCas", "login": "ecas-unique-id", "display_name": "user.one@example.org"}
        self.assertEqual(
            self.plugin.authenticateCredentials(credentials),
            ("ecas-unique-id", "user.one@example.org"),
        )

    def test_display_identifier_defaults_to_email(self):
        principal = ReportekCASPrincipal(
            "user.one",
            ecas_id="ecas-unique-id",
            meta={"email": "user.one@example.org"},
        )
        self.assertEqual(self.plugin._getDisplayNameFromPrincipal(principal), "user.one@example.org")

    def test_display_identifier_uses_email_like_moniker_when_email_missing(self):
        principal = ReportekCASPrincipal(
            "user.one@example.org",
            ecas_id="ecas-unique-id",
            meta={"moniker": "user.one@example.org"},
        )
        self.assertEqual(self.plugin._getDisplayNameFromPrincipal(principal), "user.one@example.org")

    def test_display_identifier_can_use_ecas_id(self):
        self.plugin.displayIdentifier = "ecas_id"
        principal = ReportekCASPrincipal(
            "user.one",
            ecas_id="ecas-unique-id",
            meta={"email": "user.one@example.org"},
        )
        self.assertEqual(self.plugin._getDisplayNameFromPrincipal(principal), "ecas-unique-id")

    def test_login_identifier_can_use_email(self):
        self.plugin.loginIdentifier = "email"
        principal = ReportekCASPrincipal(
            "user.one",
            ecas_id="ecas-unique-id",
            meta={"email": "user.one@example.org"},
        )
        self.assertEqual(self.plugin._getLoginFromPrincipal(principal), "user.one@example.org")

    def test_login_identifier_can_use_moniker_for_legacy_compatibility(self):
        self.plugin.loginIdentifier = "moniker"
        principal = ReportekCASPrincipal(
            "user.one",
            ecas_id="ecas-unique-id",
            meta={"email": "user.one@example.org"},
        )
        self.assertEqual(self.plugin._getLoginFromPrincipal(principal), "user.one")

    def test_extractor_is_noop_outside_bdr(self):
        with patch("Products.Reportek.ReportekCASPlugin.REPORTEK_DEPLOYMENT", config.DEPLOYMENT_CDR):
            result = self.plugin.extractCredentials(DummyRequest(session=DummySession(), ticket="ST-1"))
        self.assertIsNone(result)

    def test_challenge_is_noop_outside_bdr(self):
        response = DummyResponse()
        with patch("Products.Reportek.ReportekCASPlugin.REPORTEK_DEPLOYMENT", config.DEPLOYMENT_CDR):
            result = self.plugin.challenge(DummyRequest(session=DummySession()), response)
        self.assertEqual(result, 0)
        self.assertIsNone(response.redirect_url)

    def test_runtime_cache_does_not_write_persistent_plugin_mappings(self):
        self.plugin._redisClient = lambda: None
        self.plugin._addSession("ST-1", "session-1")
        self.plugin.proxyCallback("PGT-1", "PGTIOU-1")
        self.assertEqual(len(self.plugin._sessionStorage), 0)
        self.assertEqual(len(self.plugin._pgtStorage), 0)
        self.assertEqual(self.plugin._getSessionId("ST-1"), "session-1")
        self.assertEqual(self.plugin._cacheGet("pgt", "PGTIOU-1"), "PGT-1")

    def test_logout_revokes_beaker_session_by_session_index(self):
        self.plugin._redisClient = lambda: None
        session = DummySession()
        assertion = ReportekCASAssertion(ReportekCASPrincipal("user.one"))
        session.set(self.plugin.CAS_ASSERTION, assertion)
        self.plugin._addSession("ST-logout", session.getId())

        xml = """
        <samlp:LogoutRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">
          <samlp:SessionIndex>ST-logout</samlp:SessionIndex>
        </samlp:LogoutRequest>
        """
        self.assertEqual(self.plugin.logoutCallback(xml), "Logout success.")
        self.assertIsNone(self.plugin.getAssertion(session))
        self.assertTrue(session.cleared)


class TestReportekCASImport(unittest.TestCase):
    def test_legacy_anz_ecas_sets_lax_validate_endpoint(self):
        plugin = ReportekCASPlugin("eCas")
        _set_plugin_properties(
            plugin,
            {"ticketValidationSpecification": "CAS 2.0"},
            {"class": "anz.ecasclient.ecasclient.AnzECASClient"},
        )
        self.assertEqual(plugin.ticketValidationSpecification, "CAS 2.0")
        self.assertEqual(plugin.serviceValidationEndpoint, "laxValidate")


if __name__ == "__main__":
    unittest.main()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestReportekCASPlugin))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestReportekCASImport))
    return suite
