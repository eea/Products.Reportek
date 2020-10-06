""" Products.ZCatalog patches
"""
from Products.Reportek.indexer.interfaces import IIndexableObject
from Products.Reportek.indexer.wrapper import IndexableObjectWrapper
from Products.ZCatalog.ZCatalog import ZCatalog
from zope.component import queryMultiAdapter


def patched_manage_beforeDelete(self, item, container):
    """ Because for zope3 based events, dispathObjectWillBeMoved function event
        recursively iterates over all children of the container object and it
        will run the event subscriber for each child object. Therefore, we need
        to skip iterating over all children
    """
    self.unindex_object()


def patched_catalog_object(self, obj, uid=None, idxs=None, update_metadata=1,
                           pghandler=None):
    # Wraps the object with workflow and accessibility
    # information just before cataloging.
    if IIndexableObject.providedBy(obj):
        w = obj
    else:
        w = queryMultiAdapter((obj, self), IIndexableObject)
        if w is None:
            # BBB
            w = IndexableObjectWrapper(obj, self)
    ZCatalog._old_catalog_object(self, w, uid, idxs, update_metadata,
                                 pghandler)
