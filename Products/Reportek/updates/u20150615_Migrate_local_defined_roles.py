# -*- coding: utf-8 -*-
# Delete the 'local_defined_roles' FieldIndex and create it as metadata only
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20150615_Migrate_local_defined_roles; u20150615_Migrate_local_defined_roles.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.catalog import catalog_rebuild

import transaction

VERSION = 2


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    """
    """
    catalog = getattr(app, 'Catalog')
    trans = transaction.begin()
    try:
        catalog.delIndex('local_defined_roles')
        if 'local_defined_roles' not in catalog.schema():
            catalog.addColumn('local_defined_roles')
        catalog_rebuild(catalog.unrestrictedTraverse('/'))
        trans.commit()
        print "Migration complete!"
    except:
        trans.abort()
        raise
