# -*- coding: utf-8 -*-
# Migrate QARepository attributes
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import\
#    u20161108_migrate_QARepository_attributes
#  >>> u20161107_migrate_QARepository_attributes.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import QAREPOSITORY_ID
import logging

logger = logging.getLogger(__name__)
VERSION = 11
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def migrate_QARepository_attributes(app):
    qa_repo = app.unrestrictedTraverse('/' + QAREPOSITORY_ID)
    if hasattr(qa_repo, 'setstate'):
        del qa_repo.setstate
        qa_repo._p_changed = 1
        logger.info('Changed attributes for QARepository')
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not migrate_QARepository_attributes(app):
        return

    logger.info('QARepository attributes have been migrated')
    return True
