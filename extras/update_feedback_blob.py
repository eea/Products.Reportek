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


FEEDBACKTEXT_LIMIT = 1024*32 # 32KB


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


def iter_feedback_files(feedback):
    for file_ob in feedback.objectValues(['File']):
        yield file_ob


def _aa_iter_feedback_files(parent):
    for feedback in iter_feedbacks(parent):
        for file_ob in feedback.objectValues(['File']):
            yield feedback, file_ob


def convert_attachment(feedback, file_ob):
    log.debug("Converting document %r ...", file_ob)
    ob_id = file_ob.getId()
    with RepUtils.ofs_file_content_tmp(file_ob) as tmp:
        feedback.manage_delObjects([ob_id])
        blob_file_ob = blob.add_OfsBlobFile(feedback, ob_id, tmp)
    log.info("Converted %r, %d bytes",
             ofs_path(blob_file_ob), blob_file_ob.data_file.size)
    return blob_file_ob


def write_string_to_file(string, f):
    if isinstance(string, str):
        f.write(string)
    elif isinstance(string, unicode):
        blocksize = 65536
        for c in range(len(string)/blocksize+1):
            f.write(string[c*blocksize:(c+1)*blocksize].encode('utf-8'))
    else:
        raise ValueError("Unknown type %r" % type(string))


def convert_feedbacktext(feedback):
    log.debug("Converting feedbacktext %r ...", feedback)
    blob_file_ob = blob.add_OfsBlobFile(feedback, feedback.getId() + '.html')
    with blob_file_ob.data_file.open('wb') as f:
        write_string_to_file(feedback.feedbacktext, f)
    blob_file_ob.data_file.content_type = 'text/html'
    feedback.feedbacktext = "<em>see attachment</em>"
    log.info("Converted feedbacktext for %r, %d bytes",
             ofs_path(feedback), blob_file_ob.data_file.size)
    return blob_file_ob


def convert_all(parent, limit=None, skip=0, report=True, warnings=True):
    out = {'objects': 0, 'bytes': 0}
    for i, feedback in enumerate(iter_feedbacks(parent)):
        if i < skip:
            continue
        if limit is not None and i >= skip + limit:
            break
        sp = transaction.savepoint()
        n_objects = n_bytes = 0
        try:
            for file_ob in feedback.objectValues(['File']):
                blob_file_ob = convert_attachment(feedback, file_ob)
                n_bytes += blob_file_ob.data_file.size
                n_objects += 1
            if len(feedback.feedbacktext) > FEEDBACKTEXT_LIMIT:
                blob_file_ob = convert_feedbacktext(feedback)
                n_bytes += blob_file_ob.data_file.size
                n_objects += 1
        except Exception, e:
            sp.rollback()
            if warnings:
                log.warn("Error converting %r (%s)", feedback, e)
        else:
            out['objects'] += n_objects
            out['bytes'] += n_bytes
    if report:
        return out
