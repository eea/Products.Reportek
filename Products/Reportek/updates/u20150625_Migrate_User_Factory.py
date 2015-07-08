# -*- coding: utf-8 -*-
# Create ReportekUserFactoryPlugin and remove BDRUserFactoryPlugin
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20150625_Migrate_User_Factory; u20150625_Migrate_User_Factory.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.ReportekUserFactoryPlugin import addReportekUserFactoryPlugin
from Products.Reportek.config import REPORTEK_DEPLOYMENT
from Products.Reportek.config import DEPLOYMENT_CDR as CDR
from Products.Reportek.config import DEPLOYMENT_MDR as MDR

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
        # Now we need to activate it for CDR and BDR
        plugins = acl_users._getOb('plugins')
        if REPORTEK_DEPLOYMENT != MDR:
            plugins.activatePlugin(IUserFactoryPlugin, 'reportek-user-factory')

        # Migrate local users for CDR
        if REPORTEK_DEPLOYMENT == CDR:
            ldapplugins = acl_users.objectIds('LDAP Multi Plugin')

            for plugin_id in ldapplugins:
                plugin = acl_users[plugin_id]
                ldapfolder = getattr(plugin, 'acl_users')

                if ldapfolder:
                    # Let's set the Group to LDAP server
                    ldapfolder._setProperty('_local_groups', False)
                    # Set groups_base to ou=Roles
                    ldapfolder._setProperty('groups_base', 'ou=Roles,o=EIONET,l=Europe')
                    local_users = ldapfolder.getLocalUsers()
                    for user in local_users:
                        success = doMigrateLocalUser(acl_users, user)
                        if not success:
                            print 'Unable to migrate user: %s' % str(user)
                        else:
                            print 'Migrated user: %s' % str(user)

        trans.commit()
        print "All done!"
    except:
        trans.abort()
        raise


def doMigrateLocalUser(acl_users, user_data):
    user_roles = user_data[1]
    user_id = user_data[0].split('=')[1].split(',')[0]
    role_mgr = acl_users.get('roles')

    if role_mgr:
        for role in user_roles:
            assigned = role_mgr.listAssignedPrincipals(role)

            if (user_id not in [principal[0] for principal in assigned] and
               role_mgr.listAvailablePrincipals(role, user_id)):
                if role not in list(role_mgr.listRoleIds()):
                    role_mgr.addRole(role)
                if role_mgr.assignRoleToPrincipal(role, user_id):
                    print 'Added user: %s to role: %s' % (user_id, role)
                else:
                    return False

        return True

