# -*- coding: utf-8 -*-
# Migrate authMiddlewareApi (BDR Only)
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20151127_Migrate_AuthMiddlewareApi_and_company_ids; u20151127_Migrate_AuthMiddlewareApi_and_company_ids.update(app)

from Products.Reportek.updates import MigrationBase
import transaction

VERSION = 5


def migrate_AuthMiddleWareApi(app):
    engine = app.unrestrictedTraverse('/ReportekEngine')
    authMiddlewareApi = getattr(engine, '_authMiddlewareApi', None)
    if authMiddlewareApi:
        lockedDownCollections = authMiddlewareApi.lockedDownCollections
        authMiddleware = engine.authMiddleware
        authMiddleware.lockedDownCollections = lockedDownCollections
        del engine._authMiddlewareApi
        transaction.commit()
        print 'Migration of lockedDownCollections and cleanup of old\
              _authmiddlewareApi done'

def add_company_id_to_collections(app):
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

@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    migrate_AuthMiddleWareApi(app)
    add_company_id_to_collections(app)
    print 'All done'
