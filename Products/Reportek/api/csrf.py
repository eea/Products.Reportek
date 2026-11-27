"""CSRF protection for the API called by other services.

The registries (bdr-registry, european.cache.registry) call these endpoints
from their servers with HTTP Basic auth and no form token. Browsers mark the
requests they send with ``Origin`` (cross-site and all POSTs) or
``Sec-Fetch-Site``; HTTP clients like ``requests`` send neither. So a request
with Basic auth and none of these headers is a service and skips the token
check; any other request must carry a valid ``_authenticator`` token.
"""

import plone.protect.interfaces
from plone.protect import CheckAuthenticator
from zope.interface import alsoProvides

BROWSER_HEADERS = ("Origin", "Sec-Fetch-Site")


def is_service_request(request):
    """Whether the request comes from a service: Basic auth, not a browser."""
    authorization = getattr(request, "_auth", None) or ""
    if not authorization.lower().startswith("basic "):
        return False
    return not any(request.getHeader(name) for name in BROWSER_HEADERS)


def protect(request):
    """Let a service through; require the form token from anybody else."""
    if is_service_request(request):
        alsoProvides(request, plone.protect.interfaces.IDisableCSRFProtection)
    else:
        CheckAuthenticator(request)
