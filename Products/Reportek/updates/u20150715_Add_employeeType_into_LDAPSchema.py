# -*- coding: utf-8 -*-
# Add employeeType property to LDAP Schema
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import\
#   u20150715_Add_employeeType_into_LDAPSchema
#  >>> u20150715_Add_employeeType_into_LDAPSchema.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
import transaction

VERSION = 4
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    acl_users = app.unrestrictedTraverse('/acl_users')

    trans = transaction.begin()
    try:
        ldapplugins = acl_users.objectIds('LDAP Multi Plugin')

        for plugin_id in ldapplugins:
            plugin = acl_users[plugin_id]
            ldapfolder = getattr(plugin, 'acl_users')

            if ldapfolder:
                ldapfolder.manage_addLDAPSchemaItem(ldap_name='employeeType',
                                                    friendly_name='disabled')
                print ("Added 'employeeType' with friendly name 'disabled' to\
                        %s" % ldapfolder.absolute_url())
                trans.commit()
                return True
    except Exception:
        trans.abort()
        raise
