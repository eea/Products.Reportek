from zope.interface import implementer
from zope.interface.interfaces import ObjectEvent

from Products.Reportek.interfaces import (
    IAuditAssignedEvent,
    IAuditUnassignedEvent,
    IEnvelopeEvent,
    IEnvelopeReleasedEvent,
    IEnvelopeUnReleasedEvent,
    ILocalRolesChangedEvent,
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


@implementer(ILocalRolesChangedEvent)
class LocalRolesChangedEvent(ObjectEvent):
    """Fired after manage_setLocalRoles / manage_delLocalRoles mutate
    __ac_local_roles__ on an object."""

    def __init__(self, obj, changed_roles):
        ObjectEvent.__init__(self, obj)
        self.changed_roles = frozenset(changed_roles or ())
