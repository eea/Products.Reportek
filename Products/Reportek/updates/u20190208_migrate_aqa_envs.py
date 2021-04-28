# flake8: noqa
# -*- coding: utf-8 -*-
# Migrate fgases_xml
# Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20190208_migrate_aqa_envs; u20190208_migrate_aqa_envs.update(app)

import logging

import transaction
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.updates import MigrationBase

logger = logging.getLogger(__name__)
VERSION = 17
APPLIES_TO = [
    DEPLOYMENT_CDR,
]


def log_msg(msg, level='INFO'):
    lvl = {
        'CRITICAL': 50,
        'ERROR': 40,
        'WARNING': 30,
        'INFO': 20,
        'DEBUG': 10,
        'NOTSET': 0
    }
    logger.log(lvl.get(level), msg)
    print msg


def migrate_aqa_envs(app):
    engine = app.unrestrictedTraverse('/' + ENGINE_ID)
    brains = engine.get_apps_wks(['AutomaticQA'])

    for brain in brains:
        env = None
        try:
            env = brain.getObject().getParentNode()
        except Exception as e:
            log_msg('Unable to retrieve object: {} due to {}'.format(
                brain.getURL(), str(e)), level='ERROR')
        if env and getattr(env, 'status') != 'complete':
            env.wf_status = 'forward'
            env.reindex_object()
            log_msg('Migrated {}'.format(env.absolute_url()))
            transaction.commit()
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    if not migrate_aqa_envs(app):
        return

    log_msg('AutomaticQA envs migration complete')
    return True
