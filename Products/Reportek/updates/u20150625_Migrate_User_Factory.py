# -*- coding: utf-8 -*-
# Create ReportekUserFactoryPlugin and remove BDRUserFactoryPlugin
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20150625_Migrate_User_Factory; u20150625_Migrate_User_Factory.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.ReportekUserFactoryPlugin import addReportekUserFactoryPlugin
from Products.PluggableAuthService.interfaces.plugins import IUserFactoryPlugin
import transaction

VERSION = 3


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    """
    """
    acl_users = app.unrestrictedTraverse('/acl_users')

    trans = transaction.begin()
    try:
        # Remove old bdr-ecas-user-factory if we find it
        if 'bdr-ecas-user-factory' in acl_users.objectIds():
            del acl_users['bdr-ecas-user-factory']
        # Let's add the new plugin
        addReportekUserFactoryPlugin(acl_users, 'reportek-user-factory')
        # Now we need to activate it
        plugins = acl_users._getOb('plugins')
        plugins.activatePlugin(IUserFactoryPlugin, 'reportek-user-factory')
        trans.commit()
        print "All done!"
    except:
        trans.abort()
        raise
