"""Script utilities"""

import os
import sys

HOST = os.environ.get("DEPLOYMENT_HOST", "localhost")


def get_script_args(script_name, argv=None):
    """Return arguments passed to a Reportek console script.

    The legacy Zope 2 ``bin/instance run`` command exposed arguments as::

        instance run bin/script --option value

    so older scripts parsed ``sys.argv[3:]``. Zope 4/5 ``zconsole run`` adds
    the config path before the script path::

        zconsole run etc/zope.conf bin/script --option value

    Locate the script name in ``argv`` instead of assuming a fixed offset, so
    scripts keep working with direct console-script execution, legacy
    ``instance run`` and new ``zconsole run`` invocations.
    """
    if argv is None:
        argv = sys.argv

    expected = os.path.splitext(os.path.basename(script_name))[0]
    for idx, value in enumerate(argv):
        current = os.path.splitext(os.path.basename(value))[0]
        if current == expected:
            return argv[idx + 1 :]

    # Fall back to normal console-script semantics if the script path is not
    # present in argv, for example in unit tests or custom wrappers.
    return argv[1:]


def get_zope_site():
    import Zope2

    app = Zope2.app()
    from Testing.makerequest import makerequest

    app = makerequest(app, environ={"SERVER_NAME": HOST})
    app.REQUEST["PARENTS"] = [app]
    from zope.globalrequest import setRequest

    setRequest(app.REQUEST)

    from AccessControl.SpecialUsers import system as user
    from AccessControl.SecurityManagement import newSecurityManager

    newSecurityManager(None, user)
    # We need the AUTHENTICATED_USER in the REQUEST for
    # manage_as_owner decorator
    app.REQUEST["AUTHENTICATED_USER"] = user

    return app
