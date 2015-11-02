from time import time

import ExtensionClass
from ZODB.PersistentMapping import PersistentMapping

from plone.memoize import ram

from BdrAuthorizationMiddlewareApi import AuthMiddlewareApi

import logging
logger = logging.getLogger("Reportek")

__all__ = [
    'BdrAuthorizationMiddleware'
    ]


class BdrAuthorizationMiddleware(ExtensionClass.Base):

    recheck_interval = 300

    def __init__(self, url):
        self.authMiddlewareApi = AuthMiddlewareApi(url)
        self.recheck_interval = 300
        self.lockedDownCollections = PersistentMapping()

    def setServiceUrl(self, url):
        self.authMiddlewareApi.baseUrl = url

    def setServiceRecheckInterval(self, seconds):
        self.recheck_interval = seconds

    @ram.cache(lambda *args, **kwargs: args[2] + str(time() // kwargs['recheck_interval']))
    def getUserCollectionPaths(self, username, recheck_interval=recheck_interval):
        logger.debug("Get companies from middleware for ecas user: %s" % username)
        accessiblePaths = self.authMiddlewareApi.getCollectionPaths(username)
        return accessiblePaths

    def authorizedUser(self, username, path):
        if path in self.lockedDownCollections:
            logger.warning("This collection is locked down: %s!" % path)
            return False
        accessiblePaths = self.getUserCollectionPaths(username, recheck_interval=self.recheck_interval)
        return path in accessiblePaths

    def lockDownCollection(self, path, user):
        if path not in self.lockedDownCollections:
            self.lockedDownCollections[path] = None
        self.lockedDownCollections[path] = {'state': 'locked',
                                            'ts': time(),
                                            'user': user}

    def unlockCollection(self, path, user):
        if path not in self.lockedDownCollections:
            # log unlock without lock
            self.lockedDownCollections[path] = None
        self.lockedDownCollections[path] = {'state': 'unlocked',
                                            'ts': time(),
                                            'user': user}

    def lockedCollection(self, path):
        lockedItem = self.lockedDownCollections.get(path)
        return lockedItem and lockedItem['state'] == 'locked'
