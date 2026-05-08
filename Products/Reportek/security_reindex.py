"""Security reindex for local-role changes.

Replace for `reindexObjectSecurity()` cascade with a
batched walker:

* `reindex_security_batched` walks the catalog under the object's path
  and reindexes the security indexes on each descendant in batches,
  with intermediate transaction savepoints and ZODB cache GC.

The walker runs synchronously in the request that mutated the local
roles. The decoupling from `Collection.manage_*LocalRoles` is via a
`LocalRolesChangedEvent` subscriber.
"""

import logging

import transaction

from Products.Reportek.config import DEPLOYMENT_BDR, REPORTEK_DEPLOYMENT
from Products.Reportek.constants import DEFAULT_CATALOG

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 500
SECURITY_INDEXES = ("allowedRolesAndUsers", "allowedAdminRolesAndUsers")


def reindex_security_batched(obj, batch_size=DEFAULT_BATCH_SIZE):
    """Reindex security indexes on every descendant of `obj` in batches.

    Returns the number of descendants reindexed (excluding `obj` itself,
    which the caller is expected to have reindexed).
    """
    catalog = obj.unrestrictedTraverse(DEFAULT_CATALOG, None)
    if catalog is None:
        return 0
    self_path = "/".join(obj.getPhysicalPath())
    brains = catalog.unrestrictedSearchResults(path=self_path)
    reindexed = 0
    for brain in brains:
        brain_path = brain.getPath()
        if brain_path == self_path:
            continue
        try:
            ob = brain._unrestrictedGetObject()
        except (AttributeError, KeyError):
            continue
        if ob is None:
            logger.warning(
                "reindex_security_batched: cannot get %s from catalog",
                brain_path,
            )
            continue
        was_ghost = getattr(ob, "_p_changed", 0) is None
        catalog._reindexObject(ob, idxs=SECURITY_INDEXES, update_metadata=0)
        if was_ghost:
            ob._p_deactivate()
        reindexed += 1
        if batch_size and reindexed % batch_size == 0:
            transaction.savepoint(optimistic=True)
            jar = getattr(obj, "_p_jar", None)
            if jar is not None:
                jar.cacheGC()
    return reindexed


def on_local_roles_changed(obj, event):
    """Subscriber for LocalRolesChangedEvent.

    Only BDR triggered `reindexObjectSecurity()` from the ZMI form,
    so only BDR runs the descendant reindex here.
    """
    if REPORTEK_DEPLOYMENT != DEPLOYMENT_BDR:
        return
    count = reindex_security_batched(obj)
    logger.info(
        "security reindex: %d descendant(s) under %s",
        count,
        "/".join(obj.getPhysicalPath()),
    )
