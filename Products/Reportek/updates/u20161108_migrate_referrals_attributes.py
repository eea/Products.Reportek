# -*- coding: utf-8 -*-
# Migrate referrals attributes
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20161108_migrate_referrals_attributes; u20161107_migrate_referrals_attributes.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import DF_URL_PREFIX
from Products.Reportek.constants import DEFAULT_CATALOG
import logging
import transaction

logger = logging.getLogger(__name__)
VERSION = 12
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def migrate_referrals_attributes(app):
    catalog = app.unrestrictedTraverse('/' + DEFAULT_CATALOG)
    brains = catalog({'meta_type': 'Repository Referral'})

    count = 0
    for brain in brains:
        try:
            obj = brain.getObject()
        except Exception as e:
            logger.error('Unable to retrieve object: {} due to {}'.format(brain.getURL(), str(e)))
        if obj:
            do_update = False
            year = getattr(obj, 'year', '')
            if year and isinstance(year, str):
                try:
                    obj.year = int(year)
                    do_update = True
                except ValueError:
                    logger.warning('Unable to convert year value: {} from string to integer')

            if not hasattr(obj, 'endyear'):
                obj.endyear = ''
                do_update = True

            if isinstance(obj.endyear, str) and obj.endyear != '':
                try:
                    obj.endyear = int(obj.endyear)
                    do_update = True
                except ValueError:
                    logger.warning('Unable to convert endyear value: {} from string to integer')
                    obj.endyear = ''

            # The new URI-based obligation codes. Can now be multiple
            if not hasattr(obj, 'dataflow_uris'):
                if obj.dataflow:
                    obj.dataflow_uris = (DF_URL_PREFIX + obj.dataflow,)
                else:
                    obj.dataflow_uris = ()
            if do_update:
                obj.reindex_object()

            if count % 10000 == 0:
                transaction.savepoint()
                logger.info('savepoint at %d records', count)

            count += 1

    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not migrate_referrals_attributes(app):
        return

    logger.info('referrals attributes have been migrated')
    return True
