# It also contains the boilerplate to use when naming and running scripts
# 1. Name your scripts starting with `date -u '+u_%Y_%m_%d_%H_%M_%S__'` followed by a meaningfull name
# 2. Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u_2015_02_09_15_02_03__<meaningfulName>; u_2015_02_09_15_02_03__<meaningfulName>.update(app)


import time
#from functools import wraps
import inspect

import transaction

from Products.Reportek.constants import ENGINE_ID, MIGRATION_ID

def checkMigration(module_name):
    """Decorate a migration function to track migrations inside Data.fs
    `module_name` should be the module level value of __name__ from which only the last part
    is kept. but can be any name, just keep in mind that only the last part after '.' will be kept.
    """
    def checkMigrationDec(migrationFunc):
        #@wraps(migrationFunc)
        def wrapper(app, *args, **kwargs):
            """
            `version` should be passed to the function being decorated.
            It is the current version of the update scipt (integer); each script should define a VERSION
            variable that you can pass to it. If you give a false value
            to version then version check&update will be skipped.
            `skipMigrationCheck` is an argument that should be given to the function being decorated.
            If `skipMigrationCheck` has a true value then the checking and updating of migration mapping
            is skipped alltogether.
            Please use those argumets named only, or extend the code below to support them from args too!
            """
            aSpec = inspect.getargspec(migrationFunc)
            defaultArgs = {}
            # skip the initial, non-default ones
            for i, arg in enumerate(aSpec.args[len(aSpec.args)-len(aSpec.defaults):]):
                defaultArgs[arg] = aSpec[3][i]
            if 'version' not in kwargs:
                kwargs['version'] = defaultArgs.get('version')
            if 'skipMigrationCheck' not in kwargs:
                kwargs['skipMigrationCheck'] = defaultArgs.get('skipMigrationCheck', False)
            version = kwargs['version']
            skipMigrationCheck = kwargs['skipMigrationCheck']
            thisUpdateName = module_name.split('.')[-1]

            def _trackMigration():
                thisUpdate = migs.get(thisUpdateName)
                if not thisUpdate:
                    thisUpdate = MigrationEntry(thisUpdateName, version)
                    migs[thisUpdateName] = thisUpdate
                elif version:
                    if thisUpdate.version >= version:
                        return None
                return thisUpdate

            mig = None
            if not skipMigrationCheck:
                migs = getattr(getattr(app, ENGINE_ID), MIGRATION_ID)
                mig = _trackMigration()
                if not mig:
                    return False

            # the real update (it will commit)
            ret = migrationFunc(app, *args, **kwargs)

            if mig:
                if version:
                    mig.version = version
                mig.current_ts = time.time()
                transaction.commit()
            return ret
        wrapper.__module__ = migrationFunc.__module__
        wrapper.__name__ = migrationFunc.__name__
        wrapper.__doc__ = migrationFunc.__doc__ + wrapper.__doc__
        return wrapper
    return checkMigrationDec


class MigrationEntry(object):
    def __init__(self, name, version):
        self.name = name
        self.version = version
        self.first_ts = time.time()
        self.current_ts = self.first_ts
