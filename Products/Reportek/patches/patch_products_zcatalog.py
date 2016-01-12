""" Products.ZCatalog patches
"""


def patched_manage_beforeDelete(self, item, container):
    """ Because for zope3 based events, dispathObjectWillBeMoved function event
        recursively iterates over all children of the container object and it
        will run the event subscriber for each child object. Therefore, we need
        to skip iterating over all children
    """
    self.unindex_object()
