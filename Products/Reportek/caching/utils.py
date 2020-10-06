# -*- coding: utf-8 -*-
import datetime
import logging
import time
import wsgiref.handlers

import dateutil.parser
import dateutil.tz
from AccessControl.PermissionRole import rolesForPermissionOn
from OFS.interfaces import IApplication, IFolder
from plone.registry.interfaces import IRegistry
from z3c.caching.interfaces import ILastModified
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility

LASTMODIFIED_ANNOTATION_KEY = 'plone.app.caching.operations.lastmodified'
_marker = object()

logger = logging.getLogger('Products.Reportek.caching')

#
# Operation helpers, used in the implementations of interceptResponse() and
# modifyResponse().
#
# These all take three parameters, published, request and response, as well
# as any additional keyword parameters required.
#


def setCacheHeaders(
    published,
    request,
    response,
    maxage=None,
    smaxage=None,
    lastModified=None,
    vary=None,
):
    """General purpose dispatcher to set various cache headers

    ``maxage`` is the cache timeout value in seconds
    ``smaxage`` is the proxy cache timeout value in seconds.
    ``lastModified`` is a datetime object for the last modified time
    ``vary`` is a vary header string
    """

    if maxage:
        cacheInBrowserAndProxy(
            published,
            request,
            response,
            maxage,
            smaxage=smaxage,
            lastModified=lastModified,
            vary=vary,
        )

    elif smaxage:
        cacheInProxy(
            published,
            request,
            response,
            smaxage,
            lastModified=lastModified,
            vary=vary,
        )

    elif lastModified:
        cacheInBrowser(
            published,
            request,
            response,
            lastModified=lastModified,
        )

    else:
        doNotCache(published, request, response)


def doNotCache(published, request, response):
    """Set response headers to ensure that the response is not cached by
    web browsers or caching proxies.

    This is an IE-safe operation. Under certain conditions, IE chokes on
    ``no-cache`` and ``no-store`` cache-control tokens so instead we just
    expire immediately and disable validation.
    """

    if response.getHeader('Last-Modified'):
        del response.headers['last-modified']

    response.setHeader('Expires', formatDateTime(getExpiration(0)))
    response.setHeader('Cache-Control', 'max-age=0, must-revalidate, private')


def cacheInBrowser(published, request, response, lastModified=None):
    """Set response headers to indicate that browsers should cache the
    response but expire immediately and revalidate the cache on every
    subsequent request.

    ``lastModified`` is a datetime object

    If neither etag nor lastModified is given then no validation is
    possible and this becomes equivalent to doNotCache()
    """

    if lastModified is not None:
        response.setHeader('Last-Modified', formatDateTime(lastModified))
    elif response.getHeader('Last-Modified'):
        del response.headers['last-modified']

    response.setHeader('Expires', formatDateTime(getExpiration(0)))
    response.setHeader('Cache-Control', 'max-age=0, must-revalidate, private')


def cacheInProxy(
    published,
    request,
    response,
    smaxage,
    lastModified=None,
    vary=None,
):
    """Set headers to cache the response in a caching proxy.

    ``smaxage`` is the timeout value in seconds.
    ``lastModified`` is a datetime object for the last modified time
    ``vary`` is a vary header string
    """

    if lastModified is not None:
        response.setHeader(
            'Last-Modified',
            formatDateTime(lastModified),
        )
    elif response.getHeader('Last-Modified'):
        del response.headers['last-modified']

    if vary is not None:
        response.setHeader('Vary', vary)

    response.setHeader('Expires', formatDateTime(getExpiration(0)))
    response.setHeader(
        'Cache-Control',
        'max-age=0, s-maxage={0}, must-revalidate'.format(smaxage),
    )


def cacheInBrowserAndProxy(
    published,
    request,
    response,
    maxage,
    smaxage=None,
    lastModified=None,
    vary=None,
):
    """Set headers to cache the response in the browser and caching proxy if
    applicable.

    ``maxage`` is the timeout value in seconds
    ``smaxage`` is the proxy timeout value in seconds
    ``lastModified`` is a datetime object for the last modified time
    ``vary`` is a vary header string
    """

    if lastModified is not None:
        response.setHeader('Last-Modified', formatDateTime(lastModified))
    elif response.getHeader('Last-Modified'):
        del response.headers['last-modified']

    if vary is not None:
        response.setHeader('Vary', vary)

    response.setHeader('Expires', formatDateTime(getExpiration(maxage)))

    if smaxage is not None:
        maxage = '{0}, s-maxage={1}'.format(maxage, smaxage)

    # Substituting proxy-validate in place of must=revalidate here because of
    # Safari bug
    # https://bugs.webkit.org/show_bug.cgi?id=13128
    response.setHeader(
        'Cache-Control',
        'max-age={0}, proxy-revalidate, public'.format(maxage),
    )


def cachedResponse(
    published,
    request,
    response,
    status,
    headers,
    body,
    gzip=False,
):
    """Returned a cached page. Modifies the response (status and headers)
    and returns the cached body.

    ``status`` is the cached HTTP status
    ``headers`` is a dictionary of cached HTTP headers
    ``body`` is a cached response body
    ``gzip`` should be set to True if the response is to be gzipped
    """

    response.setStatus(status)

    for k, v in headers.items():
        response.setHeader(k, v)

    response.setHeader('X-RAMCache', PAGE_CACHE_KEY, literal=1)

    if not gzip:
        response.enableHTTPCompression(request, disable=True)
    else:
        response.enableHTTPCompression(request)

    return body


def notModified(published, request, response, lastModified=None):
    """Return a ``304 NOT MODIFIED`` response. Modifies the response (status)
    and returns an empty body to indicate the request should be interrupted.

    ``lastModified`` is the last modified date to set on the response

    """

    # Specs say that Last-Modified MUST NOT be included in a 304
    # and Cache-Control/Expires MUST NOT be included unless they
    # differ from the original response.  We'll delete all, including
    # Expires although technically it should be included.  This is
    # probably okay since in the original we only include Expires
    # along with a Cache-Control and HTTP/1.1 clients will always
    # use the later over any Expires header anyway.  HTTP/1.0 clients
    # never send conditional requests so they will never see this.
    #
    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
    #
    if response.getHeader('Last-Modified'):
        del response.headers['last-modified']
    if response.getHeader('Expires'):
        del response.headers['expires']
    if response.getHeader('Cache-Control'):
        del response.headers['cache-control']

    response.setStatus(304)
    return u''


#
# Cache checks
#

def cacheStop(request, rulename):
    """Check for any cache stop variables in the request.
    """

    # Only cache GET requests
    if request.get('REQUEST_METHOD') != 'GET':
        return True

    registry = getUtility(IRegistry)
    if registry is None:
        return False

    variables = ['statusmessages', 'SearchableText']
    return set(variables) & set(request.keys())


def isModified(request, lastModified=None):
    """Return True or False depending on whether the published resource has
    been modified.


    ``lastModified`` is the current last-modified datetime, to be checked
    against the If-Modified-Since header.
    """

    if not lastModified:
        return True

    ifModifiedSince = request.getHeader('If-Modified-Since', None)
    ifNoneMatch = request.getHeader('If-None-Match', None)

    if ifModifiedSince is None and ifNoneMatch is None:
        return True


    # Check the modification date
    if ifModifiedSince and lastModified is not None:

        # Attempt to get a date

        ifModifiedSince = ifModifiedSince.split(';')[0]
        ifModifiedSince = parseDateTime(ifModifiedSince)

        if ifModifiedSince is None:
            return True

        # has content been modified since the if-modified-since time?
        try:
            # browser only knows the date to one second resolution
            delta_sec = datetime.timedelta(seconds=1)
            if (lastModified - ifModifiedSince) > delta_sec:
                return True
        except TypeError:
            logger.exception('Could not compare dates')

    # XXX Do we really want the default here to be false?
    return False


def visibleToRole(published, role, permission='View'):
    """Determine if the published object would be visible to the given
    role.

    ``role`` is a role name, e.g. ``Anonymous``.
    ``permission`` is the permission to check for.
    """
    return role in rolesForPermissionOn(permission, published)

#
# Basic helper functions
#


def getContext(published, marker=(IFolder, IApplication,)):
    """Given a published object, attempt to look up a context

    ``published`` is the object that was published.
    ``marker`` is a marker interface to look for

    Returns an item providing ``marker`` or None, if it cannot be found.
    """

    if not isinstance(marker, (list, tuple,)):
        marker = (marker,)

    def checkType(context):
        for m in marker:
            if m.providedBy(context):
                return True
        return False

    while (
        published is not None and
        not checkType(published) and
        getattr(published, '__parent__')
    ):
        published = published.__parent__

    if not checkType(published):
        return None

    return published


def formatDateTime(dt):
    """Format a Python datetime object as an RFC1123 date.

    If the datetime object is timezone-naive, it is assumed to be local time.
    """

    # We have to pass local time to format_date_time()

    if dt.tzinfo is not None:
        dt = dt.astimezone(dateutil.tz.tzlocal())

    return wsgiref.handlers.format_date_time(time.mktime(dt.timetuple()))


def parseDateTime(str):
    """Return a Python datetime object from an an RFC1123 date.

    Returns a datetime object with a timezone. If no timezone is found in the
    input string, assume local time.
    """

    try:
        dt = dateutil.parser.parse(str)
    except ValueError:
        return None

    if not dt:
        return None

    if dt.tzinfo is None:
        dt = datetime.datetime(dt.year, dt.month, dt.day,
                               dt.hour, dt.minute, dt.second, dt.microsecond,
                               dateutil.tz.tzlocal())

    return dt


def getLastModifiedAnnotation(published, request, lastModified=True):
    """Try to get the last modified date from a request annotation if available,
    otherwise try to get it from published object
    """

    if not lastModified:
        return None

    annotations = IAnnotations(request, None)
    if annotations is not None:
        dt = annotations.get(LASTMODIFIED_ANNOTATION_KEY, _marker)
        if dt is not _marker:
            return dt

    dt = getLastModified(published, lastModified=lastModified)

    if annotations is not None:
        annotations[LASTMODIFIED_ANNOTATION_KEY] = dt

    return dt


def getLastModified(published, lastModified=True):
    """Get a last modified date or None.

    If an ``ILastModified`` adapter can be found, and returns a date that is
    not timezone aware, assume it is local time and add timezone.
    """

    if not lastModified:
        return None

    lastModified = ILastModified(published, None)
    if lastModified is None:
        return None

    dt = lastModified()
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = datetime.datetime(dt.year, dt.month, dt.day,
                               dt.hour, dt.minute, dt.second, dt.microsecond,
                               dateutil.tz.tzlocal())

    return dt


def getExpiration(maxage):
    """Get an expiration date as a datetime in the local timezone.

    ``maxage`` is the maximum age of the item, in seconds. If it is 0 or
    negative, return a date ten years in the past.
    """

    now = datetime.datetime.now()
    if maxage > 0:
        return now + datetime.timedelta(seconds=maxage)
    else:
        return now - datetime.timedelta(days=3650)
