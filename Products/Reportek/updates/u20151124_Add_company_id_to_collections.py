# -*- coding: utf-8 -*-
# Add company_id to BDR collections (BDR Only)
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20151124_Add_company_id_to_collections; u20151124_Add_company_id_to_collections.update(app)

from Products.Reportek.updates import MigrationBase
import transaction

VERSION = 6

@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    catalog = getattr(app, 'Catalog')
    paths = ['fgases', '/ods', '/cars', '/vans']
    for path in paths:
        brains = catalog({'path': path,
                          'meta_type': 'Report Collection'})
        for brain in brains:
            depth = len(brain.getPath().split('/'))
            if depth >= 4:
                obj = brain.getObject()
                if 'company_id' not in obj.__dict__:
                    obj.old_company_id = obj.getId()
                    print 'Added old_company_id: {0} to collection: {1}'.format(obj.getId(), obj.absolute_url())
                else:
                    obj.company_id = obj.__dict__['company_id']
                    print 'Added company_id: {0} to collection: {1}'.format(obj.company_id, obj.absolute_url())
                obj.reindex_object()

        transaction.commit()
    print 'All done!'
