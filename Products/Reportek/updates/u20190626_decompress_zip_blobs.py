# flake8: noqa
# -*- coding: utf-8 -*-
# Decompress gzipped zip blob files
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20190626_decompress_zip_blobs; u20190626_decompress_zip_blobs.update(app)

import logging

import transaction
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.updates import MigrationBase

logger = logging.getLogger(__name__)
VERSION = 18
APPLIES_TO = [
    DEPLOYMENT_CDR,
]


def log_msg(msg, level='INFO'):
    lvl = {
        'CRITICAL': 50,
        'ERROR': 40,
        'WARNING': 30,
        'INFO': 20,
        'DEBUG': 10,
        'NOTSET': 0
    }
    logger.log(lvl.get(level), msg)
    print msg


def decompress_zip_blobs(app):
    engine = app.unrestrictedTraverse('/' + ENGINE_ID)
    catalog = app.unrestrictedTraverse('Catalog')
    query = {
        'meta_type': 'Report Document',
    }

    brains = catalog(**query)
    docs = [doc.getObject() for doc in brains
            if doc.id.endswith('.zip') and doc.getObject().is_compressed()]

    results = []
    for doc in docs:
        data_file = doc.data_file
        setattr(data_file, '_toCompress', 'no')
        setattr(data_file, 'compressed_size', None)
        path = data_file.get_fs_path()
        try:
            file_handle = data_file.open('rb')
            content = file_handle.read()
            file_handle.close()
            with data_file.open('wb', orig_size=data_file.size, preserve_mtime=True) as file_handle:
                file_handle.write(content)
            log_msg('Decompressing blob: {}. Size: {}. Compressed: {}. Path: {}'.format(
                path, data_file.size, data_file.compressed_size, doc.absolute_url()))
            results.append(doc)
            transaction.commit()
        except Exception as e:
            log_msg('Unable to decompress: {} due to: {}'.format(path, str(e)))

    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not decompress_zip_blobs(app):
        return

    log_msg('Zip blobs decompression completed!')
    return True
