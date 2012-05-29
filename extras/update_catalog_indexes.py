"""
Clean unused Catalog indexes and metadata and reindex the Catalog records.

"""

import logging
from Products.Reportek import create_reportek_indexes
from Products.Reportek.constants import DEFAULT_CATALOG
from Products.Reportek.tests.utils import makerequest
from Products.Reportek.catalog import catalog_rebuild

handler = logging.StreamHandler()

log = logging.getLogger(__name__)
log.addHandler(handler)
log.setLevel(logging.INFO)

catalog_log = logging.getLogger('Products.Reportek.catalog')
catalog_log.addHandler(handler)
catalog_log.setLevel(logging.INFO)


def get_catalog(app):
    return getattr(app, DEFAULT_CATALOG)

def update_indexes(app):
    """
    Remove all Catalog indexes and metadata. Use `create_reportek_indexes` to
    create the new indexes and metadata. Reindex the Catalog after.

    >>> import update_catalog_indexes
    >>> update_catalog_indexes.update_indexes(app)
    >>> import transaction; transaction.commit()
    # Estimated time: 10-15 minutes

    """

    app = makerequest(app)

    catalog = get_catalog(app)

    catalog.manage_catalogClear()
    log.info('Clear Catalog')

    available_indexes = catalog.indexes()
    catalog.manage_delIndex(available_indexes)

    available_metadata = catalog.schema()
    catalog.manage_delColumn(available_metadata)

    log.info('Old indexes and metadata are removed from Catalog')

    create_reportek_indexes(catalog)
    log.info('New indexes and metadata are added in Catalog')

    catalog_rebuild(app)
    log.info('Catalog records are reindexed')
