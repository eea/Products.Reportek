""" Script utilities
"""
import os
HOST = os.environ.get('DEPLOYMENT_HOST', 'localhost')


def get_zope_site():
    import Zope2
    app = Zope2.app()
    from Testing.ZopeTestCase import utils
    utils._Z2HOST = HOST
    app = utils.makerequest(app)
    app.REQUEST['PARENTS'] = [app]
    from zope.globalrequest import setRequest
    setRequest(app.REQUEST)

    from AccessControl.SpecialUsers import system as user
    from AccessControl.SecurityManagement import newSecurityManager
    newSecurityManager(None, user)
    # We need the AUTHENTICATED_USER in the REQUEST for
    # manage_as_owner decorator
    app.REQUEST['AUTHENTICATED_USER'] = user

    return app
