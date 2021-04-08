import datetime

from plone.caching.interfaces import (ICachingOperation, ICachingOperationType,
                                      _)
from Products.Reportek.caching.utils import (cacheStop, doNotCache,
                                             getLastModifiedAnnotation,
                                             isModified, notModified,
                                             parseDateTime, setCacheHeaders,
                                             visibleToRole)
from zope.component import adapter
from zope.interface import Interface, implementer, provider
from zope.publisher.interfaces.http import IHTTPRequest


@implementer(ICachingOperation)
@adapter(Interface, IHTTPRequest)
@provider(ICachingOperationType)
class BaseCaching(object):
    """A generic caching operation class that can do pretty much all the usual
    caching operations based on options settings. For UI simplicity, it might
    be easier to subclass this in your custom operations to set a few default
    operations.

    Generic options (Default value for each is None):

    ``maxage``
        is the maximum age of the cached item, in seconds..

    ``smaxage``
        is the maximum age of the cached item in proxies, in seconds.

    ``lastModified``
        is a boolean indicating whether to set a Last-Modified header
        and turn on 304 responses.

    ``vary``
        is a string to add as a Vary header value in the response.
    """

    title = _(u'Generic caching')
    description = _(
        u'Through this operation, all standard caching functions '
        u'can be performed via various combinations of the optional '
        u'parameter settings. For most cases, it\'s probably easier '
        u'to use one of the other simpler operations (Strong caching, '
        u'Moderate caching, Weak caching, or No caching).'
    )
    prefix = 'Products.Reportek.caching.baseCaching'
    options = ('maxage', 'smaxage', 'lastModified',
               'vary', 'anonOnly')

    # Default option values
    maxage = smaxage = vary = None
    lastModified = anonOnly = False

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def interceptResponse(self, rulename, response, class_=None):

        # anonOnly = self.anonOnly
        lastModified = self.lastModified

        lastModified = getLastModifiedAnnotation(
            self.published, self.request, lastModified=lastModified)

        # Remove Range from request if the If-Range condition is not fulfilled
        if_range = self.request.environ.get('HTTP_IF_RANGE', '').strip('"')
        if if_range:
            if 'HTTP_RANGE' in self.request.environ:
                if_range_dt = parseDateTime(if_range)
                delta_sec = datetime.timedelta(seconds=1)
                if if_range_dt and (lastModified - if_range_dt) < delta_sec:
                    pass
                else:
                    del self.request.environ['HTTP_RANGE']
            # If-Range check is done here so we could remove it from request
            del self.request.environ['HTTP_IF_RANGE']

        # Check for cache stop request variables
        if cacheStop(self.request, rulename):
            return None

        # Check if this should be a 304 response
        if not isModified(self.request, lastModified=lastModified):
            return notModified(
                self.published,
                self.request,
                response,
                lastModified=lastModified,
            )

        return None

    def modifyResponse(self, rulename, response, class_=None):

        maxage = self.maxage
        smaxage = self.smaxage

        # anonOnly = self.anonOnly
        vary = self.vary

        lastModified = getLastModifiedAnnotation(
            self.published, self.request, self.lastModified)

        # Check for cache stop request variables
        if cacheStop(self.request, rulename):
            # only stop with etags if configured
            return setCacheHeaders(
                self.published,
                self.request,
                response,
            )
            # XXX: should there be an else here? Last modified works without
            #      extra headers.
            #      Are there other config options?

        # Do the maxage/smaxage settings allow for proxy caching?
        proxyCache = smaxage or (maxage and smaxage is None)

        # Check if the content can be cached in shared caches
        public = True
        if proxyCache:
            public = public and visibleToRole(self.published, role='Anonymous')

        if proxyCache and not public:
            # This is private so keep it out of both shared and browser caches
            maxage = smaxage = 0

        setCacheHeaders(
            self.published,
            self.request,
            response,
            maxage=maxage,
            smaxage=smaxage,
            lastModified=lastModified,
            vary=vary,
        )


@provider(ICachingOperationType)
class WeakCaching(BaseCaching):
    """Weak caching operation. A subclass of the generic BaseCaching
    operation to help make the UI approachable by mortals
    """

    title = _(u'Weak caching')
    description = _(
        u'Cache in browser but expire immediately and enable 304 '
        u'responses on subsequent requests. 304\'s require configuration '
        u'of the \'Last-modified\' settings. If '
        u'Last-Modified  header is insufficient to ensure freshness, turn on '
    )
    prefix = 'Products.Reportek.caching.weakCaching'
    sort = 3

    # Configurable options
    options = ('lastModified', 'vary', 'anonOnly')

    # Default option values
    maxage = 0
    smaxage = vary = None
    lastModified = anonOnly = False


@provider(ICachingOperationType)
class ModerateCaching(BaseCaching):
    """Moderate caching operation. A subclass of the generic BaseCaching
    operation to help make the UI approachable by mortals
    """

    title = _(u'Moderate caching')
    description = _(
        u'Cache in browser but expire immediately (same as \'weak caching\'), '
        u'and cache in proxy (default: 24 hrs). '
        u'Use a purgable caching reverse proxy for best results. '
        u'Caution: If proxy cannot be purged, or cannot be configured '
        u'to remove the \'s-maxage\' token from the response, then stale '
        u'responses might be seen until the cached entry expires.')
    prefix = 'Products.Reportek.caching.moderateCaching'
    sort = 2

    # Configurable options
    options = ('smaxage', 'lastModified',
               'vary', 'anonOnly')

    # Default option values
    maxage = 0
    smaxage = 86400
    vary = None
    # lastModified = anonOnly = False
    lastModified = True
    anonOnly = False


@provider(ICachingOperationType)
class StrongCaching(BaseCaching):
    """Strong caching operation. A subclass of the generic BaseCaching
    operation to help make the UI approachable by mortals
    """

    title = _(u'Strong caching')
    description = _(
        u'Cache in browser and proxy (default: 24 hrs). '
        u'Caution: Only use for stable resources '
        u'that never change without changing their URL, or resources '
        u'for which temporary staleness is not critical.'
    )
    prefix = 'Products.Reportek.caching.strongCaching'
    sort = 1

    # Configurable options
    options = ('maxage', 'smaxage', 'lastModified',
               'vary', 'anonOnly')

    # Default option values
    maxage = 86400
    smaxage = etags = vary = None
    lastModified = ramCache = anonOnly = False


@implementer(ICachingOperation)
@provider(ICachingOperationType)
@adapter(Interface, IHTTPRequest)
class NoCaching(object):
    """A caching operation that tries to keep the response
    out of all caches.
    """

    title = _(u'No caching')
    description = _(u'Use this operation to keep the response '
                    u'out of all caches.')
    prefix = 'Products.Reportek.caching.noCaching'
    sort = 4
    options = ()

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def interceptResponse(self, rulename, response):
        return None

    def modifyResponse(self, rulename, response):
        doNotCache(self.published, self.request, response)
