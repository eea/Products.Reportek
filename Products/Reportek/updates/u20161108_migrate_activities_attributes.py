# -*- coding: utf-8 -*-
# Migrate activities attributes
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20161108_migrate_activities_attributes; u20161107_migrate_activities_attributes.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import DEFAULT_CATALOG
import logging
import transaction

logger = logging.getLogger(__name__)
VERSION = 13
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def migrate_activities_attributes(app):
    catalog = app.unrestrictedTraverse('/' + DEFAULT_CATALOG)
    brains = catalog({'meta_type': 'Activity'})

    count = 0
    for brain in brains:
        try:
            obj = brain.getObject()
        except Exception as e:
            logger.error('Unable to retrieve object: {} due to {}'.format(brain.getURL(), str(e)))
        if obj and hasattr(obj, 'setstate'):
            del obj.setstate
            obj._p_changed = 1
            if count % 10000 == 0:
                transaction.savepoint()
                logger.info('savepoint at %d records', count)

            count += 1
    logger.info('Changed a total of {} objects'.format(count))
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not migrate_activities_attributes(app):
        return

    logger.info('Activities attributes have been migrated')
    return True
