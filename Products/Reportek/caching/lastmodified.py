# -*- coding: utf-8 -*-
from datetime import datetime

from Acquisition import aq_base
from dateutil.tz import tzlocal
from OFS.Image import File
from Products.Reportek.interfaces import (IBaseDelivery, ICollection,
                                          IDocument, IFeedback, IReportekAPI,
                                          IReportekUtilities, IWorkitem)
from z3c.caching.interfaces import ILastModified
from zope.browserresource.interfaces import IResource
from zope.component import adapter
from zope.interface import Interface, implementer
from zope.pagetemplate.interfaces import IPageTemplate

try:
    from zope.dublincore.interfaces import IDCTimes
except ImportError:
    class IDCTimes(Interface):
        pass


@implementer(ILastModified)
@adapter(IPageTemplate)
def PageTemplateDelegateLastModified(template):
    """When looking up an ILastModified for a page template, look up an
    ILastModified for its context. May return None, in which case adaptation
    will fail.
    """
    return ILastModified(template.getParentNode(), None)


@implementer(ILastModified)
class PersistentLastModified(object):
    """General ILastModified adapter for persistent objects that have a
    _p_mtime. Note that we don't register this for IPersistent, because
    that interface is mixed into too many things and may end up taking
    precedence over other adapters. Instead, this can be registered on an
    as-needed basis with ZCML.
    """

    def __init__(self, context):
        self.context = context

    def __call__(self):
        context = aq_base(self.context)
        mtime = getattr(context, '_p_mtime', None)
        if mtime is not None and mtime > 0:
            return datetime.fromtimestamp(mtime, tzlocal())
        return None


@adapter(File)
class OFSFileLastModified(PersistentLastModified):
    """ILastModified adapter for OFS.Image.File
    """


@implementer(ILastModified)
@adapter(IDCTimes)
class DCTimesLastModified(object):
    """ILastModified adapter for zope.dublincore IDCTimes
    """

    def __init__(self, context):
        self.context = context

    def __call__(self):
        return self.context.modified


@implementer(ILastModified)
@adapter(IResource)
class ResourceLastModified(object):
    """ILastModified for Zope 3 style browser resources
    """

    def __init__(self, context):
        self.context = context

    def __call__(self):
        lmt = getattr(self.context.context, 'lmt', None)
        if lmt is not None:
            return datetime.fromtimestamp(lmt, tzlocal())


@implementer(ILastModified)
@adapter(IBaseDelivery)
class BaseDeliveryLastModified(object):
    def __init__(self, context):
        self.context = context

    def __call__(self):
        context = aq_base(self.context)
        mtime = getattr(context, '_p_mtime', None)
        if mtime is not None and mtime > 0:
            return datetime.fromtimestamp(mtime, tzlocal())
        return None


@implementer(ILastModified)
@adapter(IFeedback)
class FeedbackLastModified(object):
    def __init__(self, context):
        self.context = context

    def __call__(self):
        context = aq_base(self.context)
        mtime = getattr(context, '_p_mtime', None)
        if mtime is not None and mtime > 0:
            return datetime.fromtimestamp(mtime, tzlocal())
        return None


@implementer(ILastModified)
@adapter(ICollection)
class CollectionLastModified(object):
    def __init__(self, context):
        self.context = context

    def __call__(self):
        context = aq_base(self.context)
        mtime = getattr(context, '_p_mtime', None)
        if mtime is not None and mtime > 0:
            return datetime.fromtimestamp(mtime, tzlocal())
        return None


@implementer(ILastModified)
@adapter(IDocument)
class DocumentLastModified(object):
    def __init__(self, context):
        self.context = context

    def __call__(self):
        context = aq_base(self.context)
        mtime = getattr(context, '_p_mtime', None)
        if mtime is not None and mtime > 0:
            return datetime.fromtimestamp(mtime, tzlocal())
        return None


@implementer(ILastModified)
@adapter(IWorkitem)
class WorkitemLastModified(object):
    def __init__(self, context):
        self.context = context

    def __call__(self):
        context = aq_base(self.context)
        mtime = getattr(context, '_p_mtime', None)
        if mtime is not None and mtime > 0:
            return datetime.fromtimestamp(mtime, tzlocal())
        return None
