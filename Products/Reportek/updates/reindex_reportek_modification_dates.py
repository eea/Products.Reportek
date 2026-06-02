# -*- coding: utf-8 -*-
"""Reindex persisted Reportek modification dates after migration.

This refreshes only the historical ``bobobase_modification_time`` index and
metadata column.  It intentionally avoids full ``reindexObject()`` calls so the
persisted business modification date is not advanced during migration repair.
"""

import logging

import transaction
from Acquisition import aq_base

from Products.Reportek.modification_date import (
    MODIFICATION_DATE_ATTR,
    MODIFICATION_INDEX,
    TARGET_META_TYPES,
)

logger = logging.getLogger(__name__)


def _get_catalog(app):
    catalog = getattr(app, "Catalog", None)
    if catalog is None:
        catalog = app.unrestrictedTraverse("Catalog", None)
    if catalog is None:
        raise RuntimeError("Could not find Reportek Catalog")
    return catalog


def update(app, batch_size=1000, missing_only=False, dry_run=False):
    """Refresh the modification date catalog index/metadata.

    :param app: Zope app root
    :param batch_size: commit interval
    :param missing_only: process only objects without reportek_modification_date
    :param dry_run: count objects without reindexing
    :return: dict with counters
    """
    catalog = _get_catalog(app)
    brains = catalog(meta_type=list(TARGET_META_TYPES))
    total = len(brains)
    reindexed = 0
    missing = 0
    skipped = 0
    failed = 0

    logger.info("Reindexing %s for %s catalog brains", MODIFICATION_INDEX, total)

    for index in range(total):
        try:
            brain = brains[index]
            obj = brain.getObject()
            if obj is None:
                skipped += 1
                continue
            has_date = getattr(aq_base(obj), MODIFICATION_DATE_ATTR, None) is not None
            if not has_date:
                missing += 1
            if missing_only and has_date:
                skipped += 1
                continue
            if not dry_run:
                obj.reindexObject(idxs=[MODIFICATION_INDEX], update_metadata=1)
            reindexed += 1
        except Exception:
            failed += 1
            logger.exception("Failed to reindex %r", brain)

        processed = index + 1
        if not dry_run and processed % batch_size == 0:
            transaction.commit()
            logger.info(
                "Reindex progress: %s/%s processed, %s reindexed, %s missing, %s skipped, %s failed",
                processed,
                total,
                reindexed,
                missing,
                skipped,
                failed,
            )

    if not dry_run:
        transaction.commit()

    result = {
        "total": total,
        "reindexed": reindexed,
        "missing": missing,
        "skipped": skipped,
        "failed": failed,
        "dry_run": dry_run,
    }
    logger.info("Reindex complete: %r", result)
    return result
