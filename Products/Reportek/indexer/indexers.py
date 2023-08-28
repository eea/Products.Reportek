from Products.Reportek.indexer import indexer
from zope.interface import Interface
from Products.Reportek.RepUtils import _mergedLocalRoles
from AccessControl.ImplPython import rolesForPermissionOn
from Products.Reportek.interfaces import (ICollection, IDocument, IEnvelope,
                                          IFeedback, IReportekContent,
                                          IWorkitem)


@indexer(IReportekContent)
def dummy_released(obj):
    """ dummy to prevent indexing child objects
    """
    APPLIES = [IWorkitem, ICollection, IDocument, IFeedback]
    for i in APPLIES:
        if i.providedBy(obj):
            raise AttributeError("This field should not indexed here!")


@indexer(IEnvelope)
def envelope_released(obj):
    """
    :return: value of released
    """
    return obj.released


@indexer(IReportekContent)
def dummy_activity_id(obj):
    """ dummy to prevent indexing child objects
    """
    APPLIES = [ICollection, IDocument, IEnvelope]
    for i in APPLIES:
        if i.providedBy(obj):
            raise AttributeError("This field should not indexed here!")


# We need 2 distinct indexers here, because we can't chain the decorator and
# we get conflicting configuration if we register it for IReportekContent
@indexer(IFeedback)
def fb_activity_id(obj):
    """ return value of activity_id
    """
    return obj.activity_id


@indexer(IWorkitem)
def wk_activity_id(obj):
    """ return value of activity_id
    """
    return obj.activity_id


@indexer(IWorkitem)
def wk_process_path(obj):
    """ return value of process_path needed for pull/push role edit
    """
    return obj.process_path


@indexer(IEnvelope)
def env_restricted(obj):
    """Return True if child of restricted collection"""
    return obj.restricted


@indexer(IDocument)
def doc_reportingdate(obj):
    """Return reportingdate of the envelope"""
    return obj.reportingdate


@indexer(IDocument)
def doc_released(obj):
    """Return released status of the envelope"""
    return obj.released


@indexer(Interface)
def allowedRolesAndUsers(obj):
    """Return a list of roles and users with View permission.
    Used to filter out items you're not allowed to see.
    """

    # 'Access contents information' is the correct permission for
    # accessing and displaying metadata of an item.
    # 'View' should be reserved for accessing the item itself.
    allowed = set(rolesForPermissionOn('View', obj))

    # shortcut roles and only index the most basic system role if the object
    # is viewable by either of those
    if 'Anonymous' in allowed:
        return ['Anonymous']
    elif 'Authenticated' in allowed:
        return ['Authenticated']
    localroles = {}
    try:
        acl_users = obj.unrestrictedTraverse('acl_users', None)
        if acl_users is not None:
            localroles = acl_users._getAllLocalRoles(obj)
    except AttributeError:
        localroles = _mergedLocalRoles(obj)
    for user, roles in localroles.items():
        if allowed.intersection(roles):
            allowed.update(['user:' + user])
    if 'Owner' in allowed:
        allowed.remove('Owner')
    return list(allowed)
