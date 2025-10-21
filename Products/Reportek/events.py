from zope.interface import implementer
from zope.interface.interfaces import ObjectEvent

from Products.Reportek.interfaces import (
    IAuditAssignedEvent,
    IAuditUnassignedEvent,
    IEnvelopeEvent,
    IEnvelopeReleasedEvent,
    IEnvelopeUnReleasedEvent,
)


@implementer(IEnvelopeEvent)
class EnvelopeEvent(ObjectEvent):
    """Abstract Envelope Event"""


@implementer(IEnvelopeReleasedEvent)
class EnvelopeReleasedEvent(EnvelopeEvent):
    """Envelope released event"""


@implementer(IEnvelopeUnReleasedEvent)
class EnvelopeUnReleasedEvent(EnvelopeEvent):
    """Envelope unreleased event"""


@implementer(IAuditAssignedEvent)
class AuditAssignedEvent(EnvelopeEvent):
    """Audit assigned event"""


@implementer(IAuditUnassignedEvent)
class AuditUnassignedEvent(EnvelopeEvent):
    """Audit unassigned event"""
