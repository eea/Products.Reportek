""" Change feedback attachments from "File" to "File (Blob)".

  >>> import update_feedback_blob
  >>> update_feedback_blob.setup_log_handler()
  >>> update_feedback_blob.convert_all(app)
  >>> import transaction
  >>> transaction.commit()

"""

import logging
import tempfile
import transaction
from Products.Reportek import RepUtils
from Products.Reportek import blob

log = logging.getLogger(__name__)

handler = None

def setup_log_handler(level=logging.INFO):
    global handler
    if handler is not None:
        log.removeHandler(handler)
    handler = logging.StreamHandler()
    log.addHandler(handler)
    log.setLevel(level)


def ofs_path(ob):
    return '/'.join(ob.getPhysicalPath())


def iter_feedbacks(parent):
    blacklist = ['/Control_Panel']
    for ob in parent.objectValues():
        if ofs_path(ob) in blacklist:
            continue
        if ob.meta_type == 'Report Feedback':
            yield ob
        elif hasattr(ob.aq_base, 'objectValues'):
            for sub_ob in iter_feedbacks(ob):
                yield sub_ob


def iter_feedback_files(parent):
    for feedback in iter_feedbacks(parent):
        for file_ob in feedback.objectValues(['File']):
            yield feedback, file_ob


def convert(feedback, file_ob):
    log.debug("Converting document %r ...", file_ob)
    ob_id = file_ob.getId()
    with RepUtils.ofs_file_content_tmp(file_ob) as tmp:
        feedback.manage_delObjects([ob_id])
        blob_file_ob = blob.add_OfsBlobFile(feedback, ob_id, tmp)
    log.info("Converted %r, %d bytes",
             ofs_path(blob_file_ob), blob_file_ob.data_file.size)
    return blob_file_ob


def convert_all(parent, limit=None, skip=0, report=True):
    out = {'objects': 0, 'bytes': 0}
    for i, (feedback, file_ob) in enumerate(iter_feedback_files(parent)):
        if i < skip:
            continue
        if limit is not None and i >= skip + limit:
            break
        sp = transaction.savepoint()
        try:
            blob_file_ob = convert(feedback, file_ob)
        except Exception, e:
            sp.rollback()
            if warnings:
                log.warn("Error converting %r (%s)", file_ob, e)
        else:
            out['objects'] += 1
            out['bytes'] += blob_file_ob.data_file.size
    if report:
        return out
