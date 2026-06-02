# -*- coding: utf-8 -*-
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse

from Products.Five import BrowserView
from Products.Reportek.modification_date import get_reportek_modification_date


@implementer(IPublishTraverse)
class ModificationTimeView(BrowserView):
    """Provides safe access to object modification time.

    This view exposes the persisted Reportek business modification date
    for restricted code (Page Templates, Python Scripts).
    """

    def __init__(self, context, request):
        super().__init__(context, request)
        self._subpath = None

    def publishTraverse(self, request, name):
        """Handle path traversal to allow @@modification_time/date etc."""
        self._subpath = name
        return self

    def __call__(self):
        """Returns modification time or subpath result."""
        if self._subpath:
            method = getattr(self, self._subpath, None)
            if method and callable(method):
                return method()
            return "not available"

        return get_reportek_modification_date(self.context)

    def date(self):
        """Returns modification date as formatted string."""
        dt = get_reportek_modification_date(self.context)
        if dt is not None:
            return dt.Date()
        return "not available"

    def iso(self):
        """Returns modification time in ISO format."""
        dt = get_reportek_modification_date(self.context)
        if dt is not None:
            return dt.ISO()
        return None
