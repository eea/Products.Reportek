# -*- coding: utf-8 -*-
from plone.cachepurging.utils import getPathsToPurge, isCachePurgingEnabled
from Products.Reportek.interfaces import IReportekContent
from z3c.caching.interfaces import IPurgeEvent, IPurgePaths
from z3c.caching.purge import Purge
from zope.annotation.interfaces import IAnnotations
from zope.component import adapter, adapts
from zope.event import notify
from zope.globalrequest import getRequest
from zope.interface import implementer

KEY = "plone.cachepurging.urls"


@adapter(IPurgeEvent)
def queuePurge(event):
    """Find URLs to purge and queue them for later
    """
    # plone.cachepurging queuePurge uses getRequest which returns None,
    # fallback to the REQUEST on the object
    request = getRequest() or getattr(event.object, 'REQUEST', None)
    if request is None:
        return

    annotations = IAnnotations(request, None)
    if annotations is None:
        return

    if not isCachePurgingEnabled():
        return

    paths = annotations.setdefault(KEY, set())
    paths.update(getPathsToPurge(event.object, request))


@implementer(IPurgePaths)
class ObjectViewPurgePaths(object):
    """Purge /view for any content object with the content object's
    default URL
    """

    adapts(IReportekContent)

    def __init__(self, context):
        self.context = context

    def getRelativePaths(self):
        paths = ['index_html', 'overview', 'history_section',
                 'data_quality', 'manage_document']
        return ['/'.join([self.context.absolute_url_path(), p]) for p in paths]

    def getAbsolutePaths(self):
        return []


@adapter(IReportekContent, IPurgeEvent)
def purgeParent(object, IPurgeEvent):
    try:
        parent = getattr(object, '__parent__', object.getParentNode())
    except Exception:
        parent = None
    if parent is not None:
        notify(Purge(parent))
