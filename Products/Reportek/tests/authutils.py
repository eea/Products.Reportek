from AccessControl.SecurityManagement import newSecurityManager, noSecurityManager
from AccessControl.User import User, UnrestrictedUser, SpecialUser


def loginAnonymous():
    """ """
    noSecurityManager()
    anonymous_user = SpecialUser('Anonymous User', '', ('Anonymous',), [])
    newSecurityManager(None, anonymous_user)


def loginUnrestricted():
    """ """
    noSecurityManager()
    god = UnrestrictedUser('god', 'god', [], '')
    newSecurityManager(None, god)
    return god


def loginAs(username, roles):
    """ """
    noSecurityManager()
    user = User(username, username, roles, '')
    newSecurityManager(None, user)
    return user


def loginUser(user, zope_app=None):
    """ """
    newSecurityManager(None, user)
    if zope_app:
        zope_app.REQUEST.set('AUTHENTICATED_USER', user)


def logout():
    ''' simulates logout '''
    noSecurityManager()


def setupUser(folder, user_name, roles):
    '''Creates the user in the given folder (folder) acl_users.'''
    uf = getattr(folder, 'acl_users')
    uf._addUser(user_name, 'secret', 'secret', roles, ())
    user = uf.getUserById(user_name).__of__(uf)
    return user
