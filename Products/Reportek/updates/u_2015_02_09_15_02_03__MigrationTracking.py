# This places a Persistent Mapping in the Data.fs to keep track of the executed updates
# It also contains the boilerplate to use when naming and running scripts
# 1. Name your scripts starting with `date -u '+u_%Y_%m_%d_%H_%M_%S__'` followed by a meaningfull name
# 2. Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u_2015_02_09_15_02_03__MigrationTracking; u_2015_02_09_15_02_03__MigrationTracking.update(app)

from Products.Reportek.updates import MigrationBase
from Products.Reportek.constants import ENGINE_ID, MIGRATION_ID

import transaction
from ZODB.PersistentMapping import PersistentMapping

VERSION = 1

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
