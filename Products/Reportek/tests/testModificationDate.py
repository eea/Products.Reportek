# -*- coding: utf-8 -*-
import unittest

from Acquisition import aq_base
from DateTime import DateTime
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem

from Products.Reportek.Collection import Collection
from Products.Reportek.Document import Document
from Products.Reportek.Feedback import ReportFeedback
from Products.Reportek.modification_date import (
    MODIFICATION_DATE_ATTR,
    MODIFICATION_INDEX,
    get_reportek_modification_date,
    mark_modified,
    set_reportek_modification_date,
)
from Products.Reportek.subscribers import handle_reportek_modified_event
from Products.Reportek.workitem import workitem


class ReindexMixin(object):
    reindexed = None

    def reindexObject(self, idxs=[], update_metadata=1, uid=None):
        if self.reindexed is None:
            self.reindexed = []
        self.reindexed.append((idxs, update_metadata))


class DummyFolder(ReindexMixin, Folder):
    def __init__(self, id, meta_type):
        self.id = id
        self.meta_type = meta_type
        self.reindexed = []
        Folder.__init__(self)


class DummyItem(ReindexMixin, SimpleItem):
    def __init__(self, id, meta_type):
        self.id = id
        self.meta_type = meta_type
        self.reindexed = []


class LegacyObject(object):
    pass


class ModificationDateTests(unittest.TestCase):
    def test_new_content_constructors_set_reportek_modification_date(self):
        objects = [
            Collection("collection"),
            Document("document"),
            ReportFeedback("feedback", DateTime("2020/01/01")),
            workitem("workitem", "instance", "activity", False),
        ]

        for obj in objects:
            self.assertTrue(hasattr(obj, MODIFICATION_DATE_ATTR))
            self.assertIsNotNone(get_reportek_modification_date(obj))

    def test_get_uses_persisted_reportek_date(self):
        obj = DummyItem("doc", "Report Document")
        expected = DateTime("2020/01/02 03:04:05")

        set_reportek_modification_date(obj, expected)

        self.assertEqual(get_reportek_modification_date(obj), expected)

    def test_get_fallback_to_p_mtime_is_side_effect_free(self):
        obj = LegacyObject()
        obj._p_mtime = DateTime("2019/05/06 07:08:09").timeTime()

        result = get_reportek_modification_date(obj)

        self.assertEqual(result, DateTime(obj._p_mtime))
        self.assertFalse(hasattr(obj, MODIFICATION_DATE_ATTR))

    def test_mark_modified_updates_child_envelope_and_collection(self):
        collection = DummyFolder("collection", "Report Collection")
        envelope = DummyFolder("envelope", "Report Envelope")
        document = DummyItem("document", "Report Document")
        collection._setObject("envelope", envelope)
        envelope = collection.envelope
        envelope._setObject("document", document)
        document = envelope.document
        expected = DateTime("2021/02/03 04:05:06")

        marked = mark_modified(document, date=expected, cascade=True, reindex=True)

        self.assertEqual(len(marked), 3)
        self.assertEqual(document.reportek_modification_date, expected)
        self.assertEqual(envelope.reportek_modification_date, expected)
        self.assertEqual(collection.reportek_modification_date, expected)
        self.assertEqual(document.reindexed, [([MODIFICATION_INDEX], 1)])
        self.assertEqual(envelope.reindexed, [([MODIFICATION_INDEX], 1)])
        self.assertEqual(collection.reindexed, [([MODIFICATION_INDEX], 1)])

    def test_mark_modified_updates_ancestor_collection_for_child_collection(self):
        parent = DummyFolder("parent", "Report Collection")
        child = DummyFolder("child", "Report Collection")
        parent._setObject("child", child)
        child = parent.child
        expected = DateTime("2022/03/04 05:06:07")

        mark_modified(child, date=expected, cascade=True, reindex=False)

        self.assertEqual(child.reportek_modification_date, expected)
        self.assertEqual(parent.reportek_modification_date, expected)
        self.assertEqual(child.reindexed, [])
        self.assertEqual(parent.reindexed, [])

    def test_mark_modified_does_not_update_descendants(self):
        collection = DummyFolder("collection", "Report Collection")
        envelope = DummyFolder("envelope", "Report Envelope")
        collection._setObject("envelope", envelope)
        envelope = collection.envelope
        expected = DateTime("2023/04/05 06:07:08")

        mark_modified(collection, date=expected, cascade=True, reindex=False)

        self.assertEqual(collection.reportek_modification_date, expected)
        self.assertFalse(hasattr(aq_base(envelope), MODIFICATION_DATE_ATTR))

    def test_modified_event_handler_marks_and_cascades(self):
        collection = DummyFolder("collection", "Report Collection")
        feedback = DummyItem("feedback", "Report Feedback")
        collection._setObject("feedback", feedback)
        feedback = collection.feedback

        handle_reportek_modified_event(feedback, object())

        self.assertTrue(hasattr(feedback, MODIFICATION_DATE_ATTR))
        self.assertEqual(
            feedback.reportek_modification_date,
            collection.reportek_modification_date,
        )
        self.assertEqual(feedback.reindexed, [([MODIFICATION_INDEX], 1)])
        self.assertEqual(collection.reindexed, [([MODIFICATION_INDEX], 1)])


if __name__ == "__main__":
    unittest.main()
