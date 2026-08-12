"""Reportek CAS/ECAS PAS plugin.

Python 3 replacement for the historical ``anz.casclient`` +
``anz.ecasclient`` stack.  The plugin intentionally preserves the Reportek
facing API of the old eCas plugin so existing Reportek code can keep using::

    /acl_users/eCas
    getEcasUserId(), getEcasUser(), getEcasIDEmail(), getEcasIDUsername()

Security notes:
- TLS verification is enabled by default.
- Service URL can be pinned explicitly and should be in production.
- Tickets and PGTs are never logged.
- CAS XML is parsed with defusedxml when available.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urljoin, urlparse, urlunparse, parse_qsl

import requests
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from OFS.Cache import Cacheable
from persistent import Persistent

try:
    from persistent.mapping import PersistentMapping
except ImportError:  # pragma: no cover - ZODB compatibility fallback
    from ZODB.PersistentMapping import PersistentMapping
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.interfaces.plugins import (
    IAuthenticationPlugin,
    IChallengePlugin,
    ICredentialsResetPlugin,
    IExtractionPlugin,
)
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements

try:  # defusedxml is preferred for parsing CAS server XML responses.
    from defusedxml import ElementTree
except ImportError:  # pragma: no cover
    from xml.etree import ElementTree

try:
    from cas import CASClient
except ImportError:  # pragma: no cover - buildout should provide python-cas
    CASClient = None

from Products.Reportek.config import DEPLOYMENT_BDR, REPORTEK_DEPLOYMENT
from Products.Reportek.constants import ECAS_ID

LOG = logging.getLogger("Products.Reportek.ReportekCASPlugin")
CAS_CACHE_PREFIX = os.environ.get("CAS_CACHE_PREFIX", "reportek:cas")

# Ranked EU Login authentication levels.  Only these can be compared against
# ``minimumAuthenticationLevel``; EU Login also emits unranked values such as
# ``STRONG`` for eID logins, which must not be treated as a failure unless a
# minimum above BASIC is actually required.
AUTHENTICATION_LEVELS = {"BASIC": 0, "MEDIUM": 1, "HIGH": 2}


class _TimeoutSession(requests.Session):
    """Requests session that applies a default timeout to CAS calls."""

    def __init__(self, timeout):
        super().__init__()
        self.timeout = timeout

    def request(self, method, url, **kwargs):
        if self.timeout:
            kwargs.setdefault("timeout", self.timeout)
        return super().request(method, url, **kwargs)


CAS_YALE_NS = "http://www.yale.edu/tp/cas"
CAS_ECAS_NS = "https://ecas.ec.europa.eu/cas/schemas"
SAML2_PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol"


@dataclass
class ReportekCASPrincipal:
    """Authenticated CAS principal compatible with old anz.casclient."""

    id: str
    ecas_id: str = None
    meta: dict = None
    pgt: str = None
    plugin: object = None

    def getId(self):
        return self.id

    def getProxyTicketFor(self, service):
        if self.pgt and self.plugin:
            return self.plugin.getProxyTicketFor(self.pgt, service)
        return None

    def __getstate__(self):
        state = self.__dict__.copy()
        # The plugin is acquisition-wrapped and cannot be pickled by Beaker.
        # It is only needed for proxy-ticket helper calls, not authentication.
        state["plugin"] = None
        return state


@dataclass
class ReportekCASAssertion:
    """Assertion wrapper compatible with old anz.casclient."""

    principal: ReportekCASPrincipal

    def getPrincipal(self):
        return self.principal


class EcasClient(Persistent):
    """Persistent ecas_id -> username/email mapping entry."""

    def __init__(self, ecas_id, value):
        self.ecas_id = ecas_id
        if is_email(value):
            self._email = value
        else:
            self._username = value

    @property
    def username(self):
        return getattr(self, "_username", None)

    @property
    def email(self):
        return getattr(self, "_email", None)


def is_email(value):
    return bool(value and "@" in value and "." in value.split("@")[-1])


def _strip_ticket(url):
    parsed = urlparse(url)
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() != "ticket"
    ]
    return urlunparse(parsed._replace(query=urlencode(query)))


def _text(element):
    return element.text if element is not None else None


class ReportekCASPlugin(BasePlugin, Cacheable):
    """CAS/ECAS PAS plugin for Reportek.

    The object should normally be installed as ``/acl_users/eCas``.
    """

    meta_type = "Reportek CAS Plugin"
    security = ClassSecurityInfo()

    CAS_ASSERTION = "__reportek_cas_assertion"

    casServerUrlPrefix = ""
    casServerValidationUrl = ""
    serviceUrl = ""
    proxyCallbackUrlPrefix = ""
    ticketValidationSpecification = "CAS 2.0"
    ticketValidationSpecification_values = (
        "CAS 2.0",
        "CAS 3.0",
    )
    serviceValidationEndpoint = "serviceValidate"
    serviceValidationEndpoint_values = (
        "serviceValidate",
        "laxValidate",
    )
    loginIdentifier = "ecas_id"
    loginIdentifier_values = (
        "ecas_id",
        "email",
        "moniker",
    )
    displayIdentifier = "login"
    displayIdentifier_values = (
        "login",
        "email",
        "ecas_id",
        "moniker",
    )
    displayIdentifierGuide = (
        "'login' keeps the displayed user name identical to the PAS login id, "
        "which is what the legacy anz.ecasclient plugin did and what Reportek "
        "code comparing getUserName() with getId()/owner ids relies on. "
        "Pick another value only if user names may safely differ from ids."
    )
    minimumAuthenticationLevel = "BASIC"
    minimumAuthenticationLevel_values = (
        "BASIC",
        "MEDIUM",
        "HIGH",
    )
    authenticationLevelGuide = (
        "EU Login authenticationLevel meanings: "
        "BASIC = single-factor or equivalent authentication, suitable for lower-risk access; "
        "MEDIUM = stronger/two-step style authentication for significant security requirements; "
        "HIGH = strongest multi-factor assurance for sensitive systems. "
        "BDR default is BASIC, which enforces nothing: levels EU Login "
        "reports but we cannot rank (e.g. STRONG for eID) are logged and "
        "accepted. Selecting MEDIUM or HIGH enforces strictly, and a missing "
        "or unrankable level is then rejected."
    )
    useSession = True
    renew = False
    gateway = False
    internalMapping = True
    verifySslCertificate = True
    requestTimeout = 10
    pgtCallbackTimeout = 5
    pgtStorageTimeout = 60
    sessionMappingTimeout = 3600
    acceptAnyProxy = False
    allowedProxyChains = ()

    _properties = (
        {"id": "serviceUrl", "label": "Service URL", "type": "string", "mode": "w"},
        {
            "id": "casServerUrlPrefix",
            "label": "CAS Server URL Prefix",
            "type": "string",
            "mode": "w",
        },
        {
            "id": "casServerValidationUrl",
            "label": "ECAS Validation URL Prefix",
            "type": "string",
            "mode": "w",
        },
        {
            "id": "proxyCallbackUrlPrefix",
            "label": "Proxy Callback URL Prefix",
            "type": "string",
            "mode": "w",
        },
        {
            "id": "ticketValidationSpecification",
            "label": "Validation Specification",
            "select_variable": "ticketValidationSpecification_values",
            "type": "selection",
            "mode": "w",
        },
        {
            "id": "serviceValidationEndpoint",
            "label": "Service validation endpoint",
            "select_variable": "serviceValidationEndpoint_values",
            "type": "selection",
            "mode": "w",
        },
        {
            "id": "loginIdentifier",
            "label": "PAS login identifier",
            "select_variable": "loginIdentifier_values",
            "type": "selection",
            "mode": "w",
        },
        {
            "id": "displayIdentifier",
            "label": "Displayed user identifier",
            "select_variable": "displayIdentifier_values",
            "type": "selection",
            "mode": "w",
        },
        {
            "id": "displayIdentifierGuide",
            "label": "Displayed identifier guide",
            "type": "text",
            "mode": "r",
        },
        {
            "id": "minimumAuthenticationLevel",
            "label": "Minimum authentication level",
            "select_variable": "minimumAuthenticationLevel_values",
            "type": "selection",
            "mode": "w",
        },
        {
            "id": "authenticationLevelGuide",
            "label": "Authentication level guide",
            "type": "text",
            "mode": "r",
        },
        {"id": "useSession", "label": "Use Session", "type": "boolean", "mode": "w"},
        {"id": "renew", "label": "Renew", "type": "boolean", "mode": "w"},
        {"id": "gateway", "label": "Gateway", "type": "boolean", "mode": "w"},
        {
            "id": "internalMapping",
            "label": "Use internal ECAS mapping",
            "type": "boolean",
            "mode": "w",
        },
        {
            "id": "verifySslCertificate",
            "label": "Verify TLS certificates",
            "type": "boolean",
            "mode": "w",
        },
        {
            "id": "requestTimeout",
            "label": "CAS request timeout seconds",
            "type": "int",
            "mode": "w",
        },
        {
            "id": "pgtCallbackTimeout",
            "label": "PGT callback wait seconds",
            "type": "int",
            "mode": "w",
        },
        {
            "id": "acceptAnyProxy",
            "label": "Accept any proxy chain",
            "type": "boolean",
            "mode": "w",
        },
        {
            "id": "allowedProxyChains",
            "label": "Allowed proxy chains",
            "type": "lines",
            "mode": "w",
        },
    )

    def __init__(self, id, title=None):
        self._setId(id)
        self.title = title or ""
        self._ecas_id = PersistentMapping()
        self._pgtStorage = PersistentMapping()  # pgtIou -> {pgt, created}
        self._sessionStorage = PersistentMapping()  # ticket/session mappings

    def _storageLock(self):
        lock = getattr(self, "_v_storageLock", None)
        if lock is None:
            lock = threading.RLock()
            self._v_storageLock = lock
        return lock

    def _volatileStorage(self):
        storage = getattr(self, "_v_casStorage", None)
        if storage is None:
            storage = {
                "pgt": {},
                "id_to_session": {},
                "revoked_sessions": {},
            }
            self._v_casStorage = storage
        return storage

    def _cleanup_storage(self):
        """Expire volatile fallback entries.

        Runtime CAS state must not be stored in ZODB: every login/logout would
        mutate the PAS plugin object and create conflict errors on high traffic.
        Redis entries expire via SETEX; this only cleans the in-process fallback.
        """
        now = time.time()
        with self._storageLock():
            storage = self._volatileStorage()
            for key, value in list(storage["pgt"].items()):
                if now - value.get("created", 0) > self.pgtStorageTimeout:
                    del storage["pgt"][key]
            for name in ("id_to_session", "revoked_sessions"):
                for key, value in list(storage[name].items()):
                    if now - value.get("created", 0) > self.sessionMappingTimeout:
                        del storage[name][key]

    def _redisClient(self):
        url = os.environ.get("REDIS_URL")
        if not url:
            return None
        disabled_until = getattr(self, "_v_redisDisabledUntil", 0)
        if disabled_until and disabled_until > time.time():
            return None
        client = getattr(self, "_v_redisClient", None)
        if client is None:
            try:
                import redis

                client = redis.from_url(url)
            except Exception:
                LOG.debug("Could not create Redis CAS cache client", exc_info=True)
                self._v_redisDisabledUntil = time.time() + 60
                return None
            self._v_redisClient = client
        return client

    def _cacheKey(self, bucket, key):
        return "%s:%s:%s" % (CAS_CACHE_PREFIX, bucket, key)

    def _cacheSet(self, bucket, key, value, ttl):
        ttl = max(1, int(ttl))
        client = self._redisClient()
        if client is not None:
            try:
                client.setex(self._cacheKey(bucket, key), ttl, value)
                return
            except Exception:
                LOG.debug("Redis CAS cache write failed", exc_info=True)
                self._v_redisDisabledUntil = time.time() + 60
        with self._storageLock():
            self._cleanup_storage()
            self._volatileStorage()[bucket][key] = {
                "value": value,
                "created": time.time(),
            }

    def _cacheGet(self, bucket, key):
        client = self._redisClient()
        if client is not None:
            try:
                value = client.get(self._cacheKey(bucket, key))
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                return value
            except Exception:
                LOG.debug("Redis CAS cache read failed", exc_info=True)
                self._v_redisDisabledUntil = time.time() + 60
        with self._storageLock():
            self._cleanup_storage()
            entry = self._volatileStorage()[bucket].get(key)
            return entry and entry.get("value")

    def _cacheDelete(self, bucket, key):
        client = self._redisClient()
        if client is not None:
            try:
                client.delete(self._cacheKey(bucket, key))
            except Exception:
                LOG.debug("Redis CAS cache delete failed", exc_info=True)
                self._v_redisDisabledUntil = time.time() + 60
        with self._storageLock():
            self._volatileStorage()[bucket].pop(key, None)

    def _cacheExists(self, bucket, key):
        return self._cacheGet(bucket, key) is not None

    def _cas_client(self, service=None, validation=False, target_service=None):
        if CASClient is None:
            raise RuntimeError("python-cas is not installed")
        server_url = (
            self.casServerValidationUrl
            if validation and self.casServerValidationUrl
            else self.casServerUrlPrefix
        )
        kwargs = {
            "version": 3 if self.ticketValidationSpecification == "CAS 3.0" else 2,
            "server_url": server_url.rstrip("/") + "/",
            "service_url": target_service or service or self.getService(raw=True),
            "renew": bool(self.renew),
            "verify_ssl_certificate": bool(self.verifySslCertificate),
            "session": _TimeoutSession(int(self.requestTimeout or 0)),
        }
        proxy_callback = self.getProxyCallbackUrl()
        if proxy_callback:
            kwargs["proxy_callback"] = proxy_callback
        client = CASClient(**kwargs)
        if validation:
            client.url_suffix = self.serviceValidationEndpoint
        return client

    def _isBdrDeployment(self):
        return REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR

    def _getRequestSession(self, request=None, create=False):
        request = request or getattr(self, "REQUEST", None)
        session = getattr(request, "SESSION", None) if request is not None else None
        if session is not None:
            return session
        sdm = getattr(self, "session_data_manager", None)
        return sdm.getSessionData(create=create) if sdm is not None else None

    def _getSessionKey(self, session):
        if hasattr(session, "getContainerKey"):
            return session.getContainerKey()
        if hasattr(session, "getId"):
            return session.getId()
        return None

    def _rotateSession(self, request, session):
        """Give the browser a fresh session id for a newly established login.

        ``session.clear()`` empties a Beaker session but keeps its id and
        cookie, so without this the id survives both login (session fixation)
        and single logout - and a session revoked by ``logoutCallback`` would
        keep invalidating the user's next login until the revocation entry
        expired.  Returns the session to carry on with.
        """
        invalidate = getattr(session, "invalidate", None)
        if invalidate is None:
            return session
        try:
            invalidate()
        except Exception:
            LOG.warning("Could not rotate CAS session id", exc_info=True)
            return session
        # Zope's session data manager hands out a new object on invalidation;
        # the Beaker wrapper mutates in place and is still usable.
        return self._getRequestSession(request, create=True) or session

    security.declarePrivate("extractCredentials")

    def extractCredentials(self, request):
        creds = {}
        if not self._isBdrDeployment():
            return None
        logout_request = request.form.get("logoutRequest", "")
        if logout_request:
            self.logoutCallback(logout_request)
            return creds

        session = self._getRequestSession(request, create=False)
        assertion = self.getAssertion(session)
        if not assertion:
            ticket = request.form.get("ticket") or request.get("ticket")
            if not ticket:
                return None
            service = self.getService(raw=True)
            try:
                assertion = self.validateServiceTicket(service, ticket)
            except Exception:
                LOG.warning("CAS service ticket validation failed", exc_info=True)
                return None

            if session is None:
                session = self._getRequestSession(request, create=True)
            if session is not None:
                session = self._rotateSession(request, session)
                session_id = self._getSessionKey(session)
                if session_id:
                    self._addSession(ticket, session_id)
                    # The user just re-authenticated against CAS, so a stale
                    # revocation must not follow them into the new session.
                    self._clearRevocation(session_id)
                if self.useSession:
                    session.set(self.CAS_ASSERTION, assertion)
            else:
                LOG.warning(
                    "CAS assertion validated but no session data could be created"
                )
            self._mapAssertionUser(assertion)

        principal = assertion.getPrincipal()
        creds["login"] = self._getLoginFromPrincipal(principal)
        creds["display_name"] = self._getDisplayNameFromPrincipal(principal)
        return creds

    def _identifierFromPrincipal(self, principal, identifier):
        meta = principal.meta or {}
        moniker = principal.id or meta.get("moniker") or meta.get("domainUsername")
        email = meta.get("email") or meta.get("mail")
        if not email and is_email(moniker):
            email = moniker
        ecas_id = principal.ecas_id or meta.get("uid") or meta.get("user")
        if identifier == "email" and email:
            return email
        if identifier == "moniker" and moniker:
            return moniker
        if identifier == "ecas_id" and ecas_id:
            return ecas_id
        return ecas_id or email or moniker

    def _getLoginFromPrincipal(self, principal):
        return self._identifierFromPrincipal(principal, self.loginIdentifier)

    def _getDisplayNameFromPrincipal(self, principal):
        # PAS uses the display name as the user *name* while the login is the
        # user *id*.  Reportek compares getUserName() against stored ids in
        # several places (envelope authors, comment owners), so the two must
        # stay identical unless an operator explicitly opts out.
        if self.displayIdentifier in ("login", "", None):
            return self._getLoginFromPrincipal(principal)
        return self._identifierFromPrincipal(principal, self.displayIdentifier)

    security.declarePrivate("authenticateCredentials")

    def authenticateCredentials(self, credentials):
        if credentials.get("extractor") != self.getId():
            return None
        login = credentials.get("login")
        if not login:
            return None
        return login, credentials.get("display_name") or login

    security.declarePrivate("challenge")

    def challenge(self, request, response, **kw):
        if not self._isBdrDeployment():
            return 0
        session = self._getRequestSession(request, create=False)
        if session:
            session.set(self.CAS_ASSERTION, None)
        if not self.casServerUrlPrefix:
            return 0
        client = self._cas_client(service=self.getService(raw=True))
        url = client.get_login_url()
        if self.gateway and "gateway=" not in url:
            url += ("&" if "?" in url else "?") + "gateway=true"
        response.redirect(url, lock=1)
        return 1

    security.declarePrivate("resetCredentials")

    def resetCredentials(self, request, response):
        if not self._isBdrDeployment():
            return 0
        session = self._getRequestSession(request, create=False)
        if session is not None:
            session.clear()
            # Drop the id as well, so the logged-out cookie cannot be reused.
            self._rotateSession(request, session)
        if self.casServerUrlPrefix:
            client = self._cas_client(service=self.getService(raw=True))
            response.redirect(
                client.get_logout_url(redirect_url=self.getService(raw=True)), lock=1
            )
            return 1
        return 0

    security.declarePublic("proxyCallback")

    def proxyCallback(self, pgtId=None, pgtIou=None):
        if pgtId and pgtIou:
            self._cacheSet("pgt", pgtIou, pgtId, self.pgtStorageTimeout)
            return (
                '<?xml version="1.0"?>'
                '<casClient:proxySuccess xmlns:casClient="http://www.yale.edu/tp/casClient" />'
            )
        return "success"

    security.declarePublic("logoutCallback")

    def logoutCallback(self, logoutRequest=None):
        logoutRequest = logoutRequest or self.REQUEST.form.get("logoutRequest", "")
        try:
            root = ElementTree.fromstring(
                logoutRequest.encode("utf-8")
                if isinstance(logoutRequest, str)
                else logoutRequest
            )
        except Exception:
            LOG.warning("Invalid CAS single logout request", exc_info=True)
            return "Invalid logout request."
        session_index = None
        for element in root.iter():
            if element.tag.endswith("SessionIndex"):
                session_index = element.text
                break
        if not session_index:
            return "No session id found."
        session_id = self._getSessionId(session_index)
        self._removeByMappingId(session_index)
        if session_id:
            self._revokeSession(session_id)
            sdm = getattr(self, "session_data_manager", None)
            session = sdm.getSessionDataByKey(session_id) if sdm else None
            if session:
                session.clear()
                try:
                    import transaction

                    transaction.commit()
                except Exception:
                    LOG.debug(
                        "Could not commit CAS logout session invalidation",
                        exc_info=True,
                    )
        return "Logout success."

    security.declarePublic("validateProxyTicket")

    def validateProxyTicket(self, ticket):
        try:
            assertion = self.validateServiceTicket(
                self.getService(raw=True), ticket, proxy=True
            )
            return True, assertion
        except Exception:
            LOG.warning("CAS proxy ticket validation failed", exc_info=True)
            return False, None

    def validateServiceTicket(self, service, ticket, proxy=False):
        client = self._cas_client(service=service, validation=True)
        if proxy:
            client.url_suffix = "proxyValidate"
        response = client.get_verification_response(ticket)
        user, attributes, pgtiou = self._parse_validation_response(response)
        LOG.debug("CAS validation response user=%r attributes=%r", user, attributes)
        if not user:
            raise ValueError("CAS server did not validate ticket")
        self._validateAuthenticationLevel(attributes or {})
        pgt = self._retrievePgt(pgtiou) if pgtiou else None
        principal = self._principal_from_cas(user, attributes or {}, pgt)
        return ReportekCASAssertion(principal)

    def _parse_validation_response(self, response):
        root = ElementTree.fromstring(response)
        success = None
        failure = None
        for element in root.iter():
            if element.tag.endswith("authenticationSuccess"):
                success = element
                break
            if element.tag.endswith("authenticationFailure"):
                failure = element
        if failure is not None:
            raise ValueError(
                "CAS authentication failure: %s" % (failure.get("code") or "unknown")
            )
        if success is None:
            raise ValueError("CAS authentication response missing success element")
        data = {}
        for element in success.iter():
            tag = element.tag.split("}")[-1]
            if tag not in ("authenticationSuccess", "attributes") and element.text:
                if tag in data:
                    current = data[tag]
                    if isinstance(current, list):
                        current.append(element.text)
                    else:
                        data[tag] = [current, element.text]
                else:
                    data[tag] = element.text
        return data.get("user"), data, data.get("proxyGrantingTicket")

    def _validateAuthenticationLevel(self, attributes):
        required_name = self.minimumAuthenticationLevel or "BASIC"
        if required_name not in AUTHENTICATION_LEVELS:
            LOG.warning(
                "minimumAuthenticationLevel %r is not one of %s; "
                "no authentication level requirement is enforced",
                required_name,
                sorted(AUTHENTICATION_LEVELS),
            )
        required = AUTHENTICATION_LEVELS.get(required_name, 0)
        actual = attributes.get("authenticationLevel")

        if required <= 0:
            # BASIC is the default and means "no additional requirement".
            # EU Login keeps adding level names (STRONG for eID, ...) that we
            # cannot rank, and rejecting them here would lock out every user
            # of that login method.  Record it and let the login through.
            if actual not in AUTHENTICATION_LEVELS:
                LOG.info(
                    "CAS authenticationLevel %r is not ranked; not enforced "
                    "because minimumAuthenticationLevel is %s",
                    actual,
                    required_name,
                )
            return

        if actual not in AUTHENTICATION_LEVELS:
            raise ValueError(
                "CAS authentication level missing or unsupported: %r "
                "(minimum required: %s)" % (actual, required_name)
            )
        if AUTHENTICATION_LEVELS[actual] < required:
            raise ValueError(
                "CAS authentication level %s is below required %s"
                % (actual, required_name)
            )

    def _principal_from_cas(self, user, attributes, pgt=None):
        ecas_id = attributes.get("user") or user
        moniker = (
            attributes.get("moniker")
            or attributes.get("uid")
            or attributes.get("username")
            or user
        )
        meta = {
            "user": attributes.get("user"),
            "moniker": attributes.get("moniker"),
            "authenticationLevel": attributes.get("authenticationLevel"),
        }
        meta.update(attributes)
        principal = ReportekCASPrincipal(
            id=moniker,
            ecas_id=ecas_id,
            meta=meta,
            pgt=pgt,
            plugin=self,
        )
        return principal

    def _retrievePgt(self, pgtiou):
        deadline = time.time() + max(0, int(self.pgtCallbackTimeout))
        while time.time() <= deadline:
            pgt = self._cacheGet("pgt", pgtiou)
            if pgt:
                return pgt
            time.sleep(0.1)
        raise ValueError("CAS PGT callback did not provide a matching PGT")

    def getProxyTicketFor(self, pgt, service):
        client = self._cas_client(target_service=service)
        return client.get_proxy_ticket(pgt)

    def getLoginURL(self):
        return urljoin(self.casServerUrlPrefix.rstrip("/") + "/", "login")

    def getLogoutURL(self):
        client = self._cas_client(service=self.getService(raw=True))
        return client.get_logout_url(redirect_url=self.getService(raw=True))

    def getService(self, raw=False):
        if self.serviceUrl:
            service = self.serviceUrl
        else:
            request = self.REQUEST
            url = request.get("ACTUAL_URL", request.get("URL", ""))
            query = request.get("QUERY_STRING", "")
            service = _strip_ticket("%s?%s" % (url, query) if query else url)
        return service if raw else service

    def getProxyCallbackUrl(self):
        return (
            self.proxyCallbackUrlPrefix
            and "%s/proxyCallback" % self.proxyCallbackUrlPrefix.rstrip("/")
            or ""
        )

    def getAssertion(self, session):
        if self.useSession and session:
            if self._isSessionRevoked(session):
                session.clear()
                return None
            assertion = session.get(self.CAS_ASSERTION)
            if isinstance(assertion, ReportekCASAssertion):
                return assertion
        return None

    def getAssertionFromSession(self):
        return self.getAssertion(self._getRequestSession(create=False))

    def _addSession(self, mapping_id, session_id):
        self._cacheSet(
            "id_to_session", mapping_id, session_id, self.sessionMappingTimeout
        )

    def _revokeSession(self, session_id):
        self._cacheSet("revoked_sessions", session_id, "1", self.sessionMappingTimeout)

    def _clearRevocation(self, session_id):
        self._cacheDelete("revoked_sessions", session_id)

    def _isSessionRevoked(self, session):
        session_id = self._getSessionKey(session)
        return bool(session_id and self._cacheExists("revoked_sessions", session_id))

    def _getSessionId(self, mapping_id):
        return self._cacheGet("id_to_session", mapping_id)

    def _removeByMappingId(self, mapping_id):
        self._cacheDelete("id_to_session", mapping_id)

    def _mapAssertionUser(self, assertion):
        if not self.internalMapping:
            return
        principal = assertion.getPrincipal()
        username = principal.id
        ecas_id = principal.ecas_id or username
        self.mapUser(self, ecas_id, username)
        email = (
            principal.meta.get("email") or principal.meta.get("mail")
            if principal.meta
            else None
        )
        if email:
            self.mapUser(self, ecas_id, email)

    def invalidateOlderMapping(self, c_ecas_id, username):
        res = []
        for ecas_id, user in list(self._ecas_id.items()):
            if ecas_id == c_ecas_id:
                continue
            if is_email(username):
                if user.email and user.email.lower() == username.lower():
                    user._email = None
                    res.append(ecas_id)
            elif user.username == username:
                user._username = None
                res.append(ecas_id)
        return res

    def mapUser(self, ecas, ecas_id, username):
        ecas_user = ecas._ecas_id.get(ecas_id)
        if not ecas_user:
            ecas_user = EcasClient(ecas_id, username)
            ecas._ecas_id[ecas_id] = ecas_user
            self.invalidateOlderMapping(ecas_id, username)
        elif is_email(username):
            ecas_user._email = username
        else:
            ecas_user._username = username

    def getEcasUserId(self, username):
        if self.internalMapping:
            for ecas_id, user in self._ecas_id.items():
                if is_email(username):
                    if user.email and user.email.lower() == username.lower():
                        return ecas_id
                elif user.username == username:
                    return ecas_id
        assertion = self.getAssertionFromSession()
        if assertion:
            return assertion.getPrincipal().ecas_id
        return username

    def getEcasUser(self, username):
        assertion = self.getAssertionFromSession()
        if assertion:
            meta = dict(assertion.getPrincipal().meta or {})
            meta["ecas_id"] = assertion.getPrincipal().ecas_id
            return meta
        return {}

    def getEcasIDUser(self, ecas_id):
        return self._ecas_id.get(ecas_id)

    def getEcasIDEmail(self, ecas_id):
        if self.internalMapping:
            user = self.getEcasIDUser(ecas_id)
            if user:
                return user.email
        return "Internal ECAS mapping disabled"

    def getEcasIDUsername(self, ecas_id):
        user = self.getEcasIDUser(ecas_id)
        if user:
            return user.username
        return None


classImplements(
    ReportekCASPlugin,
    IExtractionPlugin,
    IChallengePlugin,
    ICredentialsResetPlugin,
    IAuthenticationPlugin,
)

InitializeClass(ReportekCASPlugin)


manage_addReportekCASPluginForm = PageTemplateFile(
    "zpt/reportekcasAdd.zpt",
    globals(),
    __name__="manage_addReportekCASPluginForm",
)


def manage_addReportekCASPlugin(dispatcher, id=ECAS_ID, title="", RESPONSE=None):
    plugin = ReportekCASPlugin(id, title)
    dispatcher._setObject(id, plugin)
    if RESPONSE is not None:
        RESPONSE.redirect(
            "%s/manage_main?manage_tabs_message=%s"
            % (dispatcher.absolute_url(), "ReportekCASPlugin+added.")
        )


# Backwards-compatible name used by the migration/import script.
addReportekCASPlugin = manage_addReportekCASPlugin
