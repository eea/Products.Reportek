"""The meta_type of the content classes is defined once, in constants.py.

The strings are used to look for the objects (the catalog, objectValues, ...)
and stored in the catalog, so they must not change.
"""

import unittest

from Products.Reportek import constants
from Products.Reportek.activity import activity
from Products.Reportek.blob import OfsBlobFile
from Products.Reportek.Collection import Collection
from Products.Reportek.Comment import CommentItem
from Products.Reportek.Document import Document
from Products.Reportek.Envelope import Envelope
from Products.Reportek.Feedback import ReportFeedback
from Products.Reportek.process import process
from Products.Reportek.QAScript import QAScript
from Products.Reportek.Referral import Referral
from Products.Reportek.transition import transition
from Products.Reportek.workitem import workitem

# the class, the constant and the string that is stored in the catalog
META_TYPES = [
    (Collection, constants.METATYPE_COLLECTION, "Report Collection"),
    (Envelope, constants.METATYPE_ENVELOPE, "Report Envelope"),
    (Document, constants.METATYPE_DOCUMENT, "Report Document"),
    (ReportFeedback, constants.METATYPE_FEEDBACK, "Report Feedback"),
    (CommentItem, constants.METATYPE_FEEDBACK_COMMENT, "Report Feedback Comment"),
    (Referral, constants.METATYPE_REFERRAL, "Repository Referral"),
    (OfsBlobFile, constants.METATYPE_BLOB_FILE, "File (Blob)"),
    (QAScript, constants.METATYPE_QASCRIPT, "QAScript"),
    (workitem, constants.METATYPE_WORKITEM, "Workitem"),
    (activity, constants.METATYPE_ACTIVITY, "Activity"),
    (process, constants.METATYPE_PROCESS, "Process"),
    (transition, constants.METATYPE_TRANSITION, "Transition"),
]


class MetaTypeConstantsTest(unittest.TestCase):
    def test_a_class_has_the_meta_type_of_its_constant(self):
        for cls, constant, _ in META_TYPES:
            self.assertEqual(cls.meta_type, constant, cls.__name__)

    def test_the_meta_types_are_the_ones_that_are_in_the_catalog(self):
        for cls, constant, stored in META_TYPES:
            self.assertEqual(constant, stored, cls.__name__)

    def test_the_meta_types_are_different(self):
        names = [constant for _, constant, _ in META_TYPES]
        self.assertEqual(len(names), len(set(names)))
