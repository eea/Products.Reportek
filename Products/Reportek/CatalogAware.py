##############################################################################
#
# Copyright (c) 2001 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Base class for catalog aware content items.
"""

import logging

from AccessControl.class_init import InitializeClass
from AccessControl.SecurityInfo import ClassSecurityInfo
from Acquisition import aq_base
from ExtensionClass import Base
from zope.component import queryUtility
from zope.interface import implementer

from Products.Reportek.interfaces import (IReportekCatalog,
                                          IReportekCatalogAware)


logger = logging.getLogger('CMFCore.CMFCatalogAware')


@implementer(IReportekCatalogAware)
class CatalogAware(Base):

    """Mix-in for notifying the catalog tool.
    """

    security = ClassSecurityInfo()

    # The following method can be overridden using inheritance so that it's
    # possible to specify another catalog tool for a given content type
    def _getCatalogTool(self):
        return queryUtility(IReportekCatalog)

    def indexObject(self):
        """ Index the object in the portal catalog.
        """
        catalog = self._getCatalogTool()
        if catalog is not None:
            catalog.indexObject(self)

    def unindexObject(self):
        """ Unindex the object from the portal catalog.
        """
        catalog = self._getCatalogTool()
        if catalog is not None:
            catalog.unindexObject(self)

    def reindexObject(self, idxs=[], update_metadata=1, uid=None):
        """ Reindex the object in the portal catalog.
        """
        if idxs == []:
            # Update the modification date.
            if hasattr(aq_base(self), 'notifyModified'):
                self.notifyModified()
        catalog = self._getCatalogTool()
        if catalog is not None:
            catalog.reindexObject(
                self,
                idxs=idxs,
                update_metadata=update_metadata,
                uid=uid)
    _cmf_security_indexes = ('allowedRolesAndUsers',
                             'allowedAdminRolesAndUsers')

    def reindexObjectSecurity(self, skip_self=False):
        """ Reindex security-related indexes on the object.
        """
        catalog = self._getCatalogTool()
        if catalog is None:
            return
        path = '/'.join(self.getPhysicalPath())

        # XXX if _getCatalogTool() is overriden we will have to change
        # this method for the sub-objects.
        for brain in catalog.unrestrictedSearchResults(path=path):
            brain_path = brain.getPath()
            if brain_path == path and skip_self:
                continue
            # Get the object
            try:
                ob = brain._unrestrictedGetObject()
            except (AttributeError, KeyError):
                # don't fail on catalog inconsistency
                continue
            if ob is None:
                # BBB: Ignore old references to deleted objects.
                # Can happen only when using
                # catalog-getObject-raises off in Zope 2.8
                logger.warning('reindexObjectSecurity: Cannot get %s from '
                               'catalog', brain_path)
                continue
            s = getattr(ob, '_p_changed', 0)
            ob.reindexObject(idxs=self._cmf_security_indexes)
            if s is None:
                ob._p_deactivate()


InitializeClass(CatalogAware)
