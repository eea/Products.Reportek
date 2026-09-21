# -*- coding: utf-8 -*-
"""Tests for the FME Flow API v4 support of RemoteFMEConversionApplication"""

import json
from io import BytesIO
from unittest.mock import Mock, patch

from AccessControl import Unauthorized
from AccessControl.SecurityManagement import newSecurityManager, noSecurityManager
from AccessControl.users import SimpleUser
from AccessControl.ZopeGuards import guarded_getattr
from DateTime import DateTime
from OFS.Folder import Folder

from Products.Reportek.RemoteFMEConversionApplication import (
    RemoteFMEConversionApplication,
)

from .common import BaseUnitTest

WKS_PARAMS_V4 = "{{'publishedParameters': {{'inputfile': '{GET_FILE}'}}}}"
WKS_PARAMS_V3 = (
    "{{'publishedParameters': [{{'name': 'inputfile', 'value': '{GET_FILE}'}}]}}"
)


class FakeWorkitem(object):
    """Minimal workitem: the application stores its state on it"""

    def __init__(self, app_name, storage, env):
        setattr(self, app_name, storage)
        self.env = env
        self.events = []
        self.activity_id = "FMEConversion"
        self.id = "workitem"
        self.failure = False
        self._p_changed = 0

    def addEvent(self, message):
        self.events.append(message)

    def getMySelf(self):
        return self.env


class FMEConversionApplicationV4Test(BaseUnitTest):
    def _make_app(self, api_version="v4", wks_params=WKS_PARAMS_V4):
        app = RemoteFMEConversionApplication(
            "fme",
            "",
            "https://fme.example",
            "",
            "a-token",
            "",
            "",
            "",
            "minute",
            "fmerest/v3/resources/connections/FME_SHAREDRESOURCE_TEMP",
            "convdir",
            "fmerest/v3/transformations/submit",
            None,
            "gml",
            False,
            "conversions/convert.fmw",
            wks_params,
            True,
            300,
            "fme_app",
            nRetries=5,
            FMEApiVersion=api_version,
            FMEApiEndpoint="fmeapiv4",
            FMEResourceConnection="FME_SHAREDRESOURCE_TEMP",
            FMERepository="conversions",
        )
        env = Mock()
        env.getPhysicalPath.return_value = ("", "cdr", "env")
        env.objectIds.return_value = []
        env.dataflow_uris = ["http://rod.eionet.europa.eu/obligations/780"]
        workitem = FakeWorkitem(
            "fme_app",
            {
                "upload": {
                    "retries_left": 5,
                    "last_error": None,
                    "next_run": DateTime(),
                    "status": "pending",
                    "paths": ["file.gml"],
                },
                "fmw_exec": {
                    "retries_left": 5,
                    "last_error": None,
                    "next_run": DateTime(),
                    "status": "pending",
                },
                "results": {},
                "cleanup": {
                    "retries_left": 5,
                    "last_error": None,
                    "next_run": DateTime(),
                    "status": "pending",
                },
            },
            env,
        )
        setattr(app, "workitem", workitem)
        return app, workitem, env

    # ------------------------------------------------------------- upload
    def _upload(self, app):
        doc = Mock()
        doc.title_or_id.return_value = "file.gml"
        doc.data_file.open.return_value = BytesIO(b"gml")
        app.get_files = Mock(return_value=[doc])
        response = Mock(status_code=200, content=b"")
        response.json.side_effect = ValueError("no body")
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=response,
        ) as post:
            app.upload_to_fme("workitem")
        return post

    def test_v4_upload_targets_the_resource_connection(self):
        app, workitem, _env = self._make_app()

        post = self._upload(app)

        url = post.call_args[0][0]
        self.assertEqual(
            url,
            "https://fme.example/fmeapiv4/resources/connections/"
            "FME_SHAREDRESOURCE_TEMP/upload",
        )
        self.assertEqual(
            post.call_args[1]["params"],
            {"path": "/convdir/cdr_env", "overwrite": "true"},
        )
        upload = getattr(workitem, "fme_app")["upload"]
        self.assertEqual(upload["status"], "completed")
        # v4 doesn't guarantee a response body, fall back on what we sent
        self.assertEqual(upload["paths"], ["file.gml"])

    def test_v3_upload_keeps_the_legacy_path(self):
        app, _workitem, _env = self._make_app(api_version="v3")

        post = self._upload(app)

        self.assertEqual(
            post.call_args[0][0],
            "https://fme.example/fmerest/v3/resources/connections/"
            "FME_SHAREDRESOURCE_TEMP/filesys/convdir/cdr_env",
        )

    def test_v4_upload_reports_partial_upload_as_error(self):
        app, workitem, _env = self._make_app()
        doc = Mock()
        doc.title_or_id.return_value = "file.gml"
        doc.data_file.open.return_value = BytesIO(b"gml")
        app.get_files = Mock(return_value=[doc])
        response = Mock(status_code=207, content=b"partial failure")
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=response,
        ):
            app.upload_to_fme("workitem")

        upload = getattr(workitem, "fme_app")["upload"]
        self.assertEqual(upload["status"], "pending")
        self.assertEqual(upload["retries_left"], 4)
        self.assertIn("207", upload["last_error"])

    def test_missing_resource_connection_is_reported(self):
        app, workitem, _env = self._make_app()
        app.FMEResourceConnection = ""
        doc = Mock()
        doc.title_or_id.return_value = "file.gml"
        doc.data_file.open.return_value = BytesIO(b"gml")
        app.get_files = Mock(return_value=[doc])

        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post"
        ) as post:
            app.upload_to_fme("workitem")

        post.assert_not_called()
        upload = getattr(workitem, "fme_app")["upload"]
        self.assertIn("resource connection", upload["last_error"])

    # ------------------------------------------------------- job submission
    def test_v4_job_is_submitted_with_repository_and_workspace(self):
        app, workitem, _env = self._make_app()
        response = Mock(status_code=202)
        response.json.return_value = {"id": 42}
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=response,
        ) as post:
            app.execute_workspace("workitem")

        self.assertEqual(post.call_args[0][0], "https://fme.example/fmeapiv4/jobs")
        payload = json.loads(post.call_args[1]["data"])
        self.assertEqual(
            payload,
            {
                "repository": "conversions",
                "workspace": "convert.fmw",
                "publishedParameters": {"inputfile": "file.gml"},
            },
        )
        results = getattr(workitem, "fme_app")["results"]
        self.assertEqual(results[42]["inputfile"], "file.gml")

    def test_v3_job_keeps_the_transformation_url(self):
        app, _workitem, _env = self._make_app(
            api_version="v3", wks_params=WKS_PARAMS_V3
        )
        response = Mock(status_code=202)
        response.json.return_value = {"id": 42}
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=response,
        ) as post:
            app.execute_workspace("workitem")

        self.assertEqual(
            post.call_args[0][0],
            "https://fme.example/fmerest/v3/transformations/submit/"
            "conversions/convert.fmw",
        )

    def test_a_broken_template_names_the_usual_cause(self):
        app, workitem, _env = self._make_app(
            wks_params="{{'publishedParameters': {{'inputfile': '{GET_FILE}',}}}}"
        )

        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post"
        ) as post:
            app.execute_workspace("workitem")

        post.assert_not_called()
        last_error = getattr(workitem, "fme_app")["fmw_exec"]["last_error"]
        self.assertIn("not valid JSON", last_error)
        self.assertIn("trailing comma", last_error)

    def test_v4_rejects_v3_shaped_published_parameters(self):
        app, workitem, _env = self._make_app(wks_params=WKS_PARAMS_V3)

        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post"
        ) as post:
            app.execute_workspace("workitem")

        post.assert_not_called()
        fmw_exec = getattr(workitem, "fme_app")["fmw_exec"]
        self.assertEqual(fmw_exec["status"], "retry")
        self.assertIn("publishedParameters", fmw_exec["last_error"])

    # ------------------------------------------------------------- polling
    def _job_state(self, app, payload, status_code=200):
        response = Mock(status_code=status_code)
        response.json.return_value = payload
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.get",
            return_value=response,
        ) as get:
            state = app.get_job_state("workitem", 42)
        return state, get

    def test_v4_job_statuses_are_mapped(self):
        app, _workitem, _env = self._make_app()

        (state, _status), get = self._job_state(app, {"status": "success"})
        self.assertEqual(state, "success")
        self.assertEqual(get.call_args[0][0], "https://fme.example/fmeapiv4/jobs/42")

        for running in ("queued", "running"):
            (state, _status), _get = self._job_state(app, {"status": running})
            self.assertEqual(state, "retry")

        (state, status), _get = self._job_state(
            app, {"status": "failure", "statusMessage": "boom"}
        )
        self.assertEqual(state, "abort")
        self.assertIn("boom", status)

        (state, _status), _get = self._job_state(app, {"status": "cancelled"})
        self.assertEqual(state, "abort")

    def test_job_state_retries_on_http_error(self):
        app, _workitem, _env = self._make_app()

        (state, status), _get = self._job_state(app, {}, status_code=503)

        self.assertEqual(state, "retry")
        self.assertIn("503", status)

    def test_job_state_retries_on_unexpected_status_code(self):
        app, _workitem, _env = self._make_app()

        (state, status), _get = self._job_state(app, {"id": 42}, status_code=202)

        self.assertEqual(state, "retry")
        self.assertIn("202", status)

    def test_v3_job_statuses_are_mapped(self):
        app, _workitem, _env = self._make_app(api_version="v3")

        (state, _status), get = self._job_state(
            app, {"status": "SUCCESS", "result": {"status": "SUCCESS"}}
        )
        self.assertEqual(state, "success")
        self.assertEqual(
            get.call_args[0][0],
            "https://fme.example/fmerest/v3/transformations/jobs/id/42",
        )

        (state, _status), _get = self._job_state(app, {"status": "FME_FAILURE"})
        self.assertEqual(state, "abort")

    # ------------------------------------------------------------ download
    def test_v4_downloadzip_lists_the_output_folder(self):
        app, _workitem, env = self._make_app()
        env.manage_addDDzipfile.side_effect = lambda file, verbose: (
            1,
            "zip added",
        )
        info = Mock(status_code=200)
        info.json.return_value = {
            "contents": [
                {"name": "result.gml", "type": "file"},
                {"name": "conversion_log.html", "type": "file"},
            ]
        }
        download = Mock(status_code=200, content=b"zip-bytes")
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.get",
            return_value=info,
        ) as get, patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=download,
        ) as post:
            result = app.handle_res_zip_download("workitem")

        self.assertEqual(result, (1, "zip added"))
        self.assertEqual(
            get.call_args[0][0],
            "https://fme.example/fmeapiv4/resources/connections/"
            "FME_SHAREDRESOURCE_TEMP/info",
        )
        self.assertEqual(
            get.call_args[1]["params"], {"path": "/convdir/cdr_env/output"}
        )
        self.assertEqual(
            post.call_args[0][0],
            "https://fme.example/fmeapiv4/resources/connections/"
            "FME_SHAREDRESOURCE_TEMP/downloadzip",
        )
        self.assertEqual(
            json.loads(post.call_args[1]["data"]),
            {
                "path": "/convdir/cdr_env/output",
                "items": ["result.gml", "conversion_log.html"],
                "zipFileName": "resources.zip",
            },
        )

    def test_v4_downloadzip_without_results(self):
        app, _workitem, _env = self._make_app()
        info = Mock(status_code=200)
        info.json.return_value = {"contents": []}
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.get",
            return_value=info,
        ), patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post"
        ) as post:
            result = app.handle_res_zip_download("workitem")

        post.assert_not_called()
        self.assertEqual(result[0], 404)
        self.assertIn("/convdir/cdr_env/output", result[1])

    def test_v4_downloadzip_reports_a_failed_listing(self):
        app, _workitem, _env = self._make_app()
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.get",
            return_value=Mock(status_code=403),
        ), patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post"
        ) as post:
            result = app.handle_res_zip_download("workitem")

        post.assert_not_called()
        self.assertEqual(result[0], 403)
        self.assertIn("Unable to list", result[1])

    # ------------------------------------------------------------- cleanup
    def test_v4_cleanup_deletes_the_envelope_folder(self):
        app, workitem, _env = self._make_app()
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.delete",
            return_value=Mock(status_code=204),
        ) as delete:
            app.handle_cleanup("workitem")

        self.assertEqual(
            delete.call_args[0][0],
            "https://fme.example/fmeapiv4/resources/connections/"
            "FME_SHAREDRESOURCE_TEMP/item",
        )
        self.assertEqual(delete.call_args[1]["params"], {"path": "/convdir/cdr_env"})
        self.assertEqual(getattr(workitem, "fme_app")["cleanup"]["status"], "completed")

    # -------------------------------------------------------- cancellation
    def test_v4_cancel_job(self):
        app, _workitem, _env = self._make_app()
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=Mock(status_code=204),
        ) as post:
            res = app.cancel_job(42, "workitem")

        self.assertEqual(res.status_code, 204)
        self.assertEqual(
            post.call_args[0][0], "https://fme.example/fmeapiv4/jobs/42/cancel"
        )

    def test_v3_cancel_job_falls_back_to_running_jobs(self):
        app, _workitem, _env = self._make_app(api_version="v3")
        responses = [Mock(status_code=404), Mock(status_code=204)]
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.delete",
            side_effect=responses,
        ) as delete:
            res = app.cancel_job(42, "workitem")

        self.assertEqual(res.status_code, 204)
        self.assertEqual(
            [call[0][0] for call in delete.call_args_list],
            [
                "https://fme.example/fmerest/v3/transformations/jobs/queued/42",
                "https://fme.example/fmerest/v3/transformations/jobs/running/42",
            ],
        )

    # ----------------------------------------------------------- token/auth
    def test_token_is_parsed_from_the_service_response(self):
        app, _workitem, _env = self._make_app()
        app.FMEToken = None
        app.FMEUser = "user"
        app.FMEPassword = "pass"
        app.FMETokenExpiration = "60"
        response = Mock(ok=True, content=b'{"serviceResponse": {"token": "tok"}}')
        response.json.return_value = {"serviceResponse": {"token": "tok"}}
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=response,
        ) as post:
            token = app.get_fme_token()

        self.assertEqual(token["token"], "tok")
        self.assertEqual(
            post.call_args[0][0], "https://fme.example/fmetoken/generate.json"
        )

    def test_plain_text_token_is_decoded(self):
        app, _workitem, _env = self._make_app()
        app.FMEToken = None
        app.FMETokenExpiration = "60"
        response = Mock(ok=True, content=b"plain-token\n")
        response.json.side_effect = ValueError("not json")
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=response,
        ):
            token = app.get_fme_token()

        self.assertEqual(token["token"], "plain-token")

    def test_auth_header_carries_a_text_token(self):
        app, _workitem, _env = self._make_app()
        app.FMEToken = b"bytes-token"

        self.assertEqual(
            app.get_auth_header("workitem"),
            {"Authorization": "fmetoken token=bytes-token"},
        )


class FMEConversionApplicationSecurityTest(BaseUnitTest):
    """The application drives conversions; none of that may be published."""

    PRIVATE = [
        "get_fme_token",
        "get_token",
        "get_auth_header",
        "get_headers",
        "get_request_timeout",
        "get_api_root",
        "get_resource_url",
        "get_resource_items",
        "upload_to_fme",
        "execute_workspace",
        "get_job_state",
        "poll_results",
        "handle_cleanup",
        "handle_res_zip_download",
        "cancel_job",
        "delete_job",
    ]

    def test_internals_are_not_web_accessible(self):
        for name in self.PRIVATE:
            roles = getattr(
                RemoteFMEConversionApplication, name + "__roles__", "ABSENT"
            )
            self.assertEqual(
                roles, (), "%s is reachable through the publisher (%r)" % (name, roles)
            )

    def test_management_screens_need_a_permission(self):
        for name, permission in (
            ("manage_settings", "_View_management_screens_Permission"),
            ("manage_settings_html", "_View_management_screens_Permission"),
            ("has_secret", "_View_management_screens_Permission"),
            ("index_html", "_View_configuration_Permission"),
            ("is_v4", "_View_configuration_Permission"),
        ):
            roles = getattr(RemoteFMEConversionApplication, name + "__roles__", None)
            self.assertEqual(getattr(roles, "_p", None), permission, name)

    def test_the_object_stays_reachable(self):
        """The envelope traverses to the application as the reporter.

        A reporter holds its role locally on its own collection, never on
        /Applications, so protecting the object itself locks the workflow out
        with "You are not allowed to access FMEConversionApplication".
        """
        self.assertEqual(
            getattr(RemoteFMEConversionApplication, "__roles__", "ABSENT"), "ABSENT"
        )

    def test_a_plain_authenticated_user_can_traverse_to_it(self):
        folder = Folder("f")
        app = self._make_app()
        folder._setObject("fme", app)
        newSecurityManager(None, SimpleUser("rep", "", ["Authenticated"], []))
        try:
            guarded_getattr(folder, "fme")
        finally:
            noSecurityManager()

    def test_configuration_attributes_carry_no_permission(self):
        """Protecting a plain value denies everybody, Managers included.

        AccessControl validates the acquisition context of the value, and a
        string has none, so `declareProtected` on a data attribute locks out
        every user whose account lives in a user folder.
        """
        for name in RemoteFMEConversionApplication.PROTECTED_ATTRIBUTES:
            self.assertEqual(
                getattr(RemoteFMEConversionApplication, name + "__roles__", "ABSENT"),
                "ABSENT",
                "%s is permission protected, which denies every real user" % name,
            )

    def test_the_configuration_is_denied_to_restricted_code(self):
        app = self._make_app()
        for name in RemoteFMEConversionApplication.PROTECTED_ATTRIBUTES:
            self.assertFalse(
                app.__allow_access_to_unprotected_subobjects__(name),
                "%s is readable through the publisher" % name,
            )
        for name in ("title", "id", "meta_type"):
            self.assertTrue(app.__allow_access_to_unprotected_subobjects__(name))

    def test_nobody_reads_the_configuration_off_the_object(self):
        folder = Folder("f")
        app = self._make_app()
        folder._setObject("fme", app)
        for user in (
            SimpleUser("anon", "", ["Anonymous"], []),
            SimpleUser("rep", "", ["Authenticated"], []),
            SimpleUser("boss", "", ["Manager"], []),
        ):
            newSecurityManager(None, user)
            try:
                for name in (
                    "FMEPassword",
                    "FMEToken",
                    "FMEServer",
                    "FMEWorkspaceParams",
                ) + tuple(self.PRIVATE):
                    with self.assertRaises(
                        Unauthorized,
                        msg="%s is readable by %s" % (name, user.getUserName()),
                    ):
                        guarded_getattr(folder.fme, name)
            finally:
                noSecurityManager()

    def test_a_manager_reads_the_configuration_through_the_accessor(self):
        folder = Folder("f")
        app = self._make_app()
        folder._setObject("fme", app)
        newSecurityManager(None, SimpleUser("boss", "", ["Manager"], []))
        try:
            for name in ("get_settings", "has_secret", "is_v4"):
                guarded_getattr(folder.fme, name)
            settings = folder.fme.get_settings()
        finally:
            noSecurityManager()

        self.assertEqual(settings["FMEServer"], "https://fme.example")
        for name in RemoteFMEConversionApplication.SENSITIVE_ATTRIBUTES:
            self.assertNotIn(name, settings)

    def test_a_reporter_cannot_use_the_accessor(self):
        folder = Folder("f")
        app = self._make_app()
        folder._setObject("fme", app)
        newSecurityManager(None, SimpleUser("rep", "", ["Authenticated"], []))
        try:
            with self.assertRaises(Unauthorized):
                guarded_getattr(folder.fme, "get_settings")
        finally:
            noSecurityManager()

    def _make_app(self):
        return RemoteFMEConversionApplication(
            "fme",
            "",
            "https://fme.example",
            "",
            "a-token",
            "user",
            "secret",
            "",
            "minute",
            "up",
            "dir",
            "tr",
            None,
            "gml",
            False,
            "w.fmw",
            None,
            True,
            300,
            "fme_app",
        )


class FMEConversionApplicationTimeoutTest(BaseUnitTest):
    def _app(self, connect=10, read=300):
        app = RemoteFMEConversionApplication(
            "fme",
            "",
            "https://fme.example",
            "",
            "a-token",
            "",
            "",
            "",
            "minute",
            "up",
            "convdir",
            "tr",
            None,
            "gml",
            False,
            "conversions/convert.fmw",
            None,
            True,
            300,
            "fme_app",
            nRetries=5,
            FMEApiVersion="v4",
            FMEApiEndpoint="fmeapiv4",
            FMEResourceConnection="CONN",
            FMERepository="conversions",
            FMEConnectTimeout=connect,
            FMEReadTimeout=read,
        )
        env = Mock()
        env.getPhysicalPath.return_value = ("", "cdr", "env")
        workitem = Mock()
        workitem.getMySelf.return_value = env
        setattr(app, "workitem", workitem)
        return app

    def test_timeout_defaults_to_connect_and_read(self):
        self.assertEqual(self._app().get_request_timeout(), (10.0, 300.0))

    def test_timeout_accepts_strings_from_the_settings_form(self):
        self.assertEqual(self._app("5", "120").get_request_timeout(), (5.0, 120.0))

    def test_empty_or_zero_timeout_disables_it(self):
        self.assertEqual(self._app("", "60").get_request_timeout(), (None, 60.0))
        self.assertIsNone(self._app("", "").get_request_timeout())
        self.assertIsNone(self._app(0, 0).get_request_timeout())

    def test_requests_carry_the_timeout(self):
        app = self._app("5", "120")
        response = Mock(status_code=200)
        response.json.return_value = {"status": "success"}
        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.get",
            return_value=response,
        ) as get:
            app.get_job_state("workitem", 42)

        self.assertEqual(get.call_args[1]["timeout"], (5.0, 120.0))


class FMEConversionApplicationSettingsFormTest(BaseUnitTest):
    """The settings form must survive a reload or a partial submit."""

    def _app(self):
        app = RemoteFMEConversionApplication(
            "fme",
            "t",
            "https://fme.example",
            "",
            "tok",
            "user",
            "secret",
            "60",
            "minute",
            "up",
            "dir",
            "tr",
            None,
            "gml",
            True,
            "w.fmw",
            None,
            True,
            300,
            "act",
            nRetries=7,
            FMEApiVersion="v4",
            FMEResourceConnection="CONN",
            FMERepository="repo",
            FMEConnectTimeout=10,
            FMEReadTimeout=300,
        )
        app.manage_settings_html = Mock(return_value="<html/>")
        return app

    def _request(self, form):
        request = Mock()
        request.form = form
        return request

    def test_a_reload_does_not_wipe_the_configuration(self):
        app = self._app()

        app.manage_settings(self._request({}))

        self.assertEqual(app.FMEServer, "https://fme.example")
        self.assertEqual(app.FMEPassword, "secret")
        self.assertEqual(app.nRetries, 7)
        self.assertTrue(app.FMEUploadAll)
        self.assertEqual(
            app.manage_settings_html.call_args[1]["manage_tabs_message"],
            "Nothing submitted, settings unchanged.",
        )

    def test_a_partial_submit_keeps_the_fields_it_omits(self):
        app = self._app()

        app.manage_settings(
            self._request({"title": "new", "FMEServer": "https://new.example"})
        )

        self.assertEqual(app.title, "new")
        self.assertEqual(app.FMEServer, "https://new.example")
        self.assertEqual(app.FMEPassword, "secret")
        self.assertEqual(app.FMEResourceConnection, "CONN")
        self.assertEqual(app.nRetries, 7)

    def test_numbers_fall_back_when_they_are_not_numbers(self):
        app = self._app()

        app.manage_settings(
            self._request(
                {
                    "nRetries": "not-a-number",
                    "FMEReadTimeout": "",
                    "retryFrequency": "60",
                }
            )
        )

        self.assertEqual(app.nRetries, 7)
        self.assertEqual(app.FMEReadTimeout, 300)
        self.assertEqual(app.retryFrequency, 60)
        self.assertEqual(app.get_request_timeout(), (10.0, 300.0))

    def test_unticked_checkboxes_are_cleared_on_a_real_submit(self):
        app = self._app()

        app.manage_settings(self._request({"title": "t"}))

        self.assertFalse(app.FMEUploadAll)
        self.assertFalse(app.FMEConvCleanup)


class FMEConversionApplicationCredentialsTest(BaseUnitTest):
    def _app(self):
        app = RemoteFMEConversionApplication(
            "fme",
            "t",
            "https://fme.example",
            "",
            "stored-token",
            "user",
            "stored-password",
            "60",
            "minute",
            "up",
            "dir",
            "tr",
            None,
            "gml",
            False,
            "w.fmw",
            None,
            True,
            300,
            "act",
        )
        app.manage_settings_html = Mock(return_value="<html/>")
        return app

    def _request(self, form):
        request = Mock()
        request.form = form
        return request

    def test_an_empty_field_keeps_the_stored_credential(self):
        app = self._app()

        app.manage_settings(
            self._request({"title": "t", "FMEPassword": "", "FMEToken": ""})
        )

        self.assertEqual(app.FMEPassword, "stored-password")
        self.assertEqual(app.FMEToken, "stored-token")

    def test_a_new_value_replaces_the_credential(self):
        app = self._app()

        app.manage_settings(self._request({"title": "t", "FMEPassword": "new-pw"}))

        self.assertEqual(app.FMEPassword, "new-pw")
        self.assertEqual(app.FMEToken, "stored-token")

    def test_the_clear_checkbox_removes_the_credential(self):
        app = self._app()

        app.manage_settings(self._request({"title": "t", "FMETokenClear": "1"}))

        self.assertEqual(app.FMEToken, "")
        self.assertEqual(app.FMEPassword, "stored-password")

    def test_has_secret_reports_without_disclosing(self):
        app = self._app()

        self.assertTrue(app.has_secret("FMEPassword"))
        self.assertTrue(app.has_secret("FMEToken"))
        app.FMEToken = ""
        self.assertFalse(app.has_secret("FMEToken"))
        with self.assertRaises(ValueError):
            app.has_secret("FMEServer")


class FMEConversionApplicationValidationTest(BaseUnitTest):
    """The settings page reports what would break at conversion time."""

    def _app(self, **kwargs):
        settings = dict(
            FMEApiVersion="v4",
            FMEResourceConnection="CONN",
            FMERepository="repo",
            FMEWorkspaceParams=WKS_PARAMS_V4,
            FMEUploadParams=None,
            FMEWorkspace="convert.fmw",
        )
        settings.update(kwargs)
        return RemoteFMEConversionApplication(
            "fme",
            "",
            "https://fme.example",
            "",
            "a-token",
            "",
            "",
            "",
            "minute",
            "up",
            "dir",
            "tr",
            settings["FMEUploadParams"],
            "gml",
            False,
            settings["FMEWorkspace"],
            settings["FMEWorkspaceParams"],
            True,
            300,
            "fme_app",
            nRetries=5,
            FMEApiVersion=settings["FMEApiVersion"],
            FMEApiEndpoint="fmeapiv4",
            FMEResourceConnection=settings["FMEResourceConnection"],
            FMERepository=settings["FMERepository"],
        )

    def _messages(self, app, level=None):
        return [
            p["message"]
            for p in app.validate_settings()
            if level is None or p["level"] == level
        ]

    def test_a_sound_v4_configuration_has_nothing_to_report(self):
        self.assertEqual(self._app().validate_settings(), [])

    def test_missing_v4_settings_are_errors(self):
        messages = " ".join(
            self._messages(
                self._app(FMEResourceConnection="", FMERepository=""), "error"
            )
        )

        self.assertIn("FME Resource connection is empty", messages)
        self.assertIn("FME Repository is empty", messages)

    def test_a_trailing_comma_is_named(self):
        app = self._app(
            FMEWorkspaceParams="{{'publishedParameters': {{'inputfile': '{GET_FILE}',}}}}"
        )

        messages = " ".join(self._messages(app, "error"))

        self.assertIn("not valid JSON", messages)
        self.assertIn("trailing comma", messages)

    def test_a_v3_shaped_template_on_v4_is_an_error(self):
        app = self._app(FMEWorkspaceParams=WKS_PARAMS_V3)

        self.assertIn("v4 expects an object", " ".join(self._messages(app, "error")))

    def test_a_v4_shaped_template_on_v3_is_an_error(self):
        app = self._app(FMEApiVersion="v3", FMEWorkspaceParams=WKS_PARAMS_V4)

        self.assertIn("v3 expects a list", " ".join(self._messages(app, "error")))

    def test_tmdirectives_on_v4_is_a_warning(self):
        app = self._app(
            FMEWorkspaceParams=(
                "{{'publishedParameters': {{'inputfile': '{GET_FILE}'}},"
                " 'TMDirectives': {{'rtc': false}}}}"
            )
        )

        self.assertIn("TMDirectives", " ".join(self._messages(app, "warning")))

    def test_an_unknown_variable_is_named(self):
        app = self._app(
            FMEWorkspaceParams="{{'publishedParameters': {{'f': '{GET_TYPO}'}}}}"
        )

        messages = " ".join(self._messages(app, "error"))

        self.assertIn("GET_TYPO", messages)
        self.assertIn("GET_SHAPEFILE", messages)

    def test_undoubled_braces_are_explained(self):
        app = self._app(FMEWorkspaceParams='{"publishedParameters": {}}')

        self.assertIn("braces must be doubled", " ".join(self._messages(app, "error")))

    def test_v3_upload_params_are_flagged_on_v4(self):
        app = self._app(FMEUploadParams="createDirectories: true")

        self.assertIn("createDirectories", " ".join(self._messages(app, "warning")))

    def test_credentials_are_checked(self):
        app = self._app()
        app.FMEToken = ""

        self.assertIn("No FME token", " ".join(self._messages(app, "error")))

    def test_saving_reports_the_problem_count(self):
        app = self._app(FMERepository="")
        app.manage_settings_html = Mock(return_value="<html/>")
        request = Mock()
        request.form = {"title": "t"}

        app.manage_settings(request)

        self.assertIn(
            "problem(s) found",
            app.manage_settings_html.call_args[1]["manage_tabs_message"],
        )
