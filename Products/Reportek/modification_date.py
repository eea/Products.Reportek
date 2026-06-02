# -*- coding: utf-8 -*-
"""Persistent Reportek modification date helpers.

ZODB ``_p_mtime`` is a storage-level timestamp and is rewritten by database
migration/update operations.  Reportek exposes business modification dates
through the historical ``bobobase_modification_time`` API, so the canonical
value must live in a normal persistent attribute instead.
"""

import logging

from Acquisition import aq_base, aq_parent
from DateTime import DateTime

from Products.Reportek.RepUtils import datify

logger = logging.getLogger(__name__)

MODIFICATION_DATE_ATTR = "reportek_modification_date"
MODIFICATION_INDEX = "bobobase_modification_time"

TARGET_META_TYPES = set(
    [
        "Report Collection",
        "Report Envelope",
        "Repository Referral",
        "Report Document",
        "Report Feedback",
        "Workitem",
    ]
)

CASCADE_META_TYPES = set(["Report Collection", "Report Envelope"])


def get_reportek_modification_date(obj):
    """Return the canonical Reportek modified date for *obj*.

    This function is intentionally side-effect free.  Missing legacy values are
    read from ``_p_mtime`` only as a fallback; the fallback is never persisted
    here because reads during catalog traversal/templates must not dirty ZODB
    objects.
    """
    date = getattr(aq_base(obj), MODIFICATION_DATE_ATTR, None)
    if date is not None:
        return datify(date)

    mtime = getattr(aq_base(obj), "_p_mtime", None)
    if mtime is not None and mtime > 0:
        return DateTime(mtime)

    return DateTime(0)


def set_reportek_modification_date(obj, date=None):
    """Persist *date* as the canonical Reportek modified date."""
    if date is None:
        date = DateTime()
    date = datify(date)
    setattr(obj, MODIFICATION_DATE_ATTR, date)
    return date


def is_target_content(obj):
    """Return True if *obj* is a cataloged Reportek content type we track."""
    return getattr(aq_base(obj), "meta_type", None) in TARGET_META_TYPES


def _should_cascade_to(obj):
    return getattr(aq_base(obj), "meta_type", None) in CASCADE_META_TYPES


def _iter_objects_to_mark(obj, cascade=True):
    """Yield *obj* and relevant acquisition parents once each."""
    seen = set()
    current = obj
    first = True
    while current is not None:
        base = aq_base(current)
        ident = id(base)
        if ident in seen:
            break
        seen.add(ident)

        if first:
            if is_target_content(current):
                yield current
        elif cascade and _should_cascade_to(current):
            yield current

        first = False
        if not cascade:
            break
        try:
            current = aq_parent(current)
        except Exception:
            break


def _reindex_modification_date(obj):
    reindex = getattr(obj, "reindexObject", None)
    if reindex is None:
        return
    try:
        reindex(idxs=[MODIFICATION_INDEX], update_metadata=1)
    except Exception:
        logger.exception("Could not reindex %s for %r", MODIFICATION_INDEX, obj)
        raise


def mark_modified(obj, date=None, cascade=True, reindex=True):
    """Mark Reportek content as modified and optionally update parents.

    Cascading is upward only: child content updates its containing envelope and
    parent collections, but parent edits never update descendants.
    """
    date = datify(date or DateTime())
    marked = []
    for item in _iter_objects_to_mark(obj, cascade=cascade):
        set_reportek_modification_date(item, date)
        marked.append(item)
        if reindex:
            _reindex_modification_date(item)
    return marked
