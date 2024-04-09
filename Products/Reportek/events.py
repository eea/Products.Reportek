from zope.interface.interfaces import ObjectEvent
from Products.Reportek.interfaces import (IEnvelopeEvent,
                                          IEnvelopeReleasedEvent,
                                          IEnvelopeUnReleasedEvent)
from zope.interface import implementer


@implementer(IEnvelopeEvent)
class EnvelopeEvent(ObjectEvent):
    """Abstract Envelope Event"""


@implementer(IEnvelopeReleasedEvent)
class EnvelopeReleasedEvent(EnvelopeEvent):
    """Envelope released event"""


@implementer(IEnvelopeUnReleasedEvent)
class EnvelopeUnReleasedEvent(EnvelopeEvent):
    """Envelope unreleased event"""
