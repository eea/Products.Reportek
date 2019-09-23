# -*- coding: utf-8 -*-
# Generate hash for files
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20190923_add_file_hash; u20190923_add_file_hash.update(app)

import logging

import transaction
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.updates import MigrationBase

logger = logging.getLogger(__name__)
VERSION = 19
APPLIES_TO = [
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR,
    DEPLOYMENT_BDR
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


def hash_it(app):
    engine = app.unrestrictedTraverse('/' + ENGINE_ID)
    catalog = app.unrestrictedTraverse('Catalog')
    query = {
        'meta_type': 'Report Document',
    }

    brains = catalog(**query)
    docs = [doc.getObject() for doc in brains]

    results = []
    for doc in docs:
        if not doc.hash:
            try:
                doc.generate_hash()
                log_msg("{} generated hash: {}".format(doc.absolute_url(), doc.hash))
                transaction.commit()
                results.append(doc.absolute_url())
            except Exception as e:
                log_msg('Unable to set hash for: {} due to: {}'.format(doc.absolute_url(), str(e)))

    log_msg("Successfully generated hashes for: {} files.\n{}".format(len(results), results))
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not hash_it(app):
        return

    log_msg('Files hashed')
    return True
