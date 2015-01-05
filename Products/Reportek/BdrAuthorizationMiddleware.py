from OFS.Cache import Cacheable
from AccessControl import ClassSecurityInfo

from BdrAuthorizationMiddlewareApi import AuthMiddlewareApi

import logging
logger = logging.getLogger("Reportek")

__all__ = [
    'BdrAuthorizationMiddleware',
    'BdrUserFactoryPlugin',
    'manage_addBdrUserFactoryPluginForm',
    'addBdrUserFactoryPlugin',
    ]


class BdrAuthorizationMiddleware(Cacheable):

    def __init__(self, url):
        self.authMiddlewareApi = AuthMiddlewareApi(url)
        self.recheck_interval = 300

    def setServiceUrl(self, url):
        self.authMiddlewareApi.baseUrl = url

    def setServiceRecheckInterval(self, seconds):
        self.recheck_interval = seconds

    def getUserCollectionPaths(self, username):
        # TODO: cache this call
        accessiblePaths = self.authMiddlewareApi.getCollectionPaths(username)
        return accessiblePaths

    def authorizedUser(self, username, path):
        accessiblePaths = self.getUserCollectionPaths(username)
        return path in accessiblePaths


from App.class_init import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.interfaces.plugins import IUserFactoryPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from zope.interface import implements
from Products.PluggableAuthService.PropertiedUser import PropertiedUser


class BdrUserProperties(PropertiedUser):

    def get_roles_for_user_in_context(self, obj, user_id):
        # path of form 'fagses/ro/collection_id/some_deeper_path'
        if not hasattr(obj, 'absolute_url'):
            obj = obj.im_self
        current_path_parts = obj.absolute_url(1).split('/')
        if len(current_path_parts) < 3:
            return []

        col_path = '/'.join(current_path_parts[:3])
        if self.get_middleware_authorization(user_id, col_path):
            return ['Owner']
        return []

    def allowed(self, object, object_roles=None):
        basic = super(BdrUserProperties, self).allowed(object, object_roles)
        if basic:
            return 1

        user_id = self.getId()
        local_roles = self.get_roles_for_user_in_context(object, user_id)
        for role in object_roles:
            if role in local_roles:
                if self._check_context(object):
                    return 1
                return None

    def get_middleware_authorization(self, user_id, base_path):
        engine = self.unrestrictedTraverse('/ReportekEngine')
        authMiddleware = engine.authMiddlewareApi
        if authMiddleware:
            return authMiddleware.authorizedUser(user_id, base_path)
        return False



class BdrUserFactoryPlugin(BasePlugin):
    implements(IUserFactoryPlugin)

    meta_type = 'BDR User Factory Plugin'
    security = ClassSecurityInfo()

    def __init__( self, id, title=None ):
        self._setId( id )
        self.title = title

    security.declarePrivate('createUser')
    def createUser(self, user_id, name ):
        # here we can check if this user has information in the middleware
        # this is not strictly needed, we can skip this if we want

        return BdrUserProperties(id=user_id, login=name)


manage_addBdrUserFactoryPluginForm = PageTemplateFile(
    'zpt/bdrufAdd', globals(), __name__='manage_addBdrUserFactoryPluginForm' )

def addBdrUserFactoryPlugin( dispatcher, id, title='', RESPONSE=None ):
    """ Add a Local Role Plugin to 'dispatcher'.
    """

    plugin = BdrUserFactoryPlugin( id, title )
    dispatcher._setObject( id, plugin )

    if RESPONSE is not None:
        RESPONSE.redirect( '%s/manage_main?manage_tabs_message=%s' %
                           ( dispatcher.absolute_url()
                           , 'BdrUserFactory+added.' ) )


InitializeClass(BdrUserFactoryPlugin)
