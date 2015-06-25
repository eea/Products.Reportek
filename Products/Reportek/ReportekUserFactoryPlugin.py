from AccessControl import ClassSecurityInfo
from App.class_init import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluggableAuthService.interfaces.plugins import IUserFactoryPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.Reportek.ReportekPropertiedUser import ReportekPropertiedUser
from zope.interface import implements

__all__ = [
    'ReportekUserFactoryPlugin',
    'manage_addReportekUserFactoryPluginForm',
    'addReportekUserFactoryPlugin',
    ]


class ReportekUserFactoryPlugin(BasePlugin):
    implements(IUserFactoryPlugin)

    meta_type = 'Reportek User Factory Plugin'
    security = ClassSecurityInfo()

    def __init__( self, id, title=None ):
        self._setId( id )
        self.title = title

    security.declarePrivate('createUser')
    def createUser(self, user_id, name ):
        # here we can check if this user has information in the middleware
        # this is not strictly needed, we can skip this if we want

        return ReportekPropertiedUser(id=user_id, login=name)


manage_addReportekUserFactoryPluginForm = PageTemplateFile(
    'zpt/bdrufAdd', globals(), __name__='manage_addReportekUserFactoryPluginForm' )


def addReportekUserFactoryPlugin( dispatcher, id, title='', RESPONSE=None ):
    """ Add a Local Role Plugin to 'dispatcher'.
    """

    plugin = ReportekUserFactoryPlugin( id, title )
    dispatcher._setObject( id, plugin )

    if RESPONSE is not None:
        RESPONSE.redirect( '%s/manage_main?manage_tabs_message=%s' %
                           ( dispatcher.absolute_url()
                           , 'ReportekUserFactory+added.' ) )

InitializeClass(ReportekUserFactoryPlugin)
