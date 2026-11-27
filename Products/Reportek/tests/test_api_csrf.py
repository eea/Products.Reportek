"""The registry API (BDR) and the LDAP role views: requests from the
registries keep working exactly as they are sent today, requests from a
browser need plone.protect's form token."""

import base64
import io
import json
from unittest.mock import Mock, patch
from urllib.parse import urlencode

import plone.protect.interfaces
from plone.protect.authenticator import createToken
from plone.protect.utils import getRootKeyManager
from zExceptions import Forbidden
from zope.globalrequest import setRequest
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse

from Products.Reportek.api.csrf import is_service_request
from Products.Reportek.api.org_collections import OrgCollections
from Products.Reportek.api.roles import RolesMGMTAPI
from Products.Reportek.ldap_group_roles import (
    AssignRoleToPrincipalView,
    LDAPGroupRolesPlugin,
)

from .common import BaseTest

CREDENTIALS = b"api_user:api_password"  # betterleaks:allow (test fixture)
BASIC = "Basic " + base64.b64encode(CREDENTIALS).decode()
# what browsers add to a request another site makes them send
CROSS_SITE = {
    "HTTP_ORIGIN": "https://elsewhere.example",
    "HTTP_SEC_FETCH_SITE": "cross-site",
}

ORG_FORM = {
    "country_code": "de",
    "obligation_folder_name": "no_such_obligation",
    "account_uid": "company1",
    "organisation_name": "Company 1",
}
OWNERSHIP = {
    "uid": "company_user",
    "obl_folder": "obl",
    "country": "de",
    "c_folder": "company1",
    "action": "add",
}


class CSRFTestBase(BaseTest):
    def afterSetUp(self):
        super().afterSetUp()
        getRootKeyManager(self.app)

    def request(self, method="GET", auth=BASIC, form=None, body=None, **environ):
        """A request as Zope builds it from what the client sends."""
        env = {
            "SERVER_NAME": "nohost",
            "SERVER_PORT": "80",
            "REQUEST_METHOD": method,
        }
        if auth:
            env["HTTP_AUTHORIZATION"] = auth
        data = b""
        if body is not None:
            data = body.encode()
        elif form is not None:
            if method == "GET":
                env["QUERY_STRING"] = urlencode(form)
            else:
                data = urlencode(form).encode()
                env.setdefault("CONTENT_TYPE", "application/x-www-form-urlencoded")
        env["CONTENT_LENGTH"] = str(len(data))
        env.update(environ)
        request = HTTPRequest(io.BytesIO(data), env, HTTPResponse())
        request.processInputs()
        request["PARENTS"] = [self.app]
        setRequest(request)
        self.addCleanup(setRequest, None)
        return request

    def token(self):
        return createToken()

    def assertExempt(self, request, exempt=True):
        provided = plone.protect.interfaces.IDisableCSRFProtection.providedBy(request)
        self.assertEqual(provided, exempt)


class ServiceRequestTest(CSRFTestBase):
    def test_basic_auth_without_browser_headers(self):
        self.assertTrue(is_service_request(self.request("POST")))

    def test_browser_requests_are_not_services(self):
        for header in CROSS_SITE:
            request = self.request("POST", **{header: CROSS_SITE[header]})
            self.assertFalse(is_service_request(request), header)
        # a request typed in the address bar
        request = self.request("GET", HTTP_SEC_FETCH_SITE="none")
        self.assertFalse(is_service_request(request))

    def test_other_authentication_is_not_a_service(self):
        self.assertFalse(is_service_request(self.request("POST", auth=None)))
        self.assertFalse(is_service_request(self.request("POST", auth="Bearer x")))


class CreateOrganisationFolderTest(CSRFTestBase):
    def call(self, request):
        return json.loads(
            OrgCollections(self.app, request).create_organisation_folder()
        )

    def test_bdr_registry_request(self):
        # requests.post(url, data=form, auth=BDR_API_AUTH)
        request = self.request("POST", form=ORG_FORM)
        result = self.call(request)
        # past the checks, into the work itself
        self.assertEqual(
            result, {"success": False, "error": "obligation folder missing"}
        )
        self.assertEqual(request.RESPONSE.getStatus(), 200)
        self.assertExempt(request)

    def test_get_is_refused(self):
        request = self.request("GET", form=ORG_FORM)
        result = self.call(request)
        self.assertEqual(request.RESPONSE.getStatus(), 405)
        self.assertFalse(result["success"])

    def test_browser_post_needs_the_token(self):
        request = self.request("POST", form=ORG_FORM, **CROSS_SITE)
        with self.assertRaises(Forbidden):
            self.call(request)
        self.assertExempt(request, False)

    def test_browser_post_with_the_token(self):
        form = dict(ORG_FORM, _authenticator=self.token())
        request = self.request("POST", form=form, **CROSS_SITE)
        self.assertEqual(self.call(request)["error"], "obligation folder missing")


class UpdateOrganisationNameTest(CSRFTestBase):
    def call(self, request):
        return json.loads(OrgCollections(self.app, request).update_organisation_name())

    def test_cache_registry_request(self):
        # requests.get(url, params=params, auth=auth)
        form = dict(ORG_FORM, oldcompany_account="")
        request = self.request("GET", form=form)
        self.assertEqual(self.call(request), {"updated": False})
        self.assertEqual(request.RESPONSE.getStatus(), 200)
        self.assertExempt(request)

    def test_bdr_registry_request(self):
        # requests.post(url, data=form, auth=BDR_API_AUTH)
        request = self.request("POST", form=ORG_FORM)
        self.assertEqual(self.call(request), {"updated": False})
        self.assertExempt(request)

    def test_renames_the_collection(self):
        self.app.manage_addFolder("obl")
        self.app.obl.manage_addFolder("de")
        self.app.obl.de.manage_addFolder("company1", title="Old name")
        company = self.app.obl.de.company1
        company.manage_changeCollection = Mock()
        form = dict(ORG_FORM, obligation_folder_name="obl", oldcompany_account="")
        result = self.call(self.request("GET", form=form))
        self.assertEqual(result, {"updated": True})
        company.manage_changeCollection.assert_called_once_with(title="Company 1")

    def test_browser_get_needs_the_token(self):
        request = self.request("GET", form=ORG_FORM, **CROSS_SITE)
        with self.assertRaises(Forbidden):
            self.call(request)


class ManageOwnershipTest(CSRFTestBase):
    def call(self, request):
        view = RolesMGMTAPI(self.app, request)
        with patch.object(RolesMGMTAPI, "add_owner") as add_owner:
            result = view.manage_ownership()
        return result, add_owner

    def test_bdr_registry_request(self):
        # requests.post(url, data=json.dumps(form), auth=BDR_API_AUTH,
        #               headers={"Content-type": "application/json"})
        self.app.acl_users.userFolderAddUser("company_user", "x", [], [])
        self.app.manage_addFolder("obl")
        self.app.obl.manage_addFolder("de")
        self.app.obl.de.manage_addFolder("company1")
        request = self.request(
            "POST", body=json.dumps(OWNERSHIP), CONTENT_TYPE="application/json"
        )
        result, add_owner = self.call(request)
        self.assertEqual(
            json.loads(result), {"message": "Operation completed", "errors": []}
        )
        add_owner.assert_called_once()
        self.assertExempt(request)

    def test_json_with_a_charset(self):
        request = self.request(
            "POST",
            body=json.dumps({}),
            CONTENT_TYPE="application/json; charset=utf-8",
        )
        self.call(request)
        # not refused for its type: the empty data makes it a bad request
        self.assertEqual(request.RESPONSE.getStatus(), 400)

    def test_other_content_types_are_refused(self):
        # what a form on another site can send without asking first
        for content_type in (
            "text/plain",
            "application/x-www-form-urlencoded",
        ):
            request = self.request(
                "POST", body=json.dumps(OWNERSHIP), CONTENT_TYPE=content_type
            )
            result, add_owner = self.call(request)
            self.assertEqual(request.RESPONSE.getStatus(), 415, content_type)
            add_owner.assert_not_called()

    def test_browser_post_needs_the_token(self):
        request = self.request(
            "POST",
            body=json.dumps(OWNERSHIP),
            CONTENT_TYPE="application/json",
            **CROSS_SITE,
        )
        with self.assertRaises(Forbidden):
            self.call(request)


class LDAPRoleViewsTest(CSRFTestBase):
    def afterSetUp(self):
        super().afterSetUp()
        from Products.PluggableAuthService.plugins.ZODBRoleManager import (
            addZODBRoleManager,
        )
        from OFS.Folder import Folder

        acl = Folder("acl")
        self.app._setObject("acl", acl)
        acl = self.app.acl
        acl.searchPrincipals = lambda **kw: ()
        addZODBRoleManager(acl, "roles")
        acl._setObject("ldap_group_roles", LDAPGroupRolesPlugin())
        self.acl = acl
        self.plugin = acl.ldap_group_roles

    def assign(self, **form):
        form.update(role_id="Reporter", principal_id="someone")
        request = self.request("POST", auth=None, form=form)
        return AssignRoleToPrincipalView(self.plugin, request)()

    def assigned(self):
        roles = self.acl.roles
        return "Reporter" in roles.listRoleIds() and [
            p for p, _ in roles.listAssignedPrincipals("Reporter")
        ] == ["someone"]

    def test_without_the_token_nothing_changes(self):
        with self.assertRaises(Forbidden):
            self.assign()
        self.assertFalse(self.assigned())

    def test_the_forms_token_lets_it_through(self):
        self.assign(_authenticator=self.token())
        self.assertTrue(self.assigned())


class ForbiddenErrorPageTest(CSRFTestBase):
    def test_json_clients_get_403(self):
        from Products.Reportek.errors import ErrorView

        request = self.request("POST", HTTP_ACCEPT="application/json")
        view = ErrorView()
        view.context = Forbidden("Form authenticator is invalid.")
        view.request = request
        body = json.loads(view())
        self.assertEqual(request.response.getStatus(), 403)
        self.assertEqual(body["errors"][0]["title"], "Forbidden")
