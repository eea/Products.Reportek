""" Authentication library """
from Products.PluggableAuthService.PluggableAuthService import addPluggableAuthService
from Products.PluggableAuthService.plugins.ZODBRoleManager import addZODBRoleManager
from Products.PluggableAuthService.plugins.ZODBUserManager import addZODBUserManager
from Products.PluggableAuthService.plugins.CookieAuthHelper import addCookieAuthHelper
from Products.PluggableAuthService.plugins.HTTPBasicAuthHelper import addHTTPBasicAuthHelper
import Products.PluggableAuthService.interfaces.plugins as plugin_interfaces


def add_PAS(app):
    """
    Full configuration of PluggableAuthService:
    - local users plugin
    - Zope Roles plugin
    - http basic auth plugin
    - cookie auth plugin

    """
    if getattr(app, 'acl_users', False):
        del app['acl_users']
    addPluggableAuthService(app)
    pas = app['acl_users']
    addZODBUserManager(pas, 'users')
    addZODBRoleManager(pas, 'roles')
    addCookieAuthHelper(pas, 'cookie_auth')
    addHTTPBasicAuthHelper(pas, 'basic_auth')

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
    ]

    for plugin_id, type_name in plugin_activation:
        plugin_type = getattr(plugin_interfaces, type_name)
        pas['plugins'].activatePlugin(plugin_type, plugin_id)

    return pas
