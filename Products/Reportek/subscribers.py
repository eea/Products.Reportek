# -*- coding: utf-8 -*-
from DateTime import DateTime
from time import time
from Products.Reportek.constants import ENGINE_ID


def handle_document_removed_event(obj, event):
    """Delete associated feedback objects when file is deleted"""
    fbs_id = [fb.getId() for fb in obj.getFeedbacksForDocument()]
    if fbs_id:
        parent = getattr(obj, 'aq_parent', None)
        if parent:
            parent.manage_delObjects(fbs_id)


def handle_feedback_added_event(obj, event):
    """Force the update of envelopes bobobase_modification_time"""
    env = obj.getParentNode()
    env.last_fb = DateTime()
    env._p_changed = 1
    env.reindex_object()


def handle_document_renamed_event(obj, event):
    """Force the update of data_file's mtime value"""
    if getattr(event, 'newName', None):
        obj.data_file.mtime = time()
        obj._p_changed = 1
        obj.reindex_object()


# Handler for collection added
def handle_collection_added_event(obj, event):
    """Trigger notify metadata when a collection is added"""
    engine = obj.unrestrictedTraverse(ENGINE_ID, None)
    if engine and getattr(engine, 'col_sync_rmq', False):
        engine.add_new_col_sync(
            '/'.join(obj.getPhysicalPath()),
            obj.bobobase_modification_time().HTML4())
        if getattr(engine, 'col_sync_rmq_pub', False):
            obj.notify_sync()


# Handler for collection deleted
def handle_collection_removed_event(obj, event):
    """Cleanup sync data when collection is deleted"""
    engine = obj.unrestrictedTraverse(ENGINE_ID, None)
    if engine and getattr(engine, 'col_sync_rmq', False):
        if engine.cols_sync_history:
            del engine.cols_sync_history['/'.join(obj.getPhysicalPath())]
            engine._p_changed = True


# def handle_envelope_released_event(obj, event):
#     """test"""
