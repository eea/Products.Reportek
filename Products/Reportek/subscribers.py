# -*- coding: utf-8 -*-
import os
from RepUtils import get_zip_cache


def handle_document_removed_event(obj, event):
    """Delete associated feedback objects when file is deleted"""
    fbs_id = [fb.getId() for fb in obj.getFeedbacksForDocument()]
    if fbs_id:
        parent = getattr(obj, 'aq_parent', None)
        if parent:
            parent.manage_delObjects(fbs_id)


def handle_zipstream_completed_event(event):
    """Delete the files used to generate the zipstream."""
    env_id = event.envelope_id
    zip_cache = get_zip_cache()
    for f in os.listdir(zip_cache):
        if f.startswith(env_id):
            os.remove(os.path.join(zip_cache, f))
