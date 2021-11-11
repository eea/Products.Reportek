# -*- coding: utf-8 -*-
# Migrate partofyear attribute to more sane values
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20160720_Migrate_partofyear
#  >>> u20160720_Migrate_partofyear.update(app)

from Acquisition import aq_base
from Products.Reportek.updates import MigrationBase
from Products.Reportek.vocabularies import REPORTING_PERIOD_DESCRIPTION as rpd
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.config import DEPLOYMENT_MDR
import transaction
import logging
logger = logging.getLogger("Reportek")

VERSION = 6
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def migrate_partofyear(app, ctype):
    catalog = getattr(app, 'Catalog')
    # Convert the LazyMap to list otherwise we can't loop over all items for
    # some reason
    brains = list(catalog(meta_type=ctype))
    logger.info("Total number of {} type objects is: {}".format(ctype,
                                                                len(brains)))
    count = 0
    changed_count = 0
    for brain in brains:
        obj = brain.getObject()
        existing = aq_base(obj).partofyear
        if existing:
            try:
                obj.partofyear = rpd.keys()[rpd.values().index(existing)]
                obj.reindex_object()
                changed_count += 1
            except Exception as e:
                logger.error("Unable to change value {}\
                              for {} due to {}".format(obj.partofyear,
                                                       obj.absolute_url(),
                                                       str(e)))
            if (count % 1000) == 0:
                logger.info("Savepoint at: {} objects".format(count))
                transaction.savepoint()
            count += 1
    logger.info("Total number of changed {} type objects: {}".format(
        ctype, changed_count))
    transaction.commit()


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    migrate_partofyear(app, 'Report Collection')
    logger.info("Collections updated")
    migrate_partofyear(app, 'Report Envelope')
    logger.info("Envelopes updated")
    return True
