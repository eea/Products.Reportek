# flake8: noqa
# -*- coding: utf-8 -*-
# Add new FGAS Verification Collection
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20250303_add_new_fgas_ver_col; u20250303_add_new_fgas_ver_col.update(app)

import logging

import transaction
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import ENGINE_ID, DEFAULT_CATALOG
from Products.Reportek.updates import MigrationBase
from Products.Reportek.RepUtils import getToolByName


logger = logging.getLogger(__name__)
VERSION = 23
APPLIES_TO = [
    DEPLOYMENT_BDR
]

FGAS_OBL_ID = 'http://rod.eionet.europa.eu/obligations/868'
FGAS_VER_OBL_ID = 'http://rod.eionet.europa.eu/obligations/870'
FGAS_VER_COL_ID = 'col_fgas_ver'
FGAS_VER_TITLE = 'Verification (bulk and/or equipment/products) under Regulation (EU) 2024/573'

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

def get_fgas_collections(app):
    catalog = getToolByName(app, DEFAULT_CATALOG, None)
    query = {
        "path": "/fgases",
        "dataflow_uris": FGAS_OBL_ID,
        "meta_type": "Report Collection"
    }

    return catalog(**query)

def add_new_fgas_ver_col(app):
    brains = get_fgas_collections(app)
    count = 0
    errors = 0
    engine = app.ReportekEngine
    try:
        for brain in brains:
            try:
                if len(brain.getPath().split('/')) != 4:
                    print "Skipping non-4-level path:{}".format(brain.getPath())
                    continue
                obj = brain.getObject()
                if obj.company_id:
                    engine.create_fgas_ver_col(obj, FGAS_VER_TITLE)
                    print "Created FGAS verification collection for: {}".format(obj.absolute_url())
                    logger.info(
                        'Added FGAS verification collection to: %s',
                            obj.absolute_url())
                    if count % 10000 == 0:
                        transaction.savepoint()
                        logger.info('savepoint at %d records', count)
                    count += 1
                else:
                    print "Skipping non-company collection: {}".format(obj.absolute_url())
                    logger.info(
                        'Not a company collection: %s. ',
                        obj.absolute_url())
            except Exception as e:
                errors += 1
                print "Skipping error processing: {}".format(brain.getURL())
                logger.error(
                    'Error processing %s: %s', brain.getURL(), str(e))
                continue

        transaction.commit()
        print "Changed {} objects with {} errors".format(count, errors)
        logger.info('Changed %d objects with %d errors', count, errors)
        return True
    except Exception as e:
        print "Critical error during migration: {}".format(str(e))
        logger.critical('Critical error during migration: %s', str(e))
        transaction.abort()
        return False


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not add_new_fgas_ver_col(app):
        return

    log_msg('FGAS verification collection added to existing FGAS Collections.')
    return True
