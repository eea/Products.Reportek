"""
Updates regarding Authentication in Reportek.
These methods do not perform transaction commit, you have to do it by yourself.

Usage:
>>> from update_auth import update_authentication
>>> update_authentication(app)
>>> import transaction; transaction.commit()


To install simple PAS-based authentication, e.g. on a fresh database, for
testing, you can call add_PAS directly:

>>> import update_auth, transaction
>>> update_auth.add_PAS(app, {'admin': {'pass': 'admin', 'role': 'Manager'}})
>>> import transaction.commit()

"""

LDAPMULTIPLUGIN_ID = 'ldapmultiplugin'


def add_PAS(app, local_users):
    """
    Full configuration of PluggableAuthService:
    - local users plugin
    - Zope Roles plugin
    - http basic auth plugin
    - cookie auth plugin
    - LDAPMultiPlugin - without LDAPUserFolder!
    - adds local_users - dict {user_id: {'role': .., 'pass': .. }, ..}

    """
    from Products.PluggableAuthService.PluggableAuthService import addPluggableAuthService
    from Products.PluggableAuthService.plugins.ZODBRoleManager import addZODBRoleManager
    from Products.PluggableAuthService.plugins.ZODBUserManager import addZODBUserManager
    from Products.PluggableAuthService.plugins.CookieAuthHelper import addCookieAuthHelper
    from Products.PluggableAuthService.plugins.HTTPBasicAuthHelper import addHTTPBasicAuthHelper
    import Products.PluggableAuthService.interfaces.plugins as plugin_interfaces
    from Products.LDAPMultiPlugins.LDAPMultiPlugin import LDAPMultiPlugin

    del app['acl_users']
    addPluggableAuthService(app)
    addZODBUserManager(app['acl_users'], 'users')
    addZODBRoleManager(app['acl_users'], 'roles')
    addCookieAuthHelper(app['acl_users'], 'cookie_auth')
    addHTTPBasicAuthHelper(app['acl_users'], 'basic_auth')

    # Instantiate the folderish adapter object
    pas = app['acl_users']
    id = LDAPMULTIPLUGIN_ID
    lmp = LDAPMultiPlugin(id, 'LDAP Multi Plugin')
    pas._setObject(id, lmp)

    plugin_activation = [
        ('users', 'IAuthenticationPlugin'),
        ('users', 'IUserEnumerationPlugin'),
        ('users', 'IUserAdderPlugin'),
        ('roles', 'IRolesPlugin'),
        ('roles', 'IRoleEnumerationPlugin'),
        ('roles', 'IRoleAssignerPlugin'),
        ('cookie_auth', 'IExtractionPlugin'),
        ('cookie_auth', 'IChallengePlugin'),
        ('cookie_auth', 'ICredentialsUpdatePlugin'),
        ('cookie_auth', 'ICredentialsResetPlugin'),
        ('basic_auth', 'IExtractionPlugin'),
        ('basic_auth', 'IChallengePlugin'),
        ('basic_auth', 'ICredentialsResetPlugin'),
        (LDAPMULTIPLUGIN_ID, 'IAuthenticationPlugin'),
        (LDAPMULTIPLUGIN_ID, 'IUserEnumerationPlugin'),
        (LDAPMULTIPLUGIN_ID, 'IRolesPlugin'),
        (LDAPMULTIPLUGIN_ID, 'IRoleEnumerationPlugin'),
    ]

    for plugin_id, type_name in plugin_activation:
        plugin_type = getattr(plugin_interfaces, type_name)
        app['acl_users']['plugins'].activatePlugin(plugin_type, plugin_id)

    for user_id in local_users:
        user = local_users[user_id]
        app['acl_users']['users'].addUser(user_id=user_id,
                                          login_name=user_id,
                                          password=user['pass'])

        app['acl_users']['roles'].assignRoleToPrincipal(role_id=user['role'],
                                                        principal_id=user_id)

def update_authentication(app):
    """
    This must be called in debug for full migration from LDAPUserFolder 2.9 to PAS
    After migration, Products.LDAPUserFolder 2.13 can be used

    """
    from Products.Reportek.updates.ldapfolder_migration import exportLDAPUserFolder, importLDAPUserFolder
    from Products.LDAPUserFolder.LDAPUserFolder import manage_addLDAPUserFolder
    exportLDAPUserFolder(app)
    # grab local users
    local_users = {}
    for username in app.acl_users.data:
        user = app.acl_users.data[username]
        local_users[username] = {'role': user.roles[0], 'pass': user.__}
    # remove acl_users and add PAS with plugins, including LMP
    add_PAS(app, local_users)
    lmp = app.acl_users[LDAPMULTIPLUGIN_ID]
    manage_addLDAPUserFolder(lmp)
    importLDAPUserFolder(lmp)
    # From Products.LDAPMultiPlugins:
    ## clean out the __allow_groups__ bit because it is not needed here
    ## and potentially harmful
    if hasattr(lmp, '__allow_groups__'):
        del lmp.__allow_groups__

    # set rdn_attr
    lmp.acl_users._rdnattr = 'uid'
    # set all role mappings
    for role in app.valid_roles():
        if role not in ('Anonymous', 'Authenticated'):
            lmp.acl_users.manage_addGroupMapping(role, role)

