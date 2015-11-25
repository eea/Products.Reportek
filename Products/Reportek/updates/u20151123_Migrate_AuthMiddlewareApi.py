# -*- coding: utf-8 -*-
# Migrate authMiddlewareApi (BDR Only)
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20151123_Migrate_AuthMiddlewareApi; u20151123_Migrate_AuthMiddlewareApi.update(app)

from Products.Reportek.updates import MigrationBase
import transaction

VERSION = 5


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
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
    print 'All done'
