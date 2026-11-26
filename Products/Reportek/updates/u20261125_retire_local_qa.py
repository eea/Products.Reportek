# -*- coding: utf-8 -*-
"""Retire /QARepository, its local QA scripts and the legacy Converter objects.

A local QAScript's ``script_url`` and a persistent Converter's ``convert_url``
were command lines run on the Zope host. The code that ran them is gone (see
Products.Reportek.qa); this update removes the stored objects:

1. copies the QA application path from /QARepository to ReportekEngine's
   ``QA_application``, which is where Products.Reportek.qa now reads it;
2. deletes /QARepository and everything in it;
3. deletes any Converter objects stored in /Converters. Local conversions
   come from the local-converters service and are not stored there.

Export /QARepository (ZMI Import/Export) and keep a copy of Data.fs first:
the objects cannot be restored otherwise. If /QARepository still holds
anything, the update refuses to run unless it is called with
``confirm_exported=True``, so a click on the Migrations tab cannot destroy it.

Only object ids and SHA-256 hashes of the stored command lines are logged,
never the command lines, which may contain passwords.

Run from Zope debug/zconsole after deploying this code::

    from Products.Reportek.updates import u20261125_retire_local_qa
    u20261125_retire_local_qa.update(app, confirm_exported=True)
"""

import hashlib
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

VERSION = 26
APPLIES_TO = [DEPLOYMENT_BDR, DEPLOYMENT_CDR, DEPLOYMENT_MDR]

LEGACY_CONVERTER_META_TYPE = "Converter"


def log_msg(msg, level="INFO"):
    logger.log(logging.getLevelName(level), msg)
    print(msg)


def _fingerprint(value):
    if not isinstance(value, str):
        value = repr(value)
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:16]


def copy_qa_application(app, qarepo):
    """QARepository.QA_application was the path in use; ReportekEngine's own
    QA_application property was not read by anything until now."""
    engine = getattr(app, constants.ENGINE_ID, None)
    if engine is None:
        log_msg("No ReportekEngine found; QA_application not copied", "WARNING")
        return False
    old = getattr(aq_base(qarepo), "QA_application", "")
    current = getattr(engine, "QA_application", "")
    if old and old != current:
        engine.QA_application = old
        log_msg(
            "ReportekEngine.QA_application set to %r (was %r)" % (old, current)
        )
    else:
        log_msg("ReportekEngine.QA_application kept as %r" % (current,))
    return True


def remove_qa_repository(app, qarepo):
    ids = list(qarepo.objectIds())
    for ob in qarepo.objectValues():
        log_msg(
            "Removing %s %s (script_url sha256 %s)"
            % (
                ob.meta_type,
                ob.getId(),
                _fingerprint(getattr(aq_base(ob), "script_url", "")),
            )
        )
    app._delObject(constants.QAREPOSITORY_ID)
    log_msg("Removed /%s and %d object(s) in it" % (constants.QAREPOSITORY_ID, len(ids)))


def remove_legacy_converters(app):
    converters = getattr(aq_base(app), constants.CONVERTERS_ID, None)
    if converters is None:
        return
    legacy = converters.objectIds(LEGACY_CONVERTER_META_TYPE)
    for conv_id in legacy:
        ob = converters._getOb(conv_id)
        log_msg(
            "Removing legacy Converter %s (convert_url sha256 %s)"
            % (conv_id, _fingerprint(getattr(aq_base(ob), "convert_url", "")))
        )
    for conv_id in list(legacy):
        converters._delObject(conv_id)
    log_msg("Removed %d legacy Converter object(s)" % len(legacy))


def retire_local_qa(app, confirm_exported=False):
    qarepo = getattr(aq_base(app), constants.QAREPOSITORY_ID, None)
    if qarepo is not None:
        count = len(qarepo.objectIds())
        if count and not confirm_exported:
            log_msg(
                "/%s still holds %d object(s). Export it and keep a copy of "
                "Data.fs, then run update(app, confirm_exported=True)."
                % (constants.QAREPOSITORY_ID, count),
                "WARNING",
            )
            transaction.abort()
            return False
        qarepo = getattr(app, constants.QAREPOSITORY_ID)
        if not copy_qa_application(app, qarepo):
            transaction.abort()
            return False
        remove_qa_repository(app, qarepo)
    else:
        log_msg("No /%s to remove" % constants.QAREPOSITORY_ID)

    remove_legacy_converters(app)
    transaction.commit()
    return True


@MigrationBase.checkMigration(__name__)
def update(app, confirm_exported=False, skipMigrationCheck=False):
    return retire_local_qa(app, confirm_exported=confirm_exported)
