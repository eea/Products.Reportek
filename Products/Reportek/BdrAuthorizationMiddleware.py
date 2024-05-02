import logging
from time import time

from OFS.SimpleItem import SimpleItem
from plone.memoize import ram
from ZODB.PersistentMapping import PersistentMapping

logger = logging.getLogger("Reportek")

__all__ = ["BdrAuthorizationMiddleware"]


class BdrAuthorizationMiddleware(SimpleItem):
    recheck_interval = 300

    def __init__(self, url):
        self.recheck_interval = 300
        self.lockedDownCollections = PersistentMapping()

    def setServiceRecheckInterval(self, seconds):
        self.recheck_interval = seconds

    @ram.cache(
        lambda *args, **kwargs: args[2]
        + str(time() // kwargs["recheck_interval"])
    )
    def getUserCollectionPaths(
        self, username, userdata=None, recheck_interval=recheck_interval
    ):
        logger.debug(
            "Get companies from middleware for ecas user: %s" % username
        )
        accessiblePaths = self.FGASRegistryAPI.getCollectionPaths(
            username, userdata=userdata
        )
        return accessiblePaths

    def authorizedUser(self, username, path, userdata=None):
        if self.lockedCollection(path):
            logger.warning("This collection is locked down: %s!" % path)
            return False
        accessiblePaths = self.getUserCollectionPaths(
            username, userdata=userdata, recheck_interval=self.recheck_interval
        )
        if path in accessiblePaths.get("paths"):
            return "RW"
        if path in accessiblePaths.get("prev_paths"):
            return "RO"

    def lockDownCollection(self, path, user):
        if path not in self.lockedDownCollections:
            self.lockedDownCollections[path] = None
        self.lockedDownCollections[path] = {
            "state": "locked",
            "ts": time(),
            "user": user,
        }

    def unlockCollection(self, path, user):
        if path not in self.lockedDownCollections:
            # log unlock without lock
            self.lockedDownCollections[path] = None
        self.lockedDownCollections[path] = {
            "state": "unlocked",
            "ts": time(),
            "user": user,
        }

    def lockedCollection(self, path):
        lockedItem = self.lockedDownCollections.get(path)
        return lockedItem and lockedItem["state"] == "locked"
