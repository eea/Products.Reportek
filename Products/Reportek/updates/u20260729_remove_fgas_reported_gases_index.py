# -*- coding: utf-8 -*-
"""Remove unsafe FGAS reported gases FieldIndex in Python 3.

``get_fgas_reported_gases`` returns a list of dictionaries. That shape is used
as metadata by templates/export code, but it is not safe as a ZCatalog
``FieldIndex`` key on Python 3 because dictionaries are not orderable.

Run from Zope debug/zconsole after deploying this code::

    from Products.Reportek.updates import u20260729_remove_fgas_reported_gases_index
    u20260729_remove_fgas_reported_gases_index.update(app)
"""

import logging

import transaction

from Products.Reportek import constants
from Products.Reportek.config import DEPLOYMENT_BDR, REPORTEK_DEPLOYMENT
from Products.Reportek.RepUtils import getToolByName
from Products.Reportek.updates import MigrationBase

logger = logging.getLogger(__name__)

VERSION = 24
APPLIES_TO = [DEPLOYMENT_BDR]
INDEX_NAME = "get_fgas_reported_gases"


def log_msg(msg, level="INFO"):
    lvl = {
        "CRITICAL": 50,
        "ERROR": 40,
        "WARNING": 30,
        "INFO": 20,
        "DEBUG": 10,
        "NOTSET": 0,
    }
    logger.log(lvl.get(level), msg)
    print(msg)


def remove_fgas_reported_gases_index(app):
    if REPORTEK_DEPLOYMENT not in APPLIES_TO:
        log_msg(
            "Skipping FGAS reported gases index cleanup for deployment: %s"
            % REPORTEK_DEPLOYMENT
        )
        return False

    catalog = getToolByName(app, constants.DEFAULT_CATALOG, None)
    if catalog is None:
        log_msg(
            "Skipping FGAS reported gases index cleanup: catalog not found", "WARNING"
        )
        return False

    changed = False
    if INDEX_NAME in catalog.indexes():
        catalog.delIndex(INDEX_NAME)
        changed = True
        log_msg("Deleted unsafe FieldIndex: %s" % INDEX_NAME)
    else:
        log_msg("FieldIndex already absent: %s" % INDEX_NAME)

    if INDEX_NAME not in catalog.schema():
        catalog.addColumn(INDEX_NAME)
        changed = True
        log_msg("Added metadata column: %s" % INDEX_NAME)
    else:
        log_msg("Metadata column already present: %s" % INDEX_NAME)

    if changed:
        transaction.commit()
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    return remove_fgas_reported_gases_index(app)
