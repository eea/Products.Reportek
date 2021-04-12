""" Update the Reportek file repository to use ZODB Blob

  >>> import update_reposit_blob
  >>> update_reposit_blob.setup_log_handler()
  >>> update_reposit_blob.convert_all(app)
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
import tempfile
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


def get_reposit_root():
    return os.path.join(CLIENT_HOME, 'reposit')


def physicalpath(doc):
    filename = doc.filename
    if not isinstance(filename, list):
        raise ValueError("what filename is this? %r" % (filename,))
    return os.path.join(get_reposit_root(), *filename)


_attrib_to_remove = ['filename', 'file_uploaded',
                     '_upload_time', '__version__']


def cleanup(doc):
    for name in _attrib_to_remove:
        if hasattr(doc.aq_base, name):
            delattr(doc.aq_base, name)


def is_updated(doc):
    if not hasattr(doc, 'data_file'):
        return False
    elif any(hasattr(doc.aq_base, name) for name in _attrib_to_remove):
        return False
    else:
        return True


def convert(doc, allow_missing):
    log.debug("Converting document %r ...", doc)
    if hasattr(doc.aq_base, 'data_file'):
        raise ValueError("Document %r already has a `data_file`." % doc)
    doc.data_file = FileContainer()
    fs_path = physicalpath(doc)
    if os.path.exists(fs_path):
        old_f = open(fs_path, 'rb')
    else:
        alternate_fs_path = fs_path + '.undo'
        if os.path.exists(alternate_fs_path):
            fs_path = alternate_fs_path
            log.debug("filesystem path is %r", fs_path)
            old_f = open(fs_path, 'rb')
        elif allow_missing:
            fs_path = '<missing>'
            old_f = tempfile.TemporaryFile()
        else:
            raise ValueError("No data file found on filesystem: %r (+'.undo')",
                             fs_path)
    if old_f is not None:
        size = 0
        with old_f:
            with doc.data_file.open('wb') as new_f:
                for block in RepUtils.iter_file_data(old_f):
                    new_f.write(block)
                    size += len(block)
    log.debug("%d bytes copied", size)
    cleanup(doc)
    log.info("Converted %r", doc)
    return fs_path, size


def ofs_path(ob):
    return '/'.join(ob.getPhysicalPath())


def convert_all(parent, limit=None, skip=0,
                allow_missing=False, warnings=True, report=True):
    out = defaultdict(list)
    total_bytes = 0
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
            fs_path, size = convert(doc, allow_missing=allow_missing)
        except Exception, e:
            sp.rollback()
            if warnings:
                log.warn("Error converting %r (%s)", doc, e)
            out['broken_documents'].append(ofs_path(doc))
        else:
            out['copied_paths'].append(fs_path)
            total_bytes += size
    msg = ("{path} Migrate documents to blob "
           "({objects} items, {bytes} bytes)").format(
        path=ofs_path(parent),
        objects=len(out['copied_paths']),
        bytes=total_bytes)
    transaction.get().note(msg)
    if report:
        return dict(out, total_bytes=total_bytes)
