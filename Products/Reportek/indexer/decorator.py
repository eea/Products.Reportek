# -*- coding: utf-8 -*-
"""This module defines a decorator that
"""

from Products.Reportek.indexer.delegate import DelegatingIndexerFactory
from Products.ZCatalog.interfaces import IZCatalog
from zope.component import adapter


class indexer(adapter):
    """ indexer taken from plone.indexer
    """

    def __init__(self, *interfaces):
        if len(interfaces) == 1:
            interfaces += (IZCatalog, )
        elif len(interfaces) > 2:
            raise ValueError(
                u'The @indexer decorator takes at most two interfaces as '
                u'arguments.',
            )
        adapter.__init__(self, *interfaces)

    def __call__(self, callable):
        factory = DelegatingIndexerFactory(callable)
        return adapter.__call__(self, factory)
