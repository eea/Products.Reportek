"""
Updates regarding Authentication in Reportek.
These methods do not perform transaction commit, you have to do it by yourself.

Usage:

>>> from update_auth import update_authentication
>>> update_authentication(app)
>>> import transaction; transaction.commit()

Obs: This update_auth package needs to be in Python PATH


To install simple PAS-based authentication, e.g. on a fresh database, for
testing, you can call add_PAS directly:

>>> from Products.Reportek.auth import add_PAS
>>> pas = add_PAS(app)
>>> pas['users'].addUser(user_id='admin', login_name='admin', password='admin')
>>> pas['roles'].assignRoleToPrincipal(role_id='Manager', principal_id='admin')
>>> import transaction; transaction.commit()

"""
import Products.PluggableAuthService.interfaces.plugins as plugin_interfaces
from Products.LDAPMultiPlugins.LDAPMultiPlugin import LDAPMultiPlugin
from Products.LDAPUserFolder.LDAPUserFolder import (LDAPUserFolder,
                                                    manage_addLDAPUserFolder)
from Products.Reportek.auth import add_PAS
from update_auth.ldapfolder_migration import (exportLDAPUserFolder,
                                              importLDAPUserFolder)

LDAPMULTIPLUGIN_ID = 'ldapmultiplugin'


def add_ldap_plugin(pas):
    """ Adds LDAPMultiPlugin to PluggableAuthService, without LDAPUserFolder
    """
    ldap_plugin_id = LDAPMULTIPLUGIN_ID
    lmp = LDAPMultiPlugin(ldap_plugin_id, 'LDAP Multi Plugin')
    pas._setObject(ldap_plugin_id, lmp)

    plugin_activation = [
        (ldap_plugin_id, 'IAuthenticationPlugin'),
        (ldap_plugin_id, 'IUserEnumerationPlugin'),
        (ldap_plugin_id, 'IRolesPlugin'),
        (ldap_plugin_id, 'IRoleEnumerationPlugin'),
        (ldap_plugin_id, 'ICredentialsResetPlugin'),
    ]

    for plugin_id, type_name in plugin_activation:
        plugin_type = getattr(plugin_interfaces, type_name)
        pas['plugins'].activatePlugin(plugin_type, plugin_id)

    return pas[ldap_plugin_id]


def update_authentication(app):
    """
    This must be called in debug for full migration from LDAPUserFolder 2.9 to
    PAS. After migration, Products.LDAPUserFolder 2.23 can be used
    """
    setattr(LDAPUserFolder, '_hash', 'mock-this')  # can not unpickle
    exportLDAPUserFolder(app)
    delattr(LDAPUserFolder, '_hash')

    local_users = {}
    for username in app.acl_users.data:
        user = app.acl_users.data[username]
        local_users[username] = {'role': user.roles[0], 'pass': user.__}

    pas = add_PAS(app, cookie_auth=False)
    for user_id in local_users:
        user = local_users[user_id]
        pas['users'].addUser(user_id=user_id,
                             login_name=user_id,
                             password=user['pass'])
        pas['roles'].assignRoleToPrincipal(role_id=user['role'],
                                           principal_id=user_id)

    lmp = add_ldap_plugin(pas)
    manage_addLDAPUserFolder(lmp)
    importLDAPUserFolder(lmp)
    # From Products.LDAPMultiPlugins:
    # clean out the __allow_groups__ bit because it is not needed here
    # and potentially harmful
    if hasattr(lmp, '__allow_groups__'):
        del lmp.__allow_groups__

    # What was lost in export-import of LDAPUserFolder
    lmp.acl_users._rdnattr = 'uid'
    lmp.acl_users._uid_attr = 'uid'
    for role in app.valid_roles():
        if role not in ('Anonymous', 'Authenticated'):
            lmp.acl_users.manage_addGroupMapping(role, role)

    # del app.loggedin
    # del app.loggedout
