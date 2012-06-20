""" Update the Reportek file repository to use ZODB Blob

  >>> import update_reposit_blob
  >>> update_reposit_blob.setup_log_handler()
  >>> result = update_reposit_blob.convert_all(app)
  >>> import transaction
  >>> transaction.commit()

The `result` dictionary contains a report of the conversion.
`result['copied_paths']` is a list of filesystem paths that can now be removed.
`result['broken_documents']` is a list of OFS paths of documents for which
conversion failed. `result['already_converted']` is a list of OFS paths of
documents which have previously been converted.

"""

import os.path
import logging
from collections import defaultdict
import transaction
from Products.Reportek.Document import Document, FileContainer
from Products.Reportek import RepUtils

log = logging.getLogger(__name__)

handler = None

def setup_log_handler(level=logging.INFO):
    global handler
    if handler is not None:
        log.removeHandler(handler)
    handler = logging.StreamHandler()
    log.addHandler(handler)
    log.setLevel(level)


def iter_documents(parent):
    for ob in parent.objectValues():
        if isinstance(ob, Document):
            yield ob
        elif hasattr(ob.aq_base, 'objectValues'):
            for sub_ob in iter_documents(ob):
                yield sub_ob


def physicalpath(doc):
    filename = doc.filename
    if not isinstance(filename, list):
        raise ValueError("what filename is this? %r" % (filename,))
    return os.path.join(CLIENT_HOME, 'reposit', *filename)


_attrib_to_remove = ['filename', 'file_uploaded', '_upload_time', '__version__']
def cleanup(doc):
    for name in _attrib_to_remove:
        delattr(doc.aq_base, name)


def is_updated(doc):
    if not hasattr(doc, 'data_file'):
        return False
    elif any(hasattr(doc.aq_base, name) for name in _attrib_to_remove):
        return False
    else:
        return True


def convert(doc):
    log.debug("Converting document %r ...", doc)
    if hasattr(doc.aq_base, 'data_file'):
        raise ValueError("Document %r already has a `data_file`." % doc)
    doc.data_file = FileContainer()
    fs_path = physicalpath(doc)
    if not os.path.exists(fs_path):
        alternate_fs_path = fs_path + '.undo'
        if os.path.exists(alternate_fs_path):
            fs_path = alternate_fs_path
        else:
            raise ValueError("No data file found on filesystem: %r (+'.undo')",
                             fs_path)
    log.debug("filesystem path is %r", fs_path)
    with open(fs_path, 'rb') as old_f:
        with doc.data_file.open('wb') as new_f:
            size = 0
            for block in RepUtils.iter_file_data(old_f):
                new_f.write(block)
                size += len(block)
    log.debug("%d bytes copied", size)
    cleanup(doc)
    log.info("Converted %r", doc)
    return fs_path


def ofs_path(ob):
    return '/'.join(ob.getPhysicalPath())


def convert_all(parent, limit=None, skip=0, warnings=True, report=True):
    out = defaultdict(list)
    for i, doc in enumerate(iter_documents(parent)):
        if i < skip:
            continue
        if limit is not None and i >= skip + limit:
            break
        if is_updated(doc):
            out['already_converted'].append(ofs_path(doc))
            continue
        sp = transaction.savepoint()
        try:
            fs_path = convert(doc)
        except Exception, e:
            sp.rollback()
            if warnings:
                log.warn("Error converting %r (%s)", doc, e)
            out['broken_documents'].append(ofs_path(doc))
        else:
            out['copied_paths'].append(fs_path)
    if report:
        return dict(out)
