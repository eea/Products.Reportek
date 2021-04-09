# -*- coding: utf-8 -*-
# This places a Persistent Mapping in the Data.fs to keep track of the executed updates
# It also contains the boilerplate to use when naming and running scripts
# 1. Name your scripts starting with `date -u '+u%Y%m%d_'` followed by a meaningfull name
# 2. Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20150209_MigrationTracking; u20150209_MigrationTracking.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.constants import ENGINE_ID, MIGRATION_ID
from Products.Reportek.config import DEPLOYMENT_CDR
from Products.Reportek.config import DEPLOYMENT_MDR
from Products.Reportek.config import DEPLOYMENT_BDR
import transaction
from ZODB.PersistentMapping import PersistentMapping

VERSION = 1
APPLIES_TO = [
    DEPLOYMENT_BDR,
    DEPLOYMENT_CDR,
    DEPLOYMENT_MDR
]


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=True):
    """    Create the mapping holding the migration history on ReportekEngine object in Data.fs
    this should be run with skipMigrationCheck=True since we can fairly assume
    that there is no migration tracking object yet.
    """
    eng = getattr(app, ENGINE_ID)
    if not hasattr(eng, MIGRATION_ID):
        setattr(eng, MIGRATION_ID, PersistentMapping())
    transaction.commit()
    return True
