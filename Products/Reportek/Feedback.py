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
# The Original Code is Reportek version 1.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Miruna Badescu, Finsiel Romania

"""
Feedback module
===============

Feedback objects are sub-objects of Report Envelopes.

"""

# $Id$

__version__='$Rev$'[6:-2]
import os
from os.path import join, isfile

# Zope imports
from Products.ZCatalog.CatalogAwareness import CatalogAware
from AccessControl.Permissions import view_management_screens
from OFS.SimpleItem import SimpleItem
from OFS.ObjectManager import ObjectManager
from blob import add_OfsBlobFile
from OFS.PropertyManager import PropertyManager
from Globals import DTMLFile, MessageDialog, InitializeClass
from AccessControl import getSecurityManager, ClassSecurityInfo
#from webdav.WriteLockInterface import WriteLockInterface
from DateTime import DateTime

# Product specific imports
from Comment import CommentsManager
import RepUtils

manage_addFeedbackForm = DTMLFile('dtml/feedbackAdd',globals())

def manage_addFeedback(self, id ='', title='', feedbacktext='', file='', activity_id='', automatic=0,
        content_type='text/plain', document_id=None, script_url=None, restricted='', REQUEST=None):
    """Adds feedback as a file to a folder."""

    # get the release date of the envelope
    releasedate = self.reportingdate
    # generate id from the release date
    # Normally, there can only be one feedback for a release
    if not id: id = 'feedback' + str(int(releasedate))
    ob = ReportFeedback(id, releasedate, title, feedbacktext, activity_id, automatic, content_type, document_id)
    if file:
        filename = RepUtils.getFilename(file.filename)
        add_OfsBlobFile(ob, filename, file)
    self._setObject(id, ob)
    obj = self._getOb(id)

    # Restricted from public
    if restricted:
        obj.manage_restrictFeedback()
    else:
        if document_id not in [None, 'xml']:
            doc = self._getOb(document_id, None)
            if doc is not None:
                if not doc.acquiredRolesAreUsedBy('View'):
                    obj.manage_restrictFeedback()

    # Send notification to UNS
    engine = self.getEngine()
    envelope = self.getMySelf()

    envelope._invalidate_zip_cache()

    #if REQUEST is None: REQUEST = self.REQUEST

    if engine.UNS_server and not ob.automatic:
        engine.sendNotificationToUNS(envelope, 'Feedback posted', 'Feedback was posted in the envelope %s (%s)' % (envelope.title_or_id(), obj.absolute_url()), self.REQUEST.AUTHENTICATED_USER.getUserName())

    if REQUEST is not None:
        return self.messageDialog(message="The Feedback %s was successfully created!" % id)

class ReportFeedback(CatalogAware, ObjectManager, SimpleItem, PropertyManager, CommentsManager):
    """
        Feedback objects are created in envelopes either manually (by Clients)
        or automatically (by activities such as the Automatic QA or Confirmation Receipt).

        They can refer to the entire delivery, or to a single Document inside it.
        Feedback items can contain files and have comments posted on them by people
        discussing the content of the feedback.
    """

    meta_type='Report Feedback'
    icon = 'misc_/Reportek/feedback_gif'

    # what management options are there?
    manage_options = (
        (ObjectManager.manage_options[0],)+
        PropertyManager.manage_options+
        ({'label':'View',  'action':'index_html'}, )+
        SimpleItem.manage_options
    )

    _properties = ({'id':'title', 'type':'string', 'mode':'w'},
            {'id':'feedbacktext', 'type':'text', 'mode':'w'},
            {'id':'releasedate', 'type':'string', 'mode':'r'},
            {'id':'automatic', 'type':'boolean', 'mode':'r'},
            {'id':'content_type', 'type':'string', 'mode':'w'},
            {'id':'document_id', 'type':'string', 'mode':'w'}
    )

    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()

    def __init__(self, id, releasedate, title='', feedbacktext='', activity_id='', automatic=0,
            content_type='text/plain', document_id=None):
        """ Initialize a new Feedback instance
        """
        self.id = id
        self.releasedate = releasedate
        self.title = title
        self.automatic = automatic
        self.feedbacktext = feedbacktext
        self.content_type = content_type
        self.activity_id = activity_id
        self.document_id = document_id
        self.postingdate = DateTime()

    def __setstate__(self,state):
        ReportFeedback.inheritedAttribute('__setstate__')(self, state)
        if not hasattr(self,'postingdate'):
            self.postingdate = self.bobobase_modification_time()

    def update_item(self, postingdate=None):
        """ If the parameter is provided, updates the postingdate to it
            If not, checks if the property exists and sets it to bobobase_modification_time
        """
        if postingdate:
            self.postingdate = postingdate
            self._p_changed = 1
        elif not hasattr(self,'postingdate'):
            self.postingdate = self.bobobase_modification_time()
            self._p_changed = 1

    def all_meta_types( self, interfaces=None ):
        """ Called by Zope to determine what kind of object the envelope can contain
        """
        y = [
            {'name': 'File',
             'action': 'manage_addProduct/OFSP/fileAdd',
             'permission': 'Add Envelopes'},
            {'name': 'File (Blob)',
             'action': 'manage_addProduct/Reportek/blob_add',
             'permission': 'Add Envelopes'},
        ]
        return y

    security.declareProtected('Change Feedback', 'manage_editFeedback')
    def manage_editFeedback(self, title='', feedbacktext='', content_type='', document_id='', applyRestriction='', restricted='', REQUEST=None):
        """ Edits the properties """
        self.title = title
        self.feedbacktext = feedbacktext
        if content_type:
            self.content_type = content_type
        if document_id != 'None':
            self.document_id = document_id
        if applyRestriction:
            if restricted:
                self.manage_restrictFeedback()
            else:
                self.manage_unrestrictFeedback()
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect('index_html')

    security.declareProtected('Change Feedback', 'manage_uploadFeedback')
    def manage_uploadFeedback(self, file='', REQUEST=None, filename=None):
        """ Upload an attachment to a feedback.
            FIXME: Misnamed method name
        """
        if filename is None:
            filename = RepUtils.getFilename(file.filename)
        add_OfsBlobFile(self, filename, file)
        if REQUEST:
            REQUEST.RESPONSE.redirect('%s/manage_editFeedbackForm' % self.absolute_url())

    security.declareProtected('Change Feedback', 'manage_uploadAttFeedback')
    def manage_uploadAttFeedback(self, file_id='', file='', REQUEST=None):
        """ Replace the content of an existing attachment
        """
        file_ob = self._getOb(file_id)
        with file_ob.data_file.open('wb') as f:
            for chunk in RepUtils.iter_file_data(file):
                f.write(chunk)
        if REQUEST:
            REQUEST.RESPONSE.redirect('%s/manage_editFeedbackForm' % self.absolute_url())

    security.declareProtected('Change Feedback', 'manage_deleteAttFeedback')
    def manage_deleteAttFeedback(self, file_id='', REQUEST=None):
        """ Delete an attachment
            FIXME: Why is the 'go' parameter not an method argument?   !#&%!!
        """
        p_action = REQUEST.get('go', '')
        if p_action == 'Delete': self.manage_delObjects(file_id)
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect('%s/manage_editFeedbackForm' % self.absolute_url())

    def compileFeedbacktext(self, REQUEST):
        """ If the feedbacktext has another content type than plain text or HTML,
            it will be displayed separately on this page
        """
        response = REQUEST.RESPONSE
        response.setHeader('Content-type', self.content_type)
        # fixme: loop chunk of data to display, not all at once
        response.write(self.feedbacktext)

    def getActivityDetails(self, p_attribute):
        """ returns the activity's description """
        l_process = self.unrestrictedTraverse(self.getParentNode().process_path)
        return getattr(getattr(l_process, self.activity_id), p_attribute)

    security.declareProtected('Change Envelopes', 'manage_restrictFeedback')
    def manage_restrictFeedback(self, REQUEST=None):
        """ Restrict access to this feedback
        """
        self.manage_restrict(ids=[self.id])
        if REQUEST:
            return self.messageDialog(
                            message='File restricted to public.',
                            action=REQUEST['HTTP_REFERER'])

    security.declareProtected('Change Envelopes', 'manage_unrestrictFeedback')
    def manage_unrestrictFeedback(self, REQUEST=None):
        """ Remove access restriction for this feedback
        """
        self.manage_unrestrict(ids=[self.id])
        if REQUEST:
            return self.messageDialog(
                            message='Document released to public.',
                            action=REQUEST['HTTP_REFERER'])

    security.declareProtected('View', 'index_html')
    index_html = DTMLFile('dtml/feedbackIndex', globals())

    security.declareProtected('Change Feedback', 'manage_editFeedbackForm')
    manage_editFeedbackForm = DTMLFile('dtml/feedbackEdit', globals())

    security.declareProtected('Change Feedback', 'manage_uploadAttFeedbackForm')
    manage_uploadAttFeedbackForm = DTMLFile('dtml/feedbackUploadAtt', globals())

    security.declareProtected('Change Feedback', 'manage_deleteAttFeedbackForm')
    manage_deleteAttFeedbackForm = DTMLFile('dtml/feedbackDeleteAtt', globals())

InitializeClass(ReportFeedback)
