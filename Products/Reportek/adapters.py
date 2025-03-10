from BTrees.OOBTree import OOBTree
from DateTime import DateTime
from persistent.dict import PersistentDict
from zope.annotation.interfaces import IAnnotations
from zope.component import adapts
from zope.interface import implementer

from Products.Reportek.Envelope import Envelope
from Products.Reportek.interfaces import IAudit

ANNOTATION_KEY = "Products.Reportek.audit"
DT_FORMAT = "%d/%m/%Y %H:%M"


@implementer(IAudit)
class Audit:
    adapts(Envelope)

    def __init__(self, context):
        self.context = context
        annotations = IAnnotations(self.context)
        if ANNOTATION_KEY not in annotations:
            annotations[ANNOTATION_KEY] = OOBTree()
        self._audit_metadata = annotations[ANNOTATION_KEY]

    def get_audit_metadata(self):
        """Get audit metadata"""

        return dict(self._audit_metadata.get("verification_settings", {}))

    def set_audit_metadata(self, data):
        """Set audit metadata"""
        self._audit_metadata["verification_settings"] = PersistentDict(data)
