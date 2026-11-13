import logging
from time import time

from OFS.SimpleItem import SimpleItem
from plone.memoize import ram
from ZODB.PersistentMapping import PersistentMapping

from Products.Reportek.RegistryManagement import (
    RegistryUnavailable,
    failed_in_this_request,
    is_cold,
    lookup_stats,
    remember_failure_in_this_request,
)

logger = logging.getLogger("Reportek")

__all__ = ["BdrAuthorizationMiddleware"]


def _paths_key(fun, self, username, userdata=None, recheck_interval=300):
    """The paths depend on what is asked: userdata is part of the key."""
    asked = tuple(sorted((userdata or {}).items()))
    return (username, asked, time() // recheck_interval)


PATHS = (__name__, "_cachedUserCollectionPaths")


class BdrAuthorizationMiddleware(SimpleItem):
    recheck_interval = 300

    def __init__(self, url):
        self.recheck_interval = 300
        self.lockedDownCollections = PersistentMapping()

    def setServiceRecheckInterval(self, seconds):
        self.recheck_interval = seconds

    def getUserCollectionPaths(
        self, username, userdata=None, recheck_interval=recheck_interval
    ):
        """The paths the registry gives the user, kept for recheck_interval.

        When the registry cannot be reached the user gets no paths. That is not
        kept: the rest of the request does not ask again, the next request does.
        """
        failed = ("paths",) + _paths_key(
            None, self, username, userdata, recheck_interval
        )
        if failed_in_this_request(failed):
            return {"paths": [], "prev_paths": [], "audit_paths": []}
        lookup_stats.record("paths", "lookup")
        try:
            return self._cachedUserCollectionPaths(
                username, userdata=userdata, recheck_interval=recheck_interval
            )
        except RegistryUnavailable:
            lookup_stats.record("paths", "failure")
            remember_failure_in_this_request(failed)
            return {"paths": [], "prev_paths": [], "audit_paths": []}

    def paths_request(self, username, userdata=None, recheck_interval=300):
        """The (url, kwargs) that the paths of the user need, when not kept."""
        key = _paths_key(None, self, username, userdata, recheck_interval)
        if failed_in_this_request(("paths",) + key) or not is_cold(PATHS, key):
            return None
        return self.FGASRegistryAPI.paths_request(username, userdata=userdata)

    @ram.cache(_paths_key)
    def _cachedUserCollectionPaths(
        self, username, userdata=None, recheck_interval=recheck_interval
    ):
        logger.debug("Get companies from middleware for ecas user: %s" % username)
        started = time()
        try:
            return self.FGASRegistryAPI._fetchCollectionPaths(
                username, userdata=userdata
            )
        finally:
            lookup_stats.record("paths", "miss", time() - started)

    def authorizedUser(self, username, path, userdata=None):
        if self.lockedCollection(path):
            logger.warning("This collection is locked down: %s!" % path)
            return False
        accessiblePaths = self.getUserCollectionPaths(
            username, userdata=userdata, recheck_interval=self.recheck_interval
        )
        for ap in accessiblePaths.get("paths"):
            if ap in path:
                return "RW"
        for ap in accessiblePaths.get("prev_paths"):
            if ap in path:
                return "RO"
        for ap in accessiblePaths.get("audit_paths"):
            if ap in path:
                return "AUDIT"
        return False

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
