import zope.component.interfaces
from zope.interface import implements


class IStatusChangedEvent(zope.component.interfaces.IObjectEvent):
    """An envelope status has changed"""


class StatusChangedEvent(zope.component.interfaces.ObjectEvent):
    """An envelope status has changed"""
    implements(IStatusChangedEvent)
