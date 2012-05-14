# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is Reportek version 2.0.1.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Soren Roug, EEA

__doc__ = """
      Hyperlink product module.
      The Hyperlink is kept as an object along with the Documents 
      .

      $Id$
"""

from Products.ZCatalog.CatalogAwareness import CatalogAware
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from Globals import DTMLFile, MessageDialog, InitializeClass
from AccessControl import getSecurityManager, ClassSecurityInfo
from webdav.WriteLockInterface import WriteLockInterface
from DateTime import DateTime
from App.ImageFile import ImageFile
import RepUtils
from time import time
import string

manage_addHyperlinkForm = DTMLFile('dtml/hyperlinkAdd',globals())

def manage_addHyperlink(self, id ='', title='', hyperlinkurl='', REQUEST=None):
    """Adds hyperlink as a file to a folder."""

    # generate id from the release date
    # Normally, there can only be one hyperlink for a release
    if not id:
        id = hyperlinkurl
    if id:
        while len(id) > 0 and id[-1] == '/': id = id[:-1]
        id = id[max(string.rfind(id,'/'),
                  string.rfind(id,'\\'),
                  string.rfind(id,':')
                 )+1:]
        id = id.strip()
        id = RepUtils.cleanup_id(id)

    ob = ReportHyperlink(id, title, hyperlinkurl)
    self._setObject(id, ob)

    if REQUEST is not None:
        return self.messageDialog(
                        message="The Hyperlink %s was successfully created!" % self.id)

class ReportHyperlink(CatalogAware, 
        SimpleItem, 
        PropertyManager
        ):
    """A Hyperlink allows indexing and conversions."""

    __implements__ = (WriteLockInterface,)
    meta_type='Report Hyperlink'
    icon = 'misc_/Reportek/hyperlink_gif'

    # what management options are there?
    manage_options = (
        PropertyManager.manage_options+
        ({'label':'View',  'action':'index_html'}, )+
        SimpleItem.manage_options
    )

    _properties = ({'id':'title', 'type':'string', 'mode':'w'},
            {'id':'hyperlinkurl', 'type':'string', 'mode':'w'},
    )

    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()

    ################################
    # Init method                  #
    ################################

    def __init__(self, id, title='', hyperlinkurl=''):
        """ Initialize a new Hyperlink instance
        """
        self.id = id
        self.title = title
        self.hyperlinkurl = hyperlinkurl
        self._upload_time = time()

    # Compatibility with Document
    security.declarePublic('icon_gif')
    icon_gif = ImageFile("www/hyperlink.gif", globals())
    #icon_gif = ImageFile("www/hyperlink_big.gif", globals())

    security.declarePublic('upload_time')
    def upload_time(self):
        """ Return the upload time
        """
        return DateTime(self._upload_time)

    def size(self):
        return ''

    security.declareProtected('Change Envelopes', 'manage_editHyperlink')
    def manage_editHyperlink(self, title='', hyperlinkurl='',
           applyRestriction='', restricted='', REQUEST=None):
        """ Edits the properties """
        self.title = title
        self.hyperlinkurl = hyperlinkurl
        if applyRestriction:
            if restricted:
                self.manage_restrictDocument()
            else:
                self.manage_unrestrictDocument()
        if REQUEST is not None:
            return self.messageDialog(
                            message="The properties of %s have been changed!" % self.id,
                            action=REQUEST['HTTP_REFERER'])

    security.declareProtected('View', 'index_html')
    index_html = DTMLFile('dtml/hyperlinkIndex', globals())

    security.declareProtected('Change Envelopes', 'manage_editHyperlinkForm')
    manage_editHyperlinkForm = DTMLFile('dtml/hyperlinkEdit', globals())

    security.declareProtected('Change Envelopes', 'manage_restrictDocument')
    def manage_restrictDocument(self, REQUEST=None):
        """ Restrict access to this file
        """
        self.manage_restrict(ids=[self.id])
        if REQUEST:
            return self.messageDialog(
                            message="File restricted to public.",
                            action=REQUEST['HTTP_REFERER'])

    security.declareProtected('Change Envelopes', 'manage_unrestrictDocument')
    def manage_unrestrictDocument(self, REQUEST=None):
        """ Remove access restriction for this file
        """
        self.manage_unrestrict(ids=[self.id])
        if REQUEST:
            return self.messageDialog(
                            message="Document released to public.",
                            action=REQUEST['HTTP_REFERER'])

InitializeClass(ReportHyperlink)
