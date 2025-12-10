# -*- coding: utf-8 -*-
from DateTime import DateTime
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse

from Products.Five import BrowserView


@implementer(IPublishTraverse)
class ModificationTimeView(BrowserView):
    """Provides safe access to object modification time.

    This view exposes _p_mtime which is protected from direct access
    in restricted code (Page Templates, Python Scripts) since
    AccessControl blocks all attributes starting with underscore.
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

        mtime = getattr(self.context, "_p_mtime", None)
        if mtime is not None and mtime > 0:
            return DateTime(mtime)
        return None

    def date(self):
        """Returns modification date as formatted string."""
        mtime = getattr(self.context, "_p_mtime", None)
        if mtime is not None and mtime > 0:
            dt = DateTime(mtime)
            return dt.Date()
        return "not available"

    def iso(self):
        """Returns modification time in ISO format."""
        mtime = getattr(self.context, "_p_mtime", None)
        if mtime is not None and mtime > 0:
            dt = DateTime(mtime)
            return dt.ISO()
        return None
