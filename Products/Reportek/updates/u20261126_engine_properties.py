# -*- coding: utf-8 -*-
"""Drop UNS_password from the property list stored on ReportekEngine.

Some engines keep their own copy of ``_properties`` in the ZODB, so removing
the entry from the class is not enough for them. The other properties, and
the UNS_password attribute itself, are left as they are.

Run from Zope debug/zconsole after deploying this code, or from the engine's
Migrations tab::

    from Products.Reportek.updates import u20261126_engine_properties
    u20261126_engine_properties.update(app)
"""

import logging

import transaction
from Acquisition import aq_base

from Products.Reportek import constants
from Products.Reportek.config import (
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR,
)
from Products.Reportek.updates import MigrationBase

logger = logging.getLogger(__name__)

VERSION = 27
APPLIES_TO = [DEPLOYMENT_BDR, DEPLOYMENT_CDR, DEPLOYMENT_MDR]

HIDDEN = ("UNS_password",)


def log_msg(msg, level="INFO"):
    logger.log(logging.getLevelName(level), msg)
    print(msg)


def drop_hidden_properties(app):
    engine = getattr(aq_base(app), constants.ENGINE_ID, None)
    if engine is None:
        log_msg("No ReportekEngine found", "WARNING")
        return False
    engine._p_activate()
    stored = engine.__dict__.get("_properties")
    if stored is None:
        log_msg("ReportekEngine uses the class property list; nothing to do")
        return True
    kept = tuple(p for p in stored if p.get("id") not in HIDDEN)
    if len(kept) != len(stored):
        engine._properties = kept
        transaction.commit()
        log_msg("Removed %s from the ReportekEngine property list" % ", ".join(HIDDEN))
    else:
        log_msg("ReportekEngine property list already clean")
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    return drop_hidden_properties(app)
