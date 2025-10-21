# flake8: noqa
# -*- coding: utf-8 -*-
# Add new ODS Obligation to existing ODS Collections
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20250108_add_new_ods_obligation; u20250108_add_new_ods_obligation.update(app)

import logging

import transaction
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import ENGINE_ID, DEFAULT_CATALOG
from Products.Reportek.updates import MigrationBase
from Products.Reportek.RepUtils import getToolByName


logger = logging.getLogger(__name__)
VERSION = 22
APPLIES_TO = [
    DEPLOYMENT_BDR
]

OLD_ODS_OBL_ID = 'http://rod.eionet.europa.eu/obligations/213'
NEW_ODS_OBL_ID = 'http://rod.eionet.europa.eu/obligations/869'

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

def get_ods_collections(app):
    catalog = getToolByName(app, DEFAULT_CATALOG, None)
    query = {
        "path": "/ods",
        "dataflow_uris": OLD_ODS_OBL_ID,
        "meta_type": "Report Collection"
    }

    return catalog(**query)

def add_new_ods_obligation(app):
    brains = get_ods_collections(app)
    count = 0
    errors = 0

    try:
        for brain in brains:
            try:
                obj = brain.getObject()
                if obj and NEW_ODS_OBL_ID not in obj.dataflow_uris:
                    obj.dataflow_uris.append(NEW_ODS_OBL_ID)
                    obj._p_changed = 1
                    logger.info(
                        'Added ODS Obligation to %s. Obligations: %s',
                            obj.absolute_url(), obj.dataflow_uris)
                    obj.reindexObject()
                    if count % 10000 == 0:
                        transaction.savepoint()
                        logger.info('savepoint at %d records', count)
                    count += 1
                else:
                    logger.info(
                        'ODS Obligation already added to %s. '
                        'Obligations: %s',
                        obj.absolute_url(), obj.dataflow_uris)
            except Exception as e:
                errors += 1
                logger.error(
                    'Error processing %s: %s', brain.getURL(), str(e))
                continue

        transaction.commit()
        logger.info('Changed %d objects with %d errors', count, errors)
        return True
    except Exception as e:
        logger.critical('Critical error during migration: %s', str(e))
        transaction.abort()
        return False


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not add_new_ods_obligation(app):
        return

    log_msg('ODS Obligation added to existing ODS Collections.')
    return True
