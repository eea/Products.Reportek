# -*- coding: utf-8 -*-
# Migrate Converter attributes
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import\
#    u20161107_migrate_converter_attributes
# u20161107_migrate_converter_attributes.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import CONVERTERS_ID
import logging
import transaction

logger = logging.getLogger(__name__)
VERSION = 9
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def migrate_converter_attributes(app):
    count = 0
    converters = app.unrestrictedTraverse('/' + CONVERTERS_ID)

    for ob in converters.objectValues('Converter'):
        if ob and hasattr(ob, 'setstate'):
            del ob.setstate
            ob._p_changed = 1
            if count % 10000 == 0:
                transaction.savepoint()
                logger.info('savepoint at %d records', count)

            count += 1
    logger.info('Changed a total of {} objects'.format(count))
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not migrate_converter_attributes(app):
        return

    logger.info('Converter attributes have been migrated')
    return True
