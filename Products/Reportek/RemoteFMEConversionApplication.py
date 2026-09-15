# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is Reportek version 1.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA). Portions created by Eau de Web are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Miruna Badescu, Eau de Web

# RemoteFMEConversionApplication
##

import json
import logging
from datetime import datetime, timedelta
from io import BytesIO

import requests
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from AccessControl.Permissions import view_management_screens
from bs4 import BeautifulSoup as bs
from DateTime import DateTime
from OFS.SimpleItem import SimpleItem

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

logger = logging.getLogger(__name__ + ".FME")
FEEDBACKTEXT_LIMIT = 1024 * 16  # 16KB

manage_addRemoteFMEConversionApplicationForm = PageTemplateFile(
    "zpt/RemoteFMEConversionApplicationAdd", globals()
)


def manage_addRemoteFMEConversionApplication(
    self,
    id="",
    title="",
    FMEServer="",
    FMETokenEndpoint="",
    FMEToken=None,
    FMEUser="",
    FMEPassword="",
    FMETokenExpiration="",
    FMETokenTimeUnit="minute",
    FMEUploadEndpoint="",
    FMEUploadDir="",
    FMETransformation="",
    FMEUploadParams=None,
    FMEUploadAll=False,
    FMEFileTypes=None,
    FMEWorkspace="",
    FMEWorkspaceParams=None,
    FMEConvCleanup=True,
    retryFrequency=300,
    app_name="",
    FMEApiVersion="v3",
    FMEApiEndpoint="fmeapiv4",
    FMEResourceConnection="",
    FMERepository="",
    FMEConnectTimeout=10,
    FMEReadTimeout=300,
    REQUEST=None,
):
    """Generic application that calls a remote FME service"""

    ob = RemoteFMEConversionApplication(
        id,
        title,
        FMEServer,
        FMETokenEndpoint,
        FMEToken,
        FMEUser,
        FMEPassword,
        FMETokenExpiration,
        FMETokenTimeUnit,
        FMEUploadEndpoint,
        FMEUploadDir,
        FMETransformation,
        FMEUploadParams,
        FMEFileTypes,
        FMEUploadAll,
        FMEWorkspace,
        FMEWorkspaceParams,
        FMEConvCleanup,
        retryFrequency,
        app_name,
        FMEApiVersion=FMEApiVersion,
        FMEApiEndpoint=FMEApiEndpoint,
        FMEResourceConnection=FMEResourceConnection,
        FMERepository=FMERepository,
        FMEConnectTimeout=FMEConnectTimeout,
        FMEReadTimeout=FMEReadTimeout,
    )
    self._setObject(id, ob)

    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)


class RemoteFMEConversionApplication(SimpleItem):
    security = ClassSecurityInfo()
    security.declareObjectProtected("Use OpenFlow")
    SENSITIVE_ATTRIBUTES = ("FMEPassword", "FMEToken")

    def __allow_access_to_unprotected_subobjects__(self, name, value=None):
        return name not in self.SENSITIVE_ATTRIBUTES

    meta_type = "Remote FME Application"
    manage_options = (
        {"label": "Settings", "action": "manage_settings_html"},
    ) + SimpleItem.manage_options
    UP_METHOD = "filesys"
    DOWN_METHOD = "downloadzip"
    V4_UP_METHOD = "upload"
    V3_JOB_ENDPOINT = "fmerest/v3/transformations/jobs/id"
    V3_QUEUED_ENDPOINT = "fmerest/v3/transformations/jobs/queued"
    V3_RUNNING_ENDPOINT = "fmerest/v3/transformations/jobs/running"
    # FME Flow API v4 job statuses, as returned by GET /fmeapiv4/jobs/<id>:
    # queued, running, success, failure, cancelled
    V4_ABORT_STATUSES = ("failure", "cancelled")
    V4_DOWNLOAD_ITEM_LIMIT = 500
    FMEServer = ""
    FMETokenEndpoint = ""
    FMEToken = None
    FMEUser = ""
    FMEPassword = ""
    FMETokenExpiration = ""
    FMETokenTimeUnit = "minute"
    FMEUploadEndpoint = ""
    FMEUploadDir = ""
    FMETransformation = ""
    FMEUploadParams = None
    FMEFileTypes = None
    FMEUploadAll = False
    FMEWorkspace = ""
    FMEWorkspaceParams = None
    FMEConvCleanup = True
    retryFrequency = 300
    nRetries = 50
    app_name = ""
    FMEApiVersion = "v3"
    FMEApiEndpoint = "fmeapiv4"
    FMEResourceConnection = ""
    FMERepository = ""
    FMEConnectTimeout = 10
    FMEReadTimeout = 300

    security.declareProtected(view_management_screens, "manage_settings")
    security.declarePrivate(
        "ensure_text",
        "get_token_endpoint",
        "parse_token",
        "get_fme_token",
        "get_token",
        "get_files",
        "get_auth_header",
        "get_headers",
        "get_request_timeout",
        "get_api_root",
        "get_resource_connection",
        "get_repository",
        "get_workspace_name",
        "get_resource_url",
        "get_resource_path",
        "get_resource_items",
        "get_upload_params",
        "get_env_path_tokenized",
        "get_env_obligation",
        "handle_cleanup",
        "handle_res_zip_download",
        "upload_to_fme",
        "get_uploaded_paths",
        "to_number",
        "validate_workspace_params",
        "get_uploaded_files",
        "get_workspace_params",
        "get_job_request",
        "execute_workspace",
        "get_job_state",
        "handle_job_success",
        "handle_job_failure",
        "poll_results",
        "cancel_job",
        "delete_job",
    )
    security.declareProtected("Use OpenFlow", "__call__")
    security.declareProtected("View configuration", "is_v4")
    security.declareProtected(view_management_screens, "has_secret")
    security.declareProtected(view_management_screens, "validate_settings")

    security.declareProtected(view_management_screens, "manage_settings_html")
    manage_settings_html = PageTemplateFile(
        "zpt/RemoteFMEConversionApplicationSettings", globals()
    )

    security.declareProtected("View configuration", "index_html")
    index_html = PageTemplateFile("zpt/RemoteFMEConversionApplicationView", globals())

    def __init__(
        self,
        id,
        title,
        FMEServer,
        FMETokenEndpoint,
        FMEToken,
        FMEUser,
        FMEPassword,
        FMETokenExpiration,
        FMETokenTimeUnit,
        FMEUploadEndpoint,
        FMEUploadDir,
        FMETransformation,
        FMEUploadParams,
        FMEFileTypes,
        FMEUploadAll,
        FMEWorkspace,
        FMEWorkspaceParams,
        FMEConvCleanup,
        retryFrequency,
        app_name,
        nRetries=50,
        FMEApiVersion="v3",
        FMEApiEndpoint="fmeapiv4",
        FMEResourceConnection="",
        FMERepository="",
        FMEConnectTimeout=10,
        FMEReadTimeout=300,
    ):
        """Initialize a new instance of Document"""
        self.id = id
        self.title = title
        self.FMEServer = FMEServer
        self.FMETokenEndpoint = FMETokenEndpoint
        self.FMEToken = FMEToken
        self.FMEUser = FMEUser
        self.FMEPassword = FMEPassword
        self.FMETokenExpiration = FMETokenExpiration
        self.FMETokenTimeUnit = FMETokenTimeUnit
        self.FMEUploadEndpoint = FMEUploadEndpoint
        self.FMEUploadDir = FMEUploadDir
        self.FMETransformation = FMETransformation
        self.FMEUploadParams = FMEUploadParams
        self.FMEFileTypes = FMEFileTypes
        self.FMEUploadAll = FMEUploadAll
        self.FMEWorkspace = FMEWorkspace
        self.FMEWorkspaceParams = FMEWorkspaceParams
        self.FMEConvCleanup = FMEConvCleanup
        self.retryFrequency = retryFrequency
        self.app_name = app_name
        self.nRetries = int(nRetries)  # integer
        self.FMEApiVersion = FMEApiVersion
        self.FMEApiEndpoint = FMEApiEndpoint
        self.FMEResourceConnection = FMEResourceConnection
        self.FMERepository = FMERepository
        self.FMEConnectTimeout = FMEConnectTimeout
        self.FMEReadTimeout = FMEReadTimeout

    def manage_settings(self, REQUEST):
        """Change properties of the FME Application"""
        form = getattr(REQUEST, "form", None) or {}
        if not form:
            return self.manage_settings_html(
                manage_tabs_message="Nothing submitted, settings unchanged."
            )
        for name in self.SENSITIVE_ATTRIBUTES:
            if form.get(name + "Clear"):
                setattr(self, name, "")
            elif form.get(name):
                setattr(self, name, form.get(name))
        for name in (
            "title",
            "FMEServer",
            "FMEApiVersion",
            "FMEApiEndpoint",
            "FMEResourceConnection",
            "FMERepository",
            "FMETokenEndpoint",
            "FMEUser",
            "FMETokenExpiration",
            "FMETokenTimeUnit",
            "FMEUploadEndpoint",
            "FMEUploadDir",
            "FMETransformation",
            "FMEUploadParams",
            "FMEFileTypes",
            "FMEWorkspace",
            "FMEWorkspaceParams",
            "app_name",
        ):
            setattr(self, name, form.get(name, getattr(self, name)))
        self.FMEUploadAll = bool(form.get("FMEUploadAll", False))
        self.FMEConvCleanup = bool(form.get("FMEConvCleanup", False))
        for name in (
            "retryFrequency",
            "nRetries",
            "FMEConnectTimeout",
            "FMEReadTimeout",
        ):
            setattr(self, name, self.to_number(form.get(name), getattr(self, name)))
        problems = self.validate_settings()
        message = "Saved changes."
        if problems:
            message = "Saved changes. {} problem(s) found, see below.".format(
                len(problems)
            )
        return self.manage_settings_html(manage_tabs_message=message)

    def to_number(self, value, default):
        """Return `value` as an int, or `default` when it isn't one"""
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def ensure_text(self, value, encoding="utf-8"):
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            for enc in (encoding, "utf-8-sig", "utf-8", "cp1252", "latin-1"):
                try:
                    return value.decode(enc)
                except UnicodeDecodeError:
                    pass
            return value.decode(encoding, "replace")
        return str(value)

    def get_fme_token(self):
        """Retrieves the token from FME"""
        res = {}
        params = {
            "user": self.FMEUser,
            "password": self.FMEPassword,
            "expiration": self.FMETokenExpiration,
            "timeunit": self.FMETokenTimeUnit,
        }
        t_unit = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
        offset = int(self.FMETokenExpiration) * t_unit.get(self.FMETokenTimeUnit)
        expires = DateTime(datetime.now() + timedelta(seconds=offset))
        try:
            resp = requests.post(
                "/".join([self.FMEServer, self.get_token_endpoint()]),
                params=params,
                timeout=self.get_request_timeout(),
            )
            if resp.ok:
                res["token"] = self.parse_token(resp)
                res["expires"] = expires

            else:
                logger.error(
                    """FME authentication request failed. Could not"""
                    """ retrieve token: {}-{}""".format(resp.status_code, resp.content)
                )
        except Exception as e:
            logger.exception(
                """FME authentication request failed. Could not"""
                """ retrieve token: {}""".format(str(e))
            )

        return res

    def get_token_endpoint(self):
        """Return the endpoint used to generate a token."""
        return (self.FMETokenEndpoint or "fmetoken/generate.json").strip("/")

    def parse_token(self, response):
        """Extract the token out of a token generation response.

        `fmetoken/generate.json` answers with a serviceResponse envelope,
        while the plain `fmetoken/generate` flavour answers with the bare
        token.
        """
        content = self.ensure_text(response.content).strip()
        try:
            payload = response.json()
        except ValueError:
            return content
        if isinstance(payload, dict):
            service_response = payload.get("serviceResponse") or {}
            token = service_response.get("token") or payload.get("token")
            if token:
                return self.ensure_text(token).strip()
        return content

    def get_token(self, workitem_id):
        """Retrieves the workitem stored token"""
        workitem = getattr(self, workitem_id)
        # If we have explicit FMEToken, override the auto token generation
        if self.FMEToken:
            return {"token": self.FMEToken}
        token = getattr(workitem, "__token", {})
        expires = token.get("expires")
        if not expires or expires <= DateTime():
            # No token or token expired
            token = self.get_fme_token()
            if token:
                setattr(workitem, "__token", token)
                workitem._p_changed = 1
        return getattr(workitem, "__token", None)

    def get_files(self, workitem_id):
        """Returns the file structure needed for requests upload"""
        workitem = getattr(self, workitem_id)
        env = workitem.getMySelf()
        files = []
        latest = {}
        if not self.FMEUploadAll:
            ext = []
            for f_ext in self.FMEFileTypes.splitlines():
                if ":" in f_ext:
                    # split complext filetypes e.g. shapefiles
                    ext.extend(f_ext.split(":")[-1].strip(" []").split(","))
                else:
                    ext.append(f_ext)
                for e in ext:
                    e_files = [
                        f
                        for f in env.objectValues("Report Document")
                        if f.title_or_id().lower().endswith("." + e.strip().lower())
                    ]
                    if e_files:
                        for e_file in e_files:
                            grp_prefix = e_file.title_or_id().split(".")[0]
                            if not latest.get(grp_prefix) or (
                                latest.get(grp_prefix)
                                and latest.get(grp_prefix).lessThanEqualTo(
                                    e_file.bobobase_modification_time()
                                )
                            ):
                                latest[grp_prefix] = e_file.bobobase_modification_time()
            if not latest:
                raise ValueError(
                    "No convertible files found in the envelope. "
                    "Convertible file extensions for this workflow: {}.".format(
                        ", ".join(ext)
                    )
                )
            up_group = list(latest.keys())[
                list(latest.values()).index(max(latest.values()))
            ]
            files = [
                f
                for f in env.objectValues("Report Document")
                if f.title_or_id().lower().startswith(up_group.lower())
            ]
        else:
            files = env.objectValues("Report Document")
        files = list(set(files))

        return files

    def get_auth_header(self, workitem_id):
        token = self.get_token(workitem_id)
        if token:
            return {
                "Authorization": "fmetoken token={}".format(
                    self.ensure_text(token.get("token")).strip()
                )
            }
        return {}

    def get_headers(self, workitem_id):
        headers = self.get_auth_header(workitem_id)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        return headers

    def get_request_timeout(self):
        """Return the (connect, read) timeout of the FME requests.

        An empty or non positive value disables the corresponding timeout.
        """
        timeouts = []
        for value in (self.FMEConnectTimeout, self.FMEReadTimeout):
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = 0
            timeouts.append(value if value > 0 else None)
        if timeouts == [None, None]:
            return None
        return tuple(timeouts)

    def validate_settings(self):
        """Return the configuration problems as {level, message} records"""
        problems = []

        def err(message):
            problems.append({"level": "error", "message": message})

        def warn(message):
            problems.append({"level": "warning", "message": message})

        if not (self.FMEServer or "").strip():
            err("FME Server is empty.")
        elif not self.FMEServer.strip().lower().startswith(("http://", "https://")):
            warn("FME Server does not start with http:// or https://.")

        if not self.FMEToken and not (self.FMEUser and self.FMEPassword):
            err(
                "No FME token is stored and there is no username/password to"
                " generate one with."
            )

        if self.is_v4():
            if not (self.FMEResourceConnection or "").strip():
                err(
                    "FME Resource connection is empty: v4 uploads to a named"
                    " connection, e.g. FME_SHAREDRESOURCE_TEMP."
                )
            if not (self.FMERepository or "").strip():
                err(
                    "FME Repository is empty: v4 sends the repository in the"
                    " job payload instead of the url."
                )
            if "/" in (self.FMEWorkspace or ""):
                warn(
                    "FME Workspace should be the bare workspace name in v4,"
                    " the repository is a separate setting."
                )
        else:
            if not (self.FMEUploadEndpoint or "").strip():
                err("FME Upload endpoint is empty.")
            if not (self.FMETransformation or "").strip():
                err("FME Transformation path is empty.")

        if (self.FMEWorkspace or "") and not self.FMEWorkspace.lower().endswith(".fmw"):
            warn("FME Workspace does not end in .fmw.")

        if self.is_v4():
            unknown = [
                k for k in self.get_upload_params() if k not in ("path", "overwrite")
            ]
            if unknown:
                warn(
                    "FME Upload Parameters {} mean nothing to the v4 upload"
                    " endpoint, which only takes path and overwrite.".format(
                        ", ".join(sorted(unknown))
                    )
                )

        problems.extend(self.validate_workspace_params())
        return problems

    def validate_workspace_params(self):
        """Render the workspace exec template and check its shape"""
        template = self.FMEWorkspaceParams
        if not template:
            return []
        sample = {
            "GET_FILE": "sample.gml",
            "GET_SHAPEFILE": "sample.shp",
            "ENVPATHTOKENIZED": "cc_eu_envelope",
            "FMEUPLOADDIR": self.FMEUploadDir or "upload-dir",
            "GET_ENV_OBLIGATION": "780",
        }
        try:
            rendered = template.format(**sample)
        except KeyError as e:
            name = e.args[0] if e.args else ""
            hint = ""
            if not str(name).isidentifier():
                # the template read a piece of JSON as a variable
                hint = (
                    " Literal braces must be doubled, as in {{ and }}, so that"
                    " the JSON braces are not read as variables."
                )
            return [
                {
                    "level": "error",
                    "message": (
                        "FME Workspace exec parameters use the unknown"
                        " variable {!r}. Known ones: {}.{}".format(
                            name, ", ".join(sorted(sample)), hint
                        )
                    ),
                }
            ]
        except (IndexError, ValueError) as e:
            return [
                {
                    "level": "error",
                    "message": (
                        "FME Workspace exec parameters cannot be rendered"
                        " ({}). Literal braces must be doubled, as in"
                        " {{ and }}.".format(e)
                    ),
                }
            ]
        try:
            payload = json.loads(rendered.replace("'", '"'))
        except ValueError as e:
            return [
                {
                    "level": "error",
                    "message": (
                        "FME Workspace exec parameters are not valid JSON once"
                        " rendered ({}). A trailing comma before a closing"
                        " brace is the usual cause.".format(e)
                    ),
                }
            ]
        if not isinstance(payload, dict):
            return [
                {
                    "level": "error",
                    "message": "FME Workspace exec parameters must be a JSON object.",
                }
            ]

        problems = []
        published = payload.get("publishedParameters")
        if self.is_v4():
            if isinstance(published, list):
                problems.append(
                    {
                        "level": "error",
                        "message": (
                            "publishedParameters is a list of name/value pairs;"
                            " v4 expects an object, e.g."
                            ' {"inputfile": "{GET_FILE}"}.'
                        ),
                    }
                )
            if "TMDirectives" in payload:
                problems.append(
                    {
                        "level": "warning",
                        "message": (
                            "TMDirectives does not exist in v4: its tag is now"
                            " the top level queue, rtc and description are"
                            " gone."
                        ),
                    }
                )
        elif isinstance(published, dict):
            problems.append(
                {
                    "level": "error",
                    "message": (
                        "publishedParameters is an object; v3 expects a list of"
                        " name/value pairs."
                    ),
                }
            )
        return problems

    def has_secret(self, name):
        """Return True when the named credential is stored.

        The credentials themselves are never handed to the templates.
        """
        if name not in self.SENSITIVE_ATTRIBUTES:
            raise ValueError("Not a credential: {}".format(name))
        return bool(getattr(self, name, ""))

    def is_v4(self):
        """Return True if this application talks to the FME Flow API v4"""
        return (self.FMEApiVersion or "v3").strip().lower() == "v4"

    def get_api_root(self):
        """Return the root url of the FME Flow API v4"""
        endpoint = (self.FMEApiEndpoint or "fmeapiv4").strip("/")
        return "/".join([self.FMEServer.rstrip("/"), endpoint])

    def get_resource_connection(self):
        """Return the v4 resource connection holding the converted files"""
        connection = (self.FMEResourceConnection or "").strip("/")
        if not connection:
            raise ValueError(
                "No FME resource connection configured. The FME Flow API v4 "
                "needs the connection name (e.g. FME_SHAREDRESOURCE_TEMP) "
                "instead of the v3 upload endpoint path."
            )
        return connection

    def get_repository(self):
        """Return the v4 repository of the workspace to run"""
        repository = (self.FMERepository or "").strip("/")
        if not repository:
            raise ValueError(
                "No FME repository configured. The FME Flow API v4 takes the "
                "repository and the workspace as separate settings."
            )
        return repository

    def get_workspace_name(self):
        """Return the name of the workspace to run"""
        return (self.FMEWorkspace or "").strip("/").split("/")[-1]

    def get_resource_url(self, *path):
        """Build a v4 resource connection url"""
        return "/".join(
            [
                self.get_api_root(),
                "resources",
                "connections",
                self.get_resource_connection(),
            ]
            + [p.strip("/") for p in path]
        )

    def get_resource_path(self, workitem_id, *extra):
        """Return the envelope path relative to the resource connection"""
        parts = [self.FMEUploadDir, self.get_env_path_tokenized(workitem_id)]
        parts.extend(extra)
        return "/" + "/".join([p.strip("/") for p in parts if p])

    def get_resource_items(self, workitem_id, path):
        """Return the (status code, names) of the files stored under `path`"""
        res = requests.get(
            self.get_resource_url("info"),
            params={"path": path},
            headers=self.get_headers(workitem_id),
            timeout=self.get_request_timeout(),
        )
        if res.status_code != 200:
            return res.status_code, []
        contents = res.json().get("contents") or []
        names = [item.get("name") for item in contents if item.get("name")]
        if len(names) > self.V4_DOWNLOAD_ITEM_LIMIT:
            logger.warning(
                "FME folder %s holds %s items, the v4 download endpoint "
                "accepts at most %s",
                path,
                len(names),
                self.V4_DOWNLOAD_ITEM_LIMIT,
            )
        return res.status_code, names

    def get_upload_params(self):
        """Return the extra upload parameters configured on the application"""
        params = {}
        if self.FMEUploadParams:
            for p in self.FMEUploadParams.splitlines():
                if ":" not in p:
                    continue
                k, v = p.split(":", 1)
                params[k.strip()] = v.strip()
        return params

    def get_env_path_tokenized(self, workitem_id):
        """Return tokenized envelope path."""
        workitem = getattr(self, workitem_id)
        env_path = "/".join(workitem.getMySelf().getPhysicalPath())
        return env_path.replace("/", "_")[1:]

    def get_env_obligation(self, workitem_id):
        """Return the envelope obligation"""
        workitem = getattr(self, workitem_id)
        df = workitem.getMySelf().dataflow_uris[0]
        return df.split("/")[-1]

    def handle_cleanup(self, workitem_id):
        """Delete the temporary folder on FME."""
        workitem = getattr(self, workitem_id)
        if self.FMEConvCleanup:
            try:
                params = {}
                if self.is_v4():
                    url = self.get_resource_url("item")
                    params = {"path": self.get_resource_path(workitem_id)}
                else:
                    url = "/".join(
                        [
                            self.FMEServer,
                            self.FMEUploadEndpoint,
                            self.UP_METHOD,
                            self.FMEUploadDir,
                            self.get_env_path_tokenized(workitem_id),
                        ]
                    )
                headers = self.get_headers(workitem_id)
                res = requests.delete(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.get_request_timeout(),
                )
                if res.status_code == 204:
                    self.__update_storage(workitem, "cleanup", status="completed")
            except Exception as e:
                self.__update_storage(
                    workitem, "cleanup", err=e, status="failed", dec_retry=True
                )

    def handle_res_zip_download(self, workitem_id):
        """Download the result files as zip"""
        workitem = getattr(self, workitem_id)
        env = workitem.getMySelf()
        headers = self.get_headers(workitem_id)
        headers["Accept"] = "application/zip"
        if self.is_v4():
            # v4 takes the file names explicitly, there is no "." wildcard
            path = self.get_resource_path(workitem_id, "output")
            status, items = self.get_resource_items(workitem_id, path)
            if not items:
                if status != 200:
                    return (
                        status,
                        "Unable to list the FME output folder {}".format(path),
                    )
                return (
                    404,
                    "No converted file(s) found on FME at {}".format(path),
                )
            url = self.get_resource_url(self.DOWN_METHOD)
            payload = {
                "path": path,
                "items": items,
                "zipFileName": "resources.zip",
            }
            res = requests.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                timeout=self.get_request_timeout(),
            )
        else:
            url = "/".join(
                [
                    self.FMEServer,
                    self.FMEUploadEndpoint,
                    self.DOWN_METHOD,
                    self.FMEUploadDir,
                    self.get_env_path_tokenized(workitem_id),
                    "output",
                ]
            )
            params = {"zipFileName": "resources.zip", "fileNames": "."}
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            res = requests.post(
                url,
                params=params,
                headers=headers,
                timeout=self.get_request_timeout(),
            )
        if res.status_code == 200:
            z = BytesIO(res.content)
            z.filename = "resources.zip"
            return env.manage_addDDzipfile(file=z, verbose=True)
        else:
            return (
                res.status_code,
                "Something went wrong while retrieving the converted file(s)",
            )

    def upload_to_fme(self, workitem_id):
        """Upload the file(s) to the fme data upload"""
        workitem = getattr(self, workitem_id)
        upload_storage = getattr(workitem, self.app_name, {}).get("upload")
        if upload_storage.get("retries_left") and upload_storage.get(
            "next_run"
        ).lessThanEqualTo(DateTime()):
            files = self.get_files(workitem_id)
            files = [
                ("files", (f.title_or_id(), f.data_file.open("rb"))) for f in files
            ]
            try:
                if self.is_v4():
                    url = self.get_resource_url(self.V4_UP_METHOD)
                    params = {
                        "path": self.get_resource_path(workitem_id),
                        "overwrite": "true",
                    }
                else:
                    url = "/".join(
                        [
                            self.FMEServer,
                            self.FMEUploadEndpoint,
                            self.UP_METHOD,
                            self.FMEUploadDir,
                            self.get_env_path_tokenized(workitem_id),
                        ]
                    )
                    params = {}
                params.update(self.get_upload_params())
                headers = self.get_headers(workitem_id)
                # We need to explicitly remove the content-type on file upload
                if "Content-Type" in headers:
                    del headers["Content-Type"]
                res = requests.post(
                    url,
                    params=params,
                    files=files,
                    headers=headers,
                    timeout=self.get_request_timeout(),
                )
                if res.status_code in (200, 201):
                    paths = self.get_uploaded_paths(res, files)
                    if paths:
                        up_files = ""
                        for x in paths:
                            up_files += "<li>%s</li>" % (x)
                        workitem.addEvent(
                            "Files uploaded to FME for conversion: <ul>%s</ul>"
                            % (up_files)
                        )

                        self.__update_storage(
                            workitem, "upload", paths=paths, status="completed"
                        )
                    else:
                        err = "Unable to determine the file(s) uploaded to FME"
                        logger.warning(err)
                        self.__update_storage(
                            workitem, "upload", err=err, dec_retry=True
                        )

                else:
                    err = "HTTP: {}: {}".format(res.status_code, res.content)
                    self.__update_storage(workitem, "upload", err=err, dec_retry=True)
            except Exception as e:
                self.__update_storage(
                    workitem,
                    "upload",
                    status="failed",
                    err=str(e),
                    dec_retry=True,
                )
            finally:
                # Close the files
                for file in files:
                    try:
                        file[-1][-1].close()
                    except Exception:
                        pass

    def get_uploaded_paths(self, response, files):
        """Return the names of the files uploaded to FME.

        The v3 endpoint answers with a list of file records; the v4 one
        doesn't guarantee a body, so fall back on the names just sent.
        """
        try:
            srv_res = response.json()
        except ValueError:
            srv_res = None
        if isinstance(srv_res, dict):
            srv_res = srv_res.get("items") or srv_res.get("files")
        if isinstance(srv_res, list):
            paths = [
                f.get("name") for f in srv_res if isinstance(f, dict) and f.get("name")
            ]
            if paths:
                return paths
        return [f[-1][0] for f in files]

    def get_uploaded_files(self, workitem_id, single_file=False, shapefile=False):
        """Return a list of uploaded files"""
        workitem = getattr(self, workitem_id)
        env = workitem.getMySelf()
        upload_storage = getattr(workitem, self.app_name, {}).get("upload")
        if single_file and upload_storage["paths"]:
            if self.FMEFileTypes:
                files = []
                for f_ext in self.FMEFileTypes.splitlines():
                    files.extend(
                        [
                            f
                            for f in upload_storage["paths"]
                            if f.lower().endswith("." + f_ext.lower())
                        ]
                    )
                    if files:
                        return files[-1]
            zips = [f for f in upload_storage["paths"] if f.lower().endswith(".zip")]
            convs = [f for f in upload_storage["paths"] if f.split(".")[0] in zips]
            for z in zips:
                if z not in convs:
                    return z
            return upload_storage["paths"][-1]
        if shapefile and upload_storage["paths"]:
            for p in reversed(upload_storage["paths"]):
                if p.endswith((".shp", ".zip")):
                    gmls = [
                        fid.split(".")[0]
                        for fid in env.objectIds("Report Document")
                        if fid.endswith(".gml")
                    ]
                    if not [x for x in gmls if p.split(".")[0] in x]:
                        return p
        return upload_storage["paths"]

    def get_workspace_params(self, workitem_id):
        """Render the JSON template configured on the application"""
        if not self.FMEWorkspaceParams:
            return {}
        wks_params = self.FMEWorkspaceParams.format(
            GET_FILE=self.get_uploaded_files(workitem_id, single_file=True),
            GET_SHAPEFILE=self.get_uploaded_files(workitem_id, shapefile=True),
            ENVPATHTOKENIZED=self.get_env_path_tokenized(workitem_id),
            FMEUPLOADDIR=self.FMEUploadDir,
            GET_ENV_OBLIGATION=self.get_env_obligation(workitem_id),
        )
        wks_params = wks_params.replace("'", '"')
        try:
            return json.loads(wks_params)
        except ValueError as e:
            logger.warning(
                "Unparsable FME Workspace exec parameters for %s: %s\n%s",
                self.absolute_url(),
                e,
                wks_params,
            )
            raise ValueError(
                "The FME Workspace exec parameters are not valid JSON once"
                " rendered ({}). A trailing comma before a closing brace is"
                " the usual cause; the rendered template is in the log.".format(e)
            )

    def get_job_request(self, workitem_id):
        """Return the (url, payload, inputfile) of the workspace execution"""
        wks_params = self.get_workspace_params(workitem_id)
        inputfile = None
        if self.is_v4():
            # v4 submits the job to a single endpoint, the workspace to run
            # is part of the payload
            url = "/".join([self.get_api_root(), "jobs"])
            payload = dict(wks_params)
            payload["repository"] = self.get_repository()
            payload["workspace"] = self.get_workspace_name()
            published = payload.get("publishedParameters") or {}
            if not isinstance(published, dict):
                raise ValueError(
                    "The FME Flow API v4 expects 'publishedParameters' as a "
                    'JSON object (e.g. {"publishedParameters": '
                    '{"inputfile": "..."}}), not as a list of '
                    "name/value pairs. Please update the FME Workspace exec "
                    "parameters of this application."
                )
            inputfile = published.get("inputfile")
        else:
            url = "/".join([self.FMEServer, self.FMETransformation, self.FMEWorkspace])
            payload = wks_params
            for param in wks_params.get("publishedParameters") or []:
                if param.get("name") == "inputfile":
                    inputfile = param.get("value")
        return url, payload, inputfile

    def execute_workspace(self, workitem_id):
        """Execute the workspace"""
        workitem = getattr(self, workitem_id)
        results = getattr(workitem, self.app_name, {}).get("results")
        try:
            url, payload, inputfile = self.get_job_request(workitem_id)
            # params should be passed in the body of the request
            res = requests.post(
                url,
                data=json.dumps(payload),
                headers=self.get_headers(workitem_id),
                timeout=self.get_request_timeout(),
            )
            if res.status_code == 202:
                # submission successful, response looks like:
                # res.json()
                # {u'id': 989126}
                # If we posted multiple files, do we get a single ID back?
                # expecting a mail response to this
                results[res.json().get("id")] = {
                    "retries_left": self.nRetries,
                    "last_error": None,
                    "next_run": DateTime(),
                    "status": "pending",
                    "inputfile": inputfile,
                }
                workitem.addEvent("FME job id: {} started".format(res.json().get("id")))
                self.__update_storage(workitem, "fmw_exec", status="completed")
            else:
                err = "HTTP: {}: {}".format(res.status_code, res.content)
                self.__update_storage(
                    workitem,
                    "fmw_exec",
                    status="retry",
                    err=err,
                    dec_retry=True,
                )
        except Exception as e:
            self.__update_storage(
                workitem, "fmw_exec", status="retry", err=e, dec_retry=True
            )

    def get_job_state(self, workitem_id, job_id):
        """Return the (state, status) of an FME job.

        `state` is one of "success", "retry", "abort" or None, the latter
        meaning the job is left untouched and polled again on the next run.
        """
        if self.is_v4():
            # https://<fme_service>/fmeapiv4/jobs/<job_id>
            # The job record is readable in any state (queued, running or
            # completed); /jobs/<job_id>/result only covers a finished job.
            url = "/".join([self.get_api_root(), "jobs", str(job_id)])
        else:
            # https://<fme_service>/fmerest/v3/transformations/jobs/id/<job_id>
            url = "/".join([self.FMEServer, self.V3_JOB_ENDPOINT, str(job_id)])
        res = requests.get(
            url,
            headers=self.get_headers(workitem_id),
            timeout=self.get_request_timeout(),
        )
        if res.status_code != 200:
            return "retry", "HTTP {}".format(res.status_code)
        response = res.json()
        fme_status = response.get("status")
        if self.is_v4():
            # v4 statuses: queued, running, success, failure, cancelled
            if fme_status == "success":
                return "success", fme_status
            if fme_status in self.V4_ABORT_STATUSES:
                message = response.get("statusMessage")
                if message:
                    fme_status = "{}: {}".format(fme_status, message)
                return "abort", fme_status
            return "retry", fme_status

        retry = [
            "SUBMITTED",
            "QUEUED",
            "DELAYED",
            "PAUSED",
            "IN_PROCESS",
            "PULLED",
        ]
        abort = [
            "DELETED",
            "ABORTED",
            "FME_FAILURE",
            "JOB_FAILURE",
        ]
        if fme_status == "SUCCESS":
            if (response.get("result") or {}).get("status") == "SUCCESS":
                return "success", fme_status
            return None, fme_status
        if fme_status in retry:
            return "retry", fme_status
        if fme_status in abort:
            return "abort", fme_status
        return None, fme_status

    def handle_job_success(self, workitem_id, job_id, inputfile=None):
        """Download the results of a finished job and post the feedback"""
        workitem = getattr(self, workitem_id)
        workitem.addEvent("""FME job id: {} finished""".format(job_id))
        dl_res = self.handle_res_zip_download(workitem_id)
        if dl_res[0] != 1:
            msg = "{}: {}".format(dl_res[0], dl_res[1])
            workitem.addEvent(msg)
            self.__post_feedback(
                workitem,
                job_id,
                msg,
                inputfile=inputfile,
                content_type="text/html",
            )
            self.__update_storage(
                workitem,
                "results",
                jobid=job_id,
                status="failed",
                err=msg,
                dec_retry=True,
            )
        else:
            msg = ("""Conversion successful. {}""").format(dl_res[1])
            workitem.addEvent(msg)
            self.__post_feedback(
                workitem,
                job_id,
                msg,
                inputfile=inputfile,
                content_type="text/html",
            )
            self.__update_storage(
                workitem,
                "results",
                jobid=job_id,
                status="completed",
            )

    def handle_job_failure(self, workitem_id, job_id, fme_status, inputfile=None):
        """Abort the conversion of a failed job"""
        workitem = getattr(self, workitem_id)
        dl_res = self.handle_res_zip_download(workitem_id)
        if dl_res[0] != 1:
            msg = "{}: {}".format(dl_res[0], dl_res[1])
            workitem.addEvent(msg)
        err = "FME Status: {}. Aborting".format(fme_status)
        self.__update_storage(
            workitem,
            "results",
            jobid=job_id,
            status="failed",
            err=err,
            dec_retry=True,
        )
        workitem.addEvent(err)
        workitem.failure = True
        self.__post_feedback(
            workitem,
            job_id,
            "Conversion failed, aborting",
            inputfile=inputfile,
        )

    def poll_results(self, workitem_id):
        """Polls for results"""
        workitem = getattr(self, workitem_id)
        results = getattr(workitem, self.app_name, {}).get("results")
        if not results:
            return
        for job_id in list(results.keys()):
            if (
                results[job_id].get("status") in ["completed", "failed"]
                or not results[job_id].get("retries_left")
                or not results[job_id].get("next_run").lessThanEqualTo(DateTime())
            ):
                continue
            inputfile = results[job_id].get("inputfile")
            try:
                state, fme_status = self.get_job_state(workitem_id, job_id)
                if state == "success":
                    self.handle_job_success(workitem_id, job_id, inputfile)
                elif state == "retry":
                    err = (
                        """FME Status: {}. Re-scheduled"""
                        """ for polling""".format(fme_status)
                    )
                    self.__update_storage(
                        workitem,
                        "results",
                        jobid=job_id,
                        status="retry",
                        err=err,
                        dec_retry=True,
                    )
                elif state == "abort":
                    self.handle_job_failure(workitem_id, job_id, fme_status, inputfile)
            except Exception as e:
                self.__update_storage(
                    workitem,
                    "results",
                    jobid=job_id,
                    status="retry",
                    err=e,
                    dec_retry=True,
                )

    def __call__(self, workitem_id, REQUEST=None):
        workitem = getattr(self, workitem_id)

        # Initialize the workitem FME Conversion specific extra properties
        self.__initialize(workitem_id)
        self.upload_to_fme(workitem_id)
        upload_storage = getattr(workitem, self.app_name, {}).get("upload")
        if upload_storage.get("status") == "completed":
            self.execute_workspace(workitem_id)

    security.declareProtected("Use OpenFlow", "callApplication")

    def callApplication(self, workitem_id, REQUEST):
        workitem = getattr(self, workitem_id)
        storage = getattr(workitem, self.app_name, {})
        upload_storage = storage.get("upload")
        results = storage.get("results")
        fmw_exec = storage.get("fmw_exec")
        if upload_storage.get("status") != "completed" and upload_storage.get(
            "retries_left"
        ):
            self.upload_to_fme(workitem_id)
        elif upload_storage.get("status") != "completed" and not upload_storage.get(
            "retries_left"
        ):
            err = "File upload failed! Aborting."
            workitem.addEvent(err)
            workitem.failure = True
            self.__post_feedback(workitem, "upload", err)
            self.__finish(workitem_id)
        if upload_storage.get("status") == "completed":
            if (
                fmw_exec.get("status") != "completed"
                and fmw_exec.get("retries_left")
                and fmw_exec.get("next_run").lessThanEqualTo(DateTime())
            ):
                self.execute_workspace(workitem_id)
            elif fmw_exec.get("status") != "completed" and not fmw_exec.get(
                "retries_left"
            ):
                err = "FME Workspace execution failed! Aborting."
                workitem.addEvent(err)
                workitem.failure = True
                self.__post_feedback(workitem, "fmw_exec", err)
                self.__finish(workitem_id)
        if results:
            poll = [
                j
                for j in results
                if (
                    results[j].get("status") not in ["completed", "failed"]
                    and results[j].get("retries_left") > 0
                )
            ]
            if poll:
                self.poll_results(workitem_id)
            else:
                exhausted = [
                    j
                    for j in results
                    if results[j].get("status") == "retry"
                    and results[j].get("retries_left") == 0
                ]
                if exhausted:
                    err = "FME Result polling max retries exhausted! Aborting."
                    workitem.addEvent(err)
                    workitem.failure = True
                    self.__post_feedback(workitem, "results", err)
                self.handle_cleanup(workitem_id)
                workitem.addEvent("FME Cleanup completed.")
                self.__finish(workitem_id)

    def __initialize(self, p_workitem_id):
        """Adds FME-QA specific extra properties to the workitem"""
        workitem = getattr(self, p_workitem_id)
        setattr(workitem, self.app_name, {})
        storage = getattr(workitem, self.app_name)

        if not self.FMEToken:
            token = self.get_fme_token()

            if token:
                setattr(workitem, "__token", token)
                workitem._p_changed = 1

        storage.update(
            {
                "upload": {
                    "retries_left": self.nRetries,
                    "last_error": None,
                    "next_run": DateTime(),
                    "status": "pending",
                },
                "fmw_exec": {
                    "retries_left": self.nRetries,
                    "last_error": None,
                    "next_run": DateTime(),
                    "status": "pending",
                },
                "results": {},
                "cleanup": {
                    "retries_left": self.nRetries,
                    "last_error": None,
                    "next_run": DateTime(),
                    "status": "pending",
                },
            }
        )

    def __update_storage(
        self,
        workitem,
        step,
        paths=None,
        jobid=None,
        status=None,
        err=None,
        dec_retry=False,
    ):
        if jobid and step == "results":
            storage = getattr(workitem, self.app_name)[step][jobid]
        else:
            storage = getattr(workitem, self.app_name)[step]
        if paths:
            storage["paths"] = paths
        if dec_retry:
            storage["retries_left"] -= 1
        if err:
            storage["last_error"] = str(err)
        if status:
            storage["status"] = status
        storage["next_run"] = DateTime(
            int(storage["next_run"]) + int(self.retryFrequency)
        )
        workitem._p_changed = 1

    def __post_feedback(
        self,
        workitem,
        jobid,
        messages,
        inputfile=None,
        attach=None,
        content_type="text/plain",
    ):
        envelope = self.aq_parent
        feedback_id = "{}_{}_{}".format(self.app_name, jobid, workitem.id)
        if inputfile:
            feedback_id = "conversion_log_{}_{}".format(workitem.id, inputfile)
        envelope.manage_addFeedback(
            id=feedback_id,
            file=attach,
            title="%s results" % self.app_name,
            activity_id=workitem.activity_id,
            automatic=1,
            feedbacktext=messages,
            document_id=inputfile,
        )
        feedback_ob = getattr(envelope, feedback_id)
        feedback_ob.content_type = content_type
        conv_res_id = "conversion_log_{}".format(jobid)
        for doc_id in envelope.objectIds("Report Document"):
            if conv_res_id in doc_id:
                doc = getattr(envelope, doc_id)
                fb_status = None
                fb_message = None
                with doc.data_file.open() as f:
                    content = f.read()
                    text_content = self.ensure_text(content)
                    if doc.content_type == "text/html":
                        soup = bs(text_content, features="html.parser")
                        log_sum = soup.find("span", attrs={"id": "feedbackStatus"})
                        fb_status = log_sum.get("class", ["UNKNOWN"])
                        if isinstance(fb_status, list):
                            fb_status = fb_status[0] if fb_status else "UNKNOWN"
                        fb_message = log_sum.text
                    if len(content) > FEEDBACKTEXT_LIMIT:
                        f.seek(0)
                        feedback_ob.manage_uploadFeedback(f, filename="qa-output")
                        feedback_attach = feedback_ob.objectValues()[0]
                        feedback_attach.data_file.content_type = doc.content_type
                        feedback_ob.feedbacktext = "{}</br>{}".format(
                            feedback_ob.feedbacktext,
                            (
                                "Feedback too large for inline display; "
                                '<a href="qa-output/view">see attachment</a>.'
                            ),
                        )
                        feedback_ob.content_type = "text/html"
                    else:
                        feedback_ob.feedbacktext = text_content
                        feedback_ob.content_type = doc.content_type
                if fb_status and fb_message:
                    if fb_status == "BLOCKER":
                        workitem.blocker = True
                    feedback_ob.message = fb_message
                    feedback_ob.feedback_status = fb_status
                    feedback_ob._p_changed = 1
                    feedback_ob.reindexObject()

                envelope.manage_delObjects([doc.getId()])
                # Get the file, post if as attachment and delete it afterwards

    def cancel_job(self, job_id, workitem_id):
        """Cancel a queued or running job, return the last response"""
        if self.is_v4():
            # v4 cancels queued and running jobs through a single endpoint:
            # POST /fmeapiv4/jobs/<job_id>/cancel
            url = "/".join([self.get_api_root(), "jobs", str(job_id), "cancel"])
            return requests.post(
                url,
                headers=self.get_headers(workitem_id),
                timeout=self.get_request_timeout(),
            )

        url = "/".join([self.FMEServer, self.V3_QUEUED_ENDPOINT, str(job_id)])
        res = requests.delete(
            url,
            headers=self.get_headers(workitem_id),
            timeout=self.get_request_timeout(),
        )
        if res.status_code == 204:
            return res
        url = "/".join([self.FMEServer, self.V3_RUNNING_ENDPOINT, str(job_id)])
        return requests.delete(
            url,
            headers=self.get_headers(workitem_id),
            timeout=self.get_request_timeout(),
        )

    def delete_job(self, job_id, workitem_id):
        """Make a request to delete the job"""
        workitem = getattr(self, workitem_id)
        try:
            username = self.REQUEST["AUTHENTICATED_USER"].getUserName()
        except Exception:
            username = "N/A"
        workitem.addEvent(
            "FME Conversion application cancelled by: {}".format(username)
        )
        try:
            res = self.cancel_job(job_id, workitem_id)
            if res.status_code == 204:
                workitem.addEvent("FME job id: {} deleted successfully".format(job_id))
            else:
                workitem.addEvent(
                    "FME job id: {} delete failed: {}".format(job_id, res.status_code)
                )
        except Exception as e:
            workitem.addEvent("FME job id: {} delete failed: {}".format(job_id, str(e)))

        self.handle_cleanup(workitem_id)
        workitem.addEvent("FME Cleanup completed.")

        self.__finish(workitem_id)

    def __finish(self, workitem_id, REQUEST=None):
        """Completes the workitem and forwards it"""
        self.activateWorkitem(workitem_id, actor="openflow_engine")
        self.completeWorkitem(workitem_id, actor="openflow_engine", REQUEST=REQUEST)


InitializeClass(RemoteFMEConversionApplication)
