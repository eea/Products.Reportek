# -*- coding: utf-8 -*-
from DateTime import DateTime
from time import time


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
    obj.data_file.mtime = time()
    obj._p_changed = 1
    obj.reindex_object()
