# -*- coding: utf-8 -*-
# Generate hash for files
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20201210_unrestrict_xmls; u20201210_unrestrict_xmls.update(app)

import logging

import transaction
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.updates import MigrationBase

logger = logging.getLogger(__name__)
VERSION = 20
APPLIES_TO = [
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


def unrestrict_docs(app):
    catalog = app.unrestrictedTraverse('Catalog')
    query = {
        'meta_type': 'Report Document',
    }

    brains = catalog(**query)
    docs = [doc.getObject() for doc in brains]

    results = []
    for doc in docs:
        try:
            if doc.isRestricted():
                doc.manage_unrestrict(ids=[doc.getId()])
                log_msg("{} is now unrestricted".format(doc.absolute_url()))
                transaction.commit()
                results.append(doc.absolute_url())
        except Exception as e:
            log_msg('Unable to unrestrict: {} due to: {}'.format(
                doc.absolute_url(), str(e)))

    log_msg("Successfully unrestricted: {} files.\n{}".format(
        len(results), results))
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not unrestrict_docs(app):
        return

    log_msg('Files unrestricted')
    return True
