# -*- coding: utf-8 -*-
# Migrate Collections attributes
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20161107_migrate_collection_attributes; u20161107_migrate_collection_attributes.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.constants import DF_URL_PREFIX
import logging
import transaction

logger = logging.getLogger(__name__)
VERSION = 8
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def migrate_collection_attributes(app):
    catalog = app.unrestrictedTraverse('/Catalog')
    brains = catalog({'meta_type': 'Report Collection'})

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
                do_update = True
                obj.endyear = ''

            if hasattr(obj, 'main_issues'):
                do_update = True
                del obj.main_issues
            if hasattr(obj, 'broad'):
                do_update = True
                del obj.broad
            if hasattr(obj, 'narrow'):
                do_update = True
                del obj.narrow
            if hasattr(obj, 'media'):
                do_update = True
                del obj.media
            if hasattr(obj, 'response'):
                do_update = True
                del obj.response
            if hasattr(obj, 'pressures'):
                do_update = True
                del obj.pressures
            if hasattr(obj, 'impacts'):
                do_update = True
                del obj.impacts
            if hasattr(obj, 'keywords'):
                do_update = True
                del obj.keywords
            # The new URI-based obligation codes. Can now be multiple
            # Old reportek could only use ROD.
            if not hasattr(obj, 'dataflow_uris'):
                if obj.dataflow:
                    obj.dataflow_uris = [DF_URL_PREFIX + obj.dataflow]
                else:
                    obj.dataflow_uris = []
                do_update = True

            if do_update:
                obj.reindex_object()

            if count % 10000 == 0:
                transaction.savepoint()
                logger.info('savepoint at %d records', count)

            count += 1

    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=True):
    if not migrate_collection_attributes(app):
        return

    logger.info('Collections attributes have been migrated')
    return True
