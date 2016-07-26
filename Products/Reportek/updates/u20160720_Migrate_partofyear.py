# -*- coding: utf-8 -*-
# Migrate partofyear attribute to more sane values
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20160720_Migrate_partofyear; u20160720_Migrate_partofyear.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.vocabularies import REPORTING_PERIOD_DESCRIPTION as rpd
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.config import DEPLOYMENT_MDR
import transaction

VERSION = 6
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


def migrate_partofyear(app):
    catalog = getattr(app, 'Catalog')
    brains = catalog(meta_type='Report Envelope')
    for brain in brains:
        obj = brain.getObject()
        existing = obj.partofyear
        try:
            obj.partofyear = rpd.keys()[rpd.values().index(existing)]
            obj.reindex_object()
        except:
            print "Unable to change value {}".format(obj.partofyear)
    transaction.commit()


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    migrate_partofyear(app)
    print 'All done'
