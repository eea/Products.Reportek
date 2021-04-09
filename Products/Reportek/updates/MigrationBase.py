# -*- coding: utf-8 -*-
# It also contains the boilerplate to use when naming and running scripts
# 1. Name your scripts starting with `date -u '+u%Y%m%d_'` followed by a meaningfull name
# 2. Run them from within debug mode like so:
#  >>> from Products.Reportek.updates import u20150209_<meaningfulName>; u20150209_<meaningfulName>.update(app)

# One only needs to provide module level VERSION integer variable
# and to decorate the update function with the module level __name__
#
# No boilerplate added to the definition of update function
# one can use
# VERSION = 2
# @MigrationBase.checkMigration(__name__)
# def upd(app):
#     pass
# and it works
#
# Additionally one can tweak the behaviour at definition time
# def upd(app, version=100, skipMigrationCheck=True):
# and at call time:
# >>> upd(app, other_positional, version=101)
#
# or at call time only
# def upd(app, other_positional, other_named=dflt): # no version argument mentioned
# >>> upd(app, other_positional, version=10)
# without worring that undeclared `version` argument reaches upd
#
# Of course all these override defaults from VERSION, etc
#
# Author: Daniel Mihai Bărăgan, daniel.baragan@eaudeweb.ro
# Contributor(s):
#

import importlib
import inspect
import time
from datetime import datetime

import pytz
import transaction
from Products.Reportek.constants import ENGINE_ID, MIGRATION_ID


def checkMigration(module_name):
    """Decorate a migration function to track migrations inside Data.fs
    `module_name` must be the module level value of __name__ from which only the last part
    is kept. But we need the whole value for import reasons.
    """
    def checkMigrationDec(migrationFunc):
        def wrapper(app, *args, **kwargs):
            """
            `version` could be passed to the function being decorated.
            It is the current version of the update scipt (integer);
            each script should define a VERSION variable that is automatically
            read by the wrapper. But you can override it by passing version=<int>
            among the arguments.
            If you give a false value to version then version check&update
            will be skipped.

            `skipMigrationCheck` is an argument that could be given to the function
            being decorated.
            If `skipMigrationCheck` has a true value then the checking and updating
            of migration mapping is skipped alltogether.
            The default is False meaning that migration table is checked and updated.

            Please use these argumets named only, or extend the code below to support them from args too!
            """
            thisUpdateName = module_name.split('.')[-1]
            try:
                version = importlib.import_module(module_name).VERSION
                version = int(version)
            except:
                version = None
            # The default values don't reach this outer function
            # they are applied only when this calls migrationFunc(**kwargs)
            # if they are missing from kwargs.
            # but we need some defaults here, thus we inspect the spec of the inner function
            aSpec = inspect.getargspec(migrationFunc)
            defaultArgs = {}
            # skip the initial, non-default ones
            for i, arg in enumerate(aSpec.args[len(aSpec.args)-len(aSpec.defaults):]):
                defaultArgs[arg] = aSpec[3][i]
            # if we have a default in the inner function for skip
            # and it is not overridden by the actual arguments in the call
            # take that as skip value
            # else take whatever is in this call arguments or the default.
            # either way, don't mangle inner function arguments and let it apply
            # its 'natural' mechanism for determining argument values
            # (besides, inner function should not use skip argument anyway, it is for wrapper only)
            if 'skipMigrationCheck' not in kwargs and 'skipMigrationCheck' in defaultArgs:
                skipMigrationCheck = defaultArgs['skipMigrationCheck']
            else:
                skipMigrationCheck = kwargs.pop('skipMigrationCheck', False)
            # check for version override from update function default arguments
            if 'version' not in kwargs and 'version' in defaultArgs:
                version = defaultArgs['version']
            else:
                # or from update function given named arguments
                # else keep what calling module's VERSION var says
                version = kwargs.pop('version', version)

            def _trackMigration():
                thisUpdate = migs.get(thisUpdateName)
                if not thisUpdate:
                    thisUpdate = MigrationEntry(thisUpdateName, version)
                    migs[thisUpdateName] = thisUpdate
                elif version:
                    if thisUpdate.version >= version:
                        return None
                return thisUpdate

            # the real update (it will also commit)
            ret = migrationFunc(app, *args, **kwargs)
            if ret:
                mig = None
                if not skipMigrationCheck:
                    migs = getattr(getattr(app, ENGINE_ID), MIGRATION_ID)
                    mig = _trackMigration()
                    if not mig:
                        return False

                if mig:
                    if version:
                        mig.version = version
                    mig.current_ts = time.time()
                    migs[thisUpdateName] = mig
                    transaction.commit()

            return ret
        wrapper.__module__ = migrationFunc.__module__
        wrapper.__name__ = migrationFunc.__name__
        if migrationFunc.__doc__:
            wrapper.__doc__ = migrationFunc.__doc__ + wrapper.__doc__
        return wrapper
    return checkMigrationDec


class MigrationEntry(object):
    DATETIME_FMT = "%Y-%m-%d %H:%M:%S %Z"

    def __init__(self, name, version, logs=None):
        self.name = name
        self.version = version
        self.first_ts = time.time()
        self.current_ts = self.first_ts
        if not logs:
            logs = []
        self.logs = logs

    @classmethod
    def toDate(cls, ts):
        return datetime.fromtimestamp(ts, pytz.utc).strftime(cls.DATETIME_FMT)

    def __repr__(self):
        return "<%s, name: %s, version: %d, created: %s, updated: %s>" % (
            self.__class__.__name__, self.name, self.version,
            self.toDate(self.first_ts), self.toDate(self.current_ts),
        )
