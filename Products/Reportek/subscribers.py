# -*- coding: utf-8 -*-
import logging
from time import time

from DateTime import DateTime
from OFS.interfaces import IObjectWillBeMovedEvent
from zope.lifecycleevent.interfaces import IObjectAddedEvent, IObjectMovedEvent

from Products.Reportek.constants import ENGINE_ID

logger = logging.getLogger(__name__)


def handle_document_removed_event(obj, event):
    """Delete associated feedback objects when file is deleted"""
    fbs_id = [fb.getId() for fb in obj.getFeedbacksForDocument()]
    if fbs_id:
        parent = getattr(obj, "aq_parent", None)
        if parent:
            parent.manage_delObjects(fbs_id)


def handle_feedback_added_event(obj, event):
    """Force the update of envelopes bobobase_modification_time"""
    env = obj.getParentNode()
    env.last_fb = DateTime()
    env._p_changed = 1
    env.reindexObject()


def handle_document_renamed_event(obj, event):
    """Force the update of data_file's mtime value"""
    if getattr(event, "newName", None) and getattr(event, "oldName", None):
        obj.data_file.mtime = time()
        obj._p_changed = 1
        obj.reindexObject()


# Handler for collection added
def handle_collection_added_event(obj, event):
    """Trigger notify metadata when a collection is added"""
    engine = obj.unrestrictedTraverse(ENGINE_ID, None)
    if engine and getattr(engine, "col_sync_rmq", False):
        engine.add_new_col_sync(
            "/".join(obj.getPhysicalPath()),
            obj.bobobase_modification_time().HTML4(),
        )
        if getattr(engine, "col_sync_rmq_pub", False):
            obj.notify_sync()


# Handler for collection deleted
def handle_collection_removed_event(obj, event):
    """Cleanup sync data when collection is deleted"""
    engine = obj.unrestrictedTraverse(ENGINE_ID, None)
    if engine and getattr(engine, "col_sync_rmq", False):
        if engine.cols_sync_history:
            del engine.cols_sync_history["/".join(obj.getPhysicalPath())]
            engine._p_changed = True


def handleContentishEvent(ob, event):
    """Event subscriber for (IObjectEvent) events."""
    if IObjectAddedEvent.providedBy(event):
        ob.indexObject()

    elif IObjectMovedEvent.providedBy(event):
        if event.newParent is not None:
            ob.indexObject()

    elif IObjectWillBeMovedEvent.providedBy(event):
        if event.oldParent is not None:
            ob.unindexObject()


def handle_audit_assigned_event(obj, event):
    """Handle envelope audit assignment"""
    logger.info("Audit assigned for: {}".format(obj.absolute_url()))


def handle_audit_unassigned_event(obj, event):
    """Handle envelope audit unassignment"""
    try:
        obl_process = obj.unrestrictedTraverse(obj.process_path)
        if obl_process and obj.status != "complete":
            end_act = obl_process.end
            wk = obj.getListOfWorkitems()[-1]
            obj.falloutWorkitem(wk.id)
            obj.fallinWorkitem(wk.id, end_act)
            obj.endFallinWorkitem(wk.id)
            logger.info("Audit unassigned for: {}".format(obj.absolute_url()))
    except Exception as e:
        logger.error("Error completing audit envelope: {}".format(e))
