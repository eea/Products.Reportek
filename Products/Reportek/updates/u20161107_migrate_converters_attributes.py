# -*- coding: utf-8 -*-
# Migrate Converters attributes
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20161107_migrate_converters_attributes; u20161107_migrate_converters_attributes.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import CONVERTERS_ID
import logging

logger = logging.getLogger(__name__)
VERSION = 10
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def migrate_converters_attributes(app):
    converters = app.unrestrictedTraverse('/' + CONVERTERS_ID)
    if hasattr(converters, 'setstate'):
        del converters.setstate
        converters._p_changed = 1
        logger.info('Changed attributes for Converters')
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not migrate_converters_attributes(app):
        return

    logger.info('Converters attributes have been migrated')
    return True
