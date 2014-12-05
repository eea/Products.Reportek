import Zope2
import transaction
import constants
from OFS.Cache import Cacheable
from Products.PluggableAuthService.utils import createViewName
from config import SATELLITE_REGISTRY_STICKY_USERS

from BdrAuthorizationMiddlewareApi import AuthMiddlewareApi

import time
import logging
logger = logging.getLogger("Reportek")

__all__ = [
    'BdrAuthorizationMiddleware',
    ]


class BdrAuthorizationMiddleware(Cacheable):

    def __init__(self, url):
        self.authMiddlewareApi = AuthMiddlewareApi(url)
        self.recheck_interval = 300

    def setServiceUrl(self, url):
        self.authMiddlewareApi.baseUrl = url

    def setServiceRecheckInterval(self, seconds):
        self.recheck_interval = seconds

    @classmethod
    def unassignRole(cls, coll, user, role='Owner'):
        roles = list(coll.get_local_roles_for_userid(user))
        try:
            roles.remove(role)
        except:
            pass
        if roles:
            coll.manage_setLocalRoles(user, roles)
        else:
            coll.manage_delLocalRoles([user])
        # FIXME due to a bug in zope, this method cannot be called outside of a request
        # FIXME but not calling it will render our algorithm wrong
        coll.reindex_object()

    @classmethod
    def assignRole(cls, coll, user, role='Owner'):
        local_roles = coll.local_defined_roles()

        coll.reindex_object()
        if user in local_roles and role in local_roles[user]:
            return
        roles = list(coll.get_local_roles_for_userid(user))
        roles.append(role)
        coll.manage_setLocalRoles(user, roles)
        # FIXME due to a bug in zope, this method cannot be called outside of a request
        # FIXME but not calling it will render our algorithm wrong
        coll.reindex_object()

    def _sticky_collectionForUser(self, user, path):
        if (user in SATELLITE_REGISTRY_STICKY_USERS
            and (not SATELLITE_REGISTRY_STICKY_USERS[user]
                    or path in SATELLITE_REGISTRY_STICKY_USERS[user]) ):
            logger.warning( ("Deciding user's %s local role on collection %s is sticky."
                             " Don't attempt permission removal") % (user, path) )
            return True
        return False

    def updateLocalRoles(self, user):
        view_name = createViewName('_updateLocalRoles', user)
        now = time.time()
        # FIXME This is called from PluggableAuthService:_extractUserIds that has
        # it's own cache guardian. Thus we will not get here unless that upper cache entry
        # expires. This makes sense only if we set recheck_interval to more that the upper one
        # I have no ideea what the expiration value of the upper one is
        # and there may be that no mortal knows...
        # Additionally, we don't have an cache manager set yet;
        # we might need to redo this object so we can manage it form ZMI
        # and add its ramcachemanager from there
        interval = now - self.ZCacheable_get(view_name, default=0)
        if interval < self.recheck_interval:
            return
        app = Zope2.bobo_application()
        try:
            # flush everything so far; we do this especially because our caller
            # has some data stored in session and that session will be reset
            # by the next 'begin' if not commited
            transaction.commit()
            transaction.begin()
            # call SatelliteRegistry to get companies for this user
            accessiblePaths = self.authMiddlewareApi.getCollectionPaths(user)
            if accessiblePaths is None:
                # skip commiting transaction; skip caching the last auth check time
                raise ValueError("Interrogating Bdr Middleware failed."
                                 " Proceding w/o refreshing authorizations for user %s."
                                 % user)
            # all we are looking for are local roles; company accounts should only have local roles
            catalog = getattr(app, constants.DEFAULT_CATALOG)
            collection_for_user = catalog(meta_type='Report Collection', local_defined_users=user)
            for colBr in collection_for_user:
                if user in colBr.local_defined_roles and 'Owner' in colBr.local_defined_roles[user]:
                    coll = colBr.getObject()
                    # mind the exception to this revoking
                    if not self._sticky_collectionForUser(user, coll.absolute_url(1)):
                        self.unassignRole(coll, user)
            # for accessible paths add user as owner
            for toOwn in accessiblePaths:
                try:
                    coll = app.unrestrictedTraverse(str(toOwn))
                except:
                    logger.info("Collection %s is not created yet" % toOwn)
                    continue
                self.assignRole(coll, user)
                logger.info("User %s is assigned local role Owner on collection %s" % (user, coll.absolute_url(1)))
            transaction.commit()
            self.ZCacheable_set(now, view_name)
        except Exception as e:
            logger.warning("Failed to refresh authorizations for user %s (%s)" % (user, repr(e)))
            transaction.abort()
            raise
