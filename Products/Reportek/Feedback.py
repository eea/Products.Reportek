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
# Miruna Badescu, Eau de Web
# Olimpiu Rob, Eau de Web

"""
Feedback module
===============

Feedback objects are sub-objects of Report Envelopes.

"""

# $Id$

from zope.lifecycleevent import ObjectModifiedEvent
from zope.interface import implements
from zope.event import notify
from Products.Reportek.CatalogAware import CatalogAware
from Products.Reportek.RepUtils import DFlowCatalogAware, parse_uri
from Products.Reportek.interfaces import IFeedback
from Products.Reportek import constants
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from OFS.ObjectManager import ObjectManager
from Globals import InitializeClass
from DateTime import DateTime
from Comment import CommentsManager
from blob import add_OfsBlobFile
from AccessControl import ClassSecurityInfo
import plone.protect.interfaces
from zope.interface import alsoProvides
import RepUtils
import StringIO
import logging

__version__ = '$Rev$'[6:-2]
logger = logging.getLogger("Reportek")

manage_addFeedbackForm = PageTemplateFile('zpt/feedback/add', globals())


def manage_addFeedback(self, id='', title='', feedbacktext='', file=None,
                       activity_id='', automatic=0, content_type='text/plain',
                       document_id=None, script_url=None, restricted='',
                       REQUEST=None):
    """Adds feedback as a file to a folder."""

    if 'IDisableCSRFProtection' in dir(plone.protect.interfaces):
        if REQUEST:
            alsoProvides(REQUEST,
                         plone.protect.interfaces.IDisableCSRFProtection)
    # get the release date of the envelope
    releasedate = self.reportingdate
    # generate id from the release date
    # Normally, there can only be one feedback for a release
    if not id:
        id = 'feedback' + str(int(releasedate))
    tmp = StringIO.StringIO(feedbacktext)
    convs = getattr(self.getPhysicalRoot(), constants.CONVERTERS_ID, None)
    # if Local Conversion Service is down
    # the next line of code will raise an exception
    # because we don't want to save unsecure html
    sanitizer = convs['safe_html']
    feedbacktext = sanitizer.convert(tmp, sanitizer.id).text

    ob = ReportFeedback(
        id, releasedate, title, feedbacktext, activity_id,
        automatic, content_type, document_id)
    if file:
        if type(file) != list:  # one file object
            file = [file]

        for f in file:
            filename = RepUtils.getFilename(f.filename)
            add_OfsBlobFile(ob, filename, f)

    self._setObject(id, ob)
    obj = self._getOb(id)

    r_enabled = (
        hasattr(self, 'is_globally_restricted')
        and self.is_globally_restricted()) or (
        hasattr(self, 'is_workflow_restricted')
        and self.is_workflow_restricted())
    if restricted or r_enabled:
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

    if engine.UNS_server and not ob.automatic:
        engine.sendNotificationToUNS(
            envelope, 'Feedback posted',
            'Feedback was posted in the envelope %s (%s)' % (
                envelope.title_or_id(),
                obj.absolute_url()),
            self.REQUEST.AUTHENTICATED_USER.getUserName())

    if REQUEST is not None:
        if 'file_upload' in REQUEST.form:
            REQUEST.RESPONSE.redirect(
                '%s/manage_editFeedbackForm' % obj.absolute_url())
        else:
            return self.messageDialog(
                message="The Feedback %s was successfully created!" % id,
                action=self.absolute_url())


def manage_addManualQAFeedback(self, id='', title='', feedbacktext='',
                               file=None, activity_id='', automatic=0,
                               content_type='text/plain', document_id=None,
                               script_url=None, restricted='', message='',
                               feedback_status='', REQUEST=None):
    """Adds a manual QA feedback as a file to a folder. To be used by Managers.
    """
    self.manage_addFeedback(id=id, title=title, feedbacktext=feedbacktext,
                            file=file, activity_id=activity_id,
                            automatic=automatic, content_type=content_type,
                            document_id=document_id, script_url=script_url,
                            restricted=restricted, REQUEST=REQUEST)
    if not id:
        id = 'feedback' + str(int(self.reportingdate))

    obj = self._getOb(id)
    obj.feedback_status = feedback_status
    obj.message = message
    obj.reindexObject()
    if REQUEST is not None:
        return self.messageDialog(
            message="The Feedback %s was successfully created!" % id,
            action=self.absolute_url())


class ReportFeedback(CatalogAware, ObjectManager, SimpleItem, PropertyManager,
                     CommentsManager, DFlowCatalogAware):
    """
        Feedback objects are created in envelopes either manually (by Clients)
        or automatically (by activities such as the Automatic QA or
        Confirmation Receipt).

        They can refer to the entire delivery, or to a single Document inside
        it.
        Feedback items can contain files and have comments posted on them by
        people discussing the content of the feedback.
    """

    meta_type = 'Report Feedback'
    icon = 'misc_/Reportek/feedback_gif'

    # what management options are there?
    manage_options = (
        (ObjectManager.manage_options[0],) +
        PropertyManager.manage_options +
        ({'label': 'View',  'action': 'index_html'}, ) +
        SimpleItem.manage_options
    )

    _properties = ({'id': 'title', 'type': 'string', 'mode': 'w'},
                   {'id': 'feedbacktext', 'type': 'text', 'mode': 'w'},
                   {'id': 'releasedate', 'type': 'string', 'mode': 'r'},
                   {'id': 'automatic', 'type': 'boolean', 'mode': 'r'},
                   {'id': 'content_type', 'type': 'string', 'mode': 'w'},
                   {'id': 'document_id', 'type': 'string', 'mode': 'w'},
                   )

    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    implements(IFeedback)
    security = ClassSecurityInfo()

    def __init__(self, id, releasedate, title='', feedbacktext='',
                 activity_id='', automatic=0, content_type='text/plain',
                 document_id=None, message='', feedback_status=''):
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
        self.message = message
        self.feedback_status = feedback_status

    def update_item(self, postingdate=None):
        """ If the parameter is provided, updates the postingdate to it
            If not, checks if the property exists and sets it to
            bobobase_modification_time
        """
        if postingdate:
            self.postingdate = postingdate
            self._p_changed = 1
        elif not hasattr(self, 'postingdate'):
            self.postingdate = self.bobobase_modification_time()
            self._p_changed = 1

    def all_meta_types(self, interfaces=None):
        """ Called by Zope to determine what kind of object the envelope can
            contain
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

    def manage_editFeedback(self, title='', feedbacktext='', content_type='',
                            document_id=None, applyRestriction='',
                            restricted='', feedback_status='', message='',
                            REQUEST=None):
        """ Edits the properties """
        if title:
            self.title = title
        if feedbacktext:
            tmp = StringIO.StringIO(feedbacktext)
            convs = getattr(self.getPhysicalRoot(),
                            constants.CONVERTERS_ID, None)
            # if Local Conversion Service is down
            # the next line of code will raise an exception
            # because we don't want to save unsecure html
            sanitizer = convs['safe_html']
            self.feedbacktext = sanitizer.convert(tmp, sanitizer.id).text
        if content_type:
            self.content_type = content_type
        if document_id != 'None':
            self.document_id = document_id
        if feedback_status:
            self.feedback_status = feedback_status
        if message:
            self.message = message

        if applyRestriction:
            if restricted:
                self.manage_restrictFeedback()
            else:
                self.manage_unrestrictFeedback()
        notify(ObjectModifiedEvent(self))
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect('index_html')

    security.declareProtected('Change Feedback', 'manage_uploadFeedback')

    def manage_uploadFeedback(self, file='', REQUEST=None, filename=None):
        """ Upload an attachment to a feedback.
            FIXME: Misnamed method name
        """
        if 'IDisableCSRFProtection' in dir(plone.protect.interfaces):
            if REQUEST:
                alsoProvides(REQUEST,
                             plone.protect.interfaces.IDisableCSRFProtection)
        if filename is None:
            filename = RepUtils.getFilename(file.filename)
        engine = self.getEngine()
        engine.AVService.scan(file)
        add_OfsBlobFile(self, filename, file)
        if REQUEST:
            REQUEST.RESPONSE.redirect(
                '%s/manage_editFeedbackForm' % self.absolute_url())

    security.declareProtected('Change Feedback', 'manage_uploadAttFeedback')

    def manage_uploadAttFeedback(self, file_id='', file='', REQUEST=None):
        """ Replace the content of an existing attachment
        """
        file_ob = self._getOb(file_id)
        with file_ob.data_file.open('wb') as f:
            for chunk in RepUtils.iter_file_data(file):
                f.write(chunk)
        if REQUEST:
            REQUEST.RESPONSE.redirect(
                '%s/manage_editFeedbackForm' % self.absolute_url())

    security.declareProtected('Change Feedback', 'manage_deleteAttFeedback')

    def manage_deleteAttFeedback(self, file_id='', REQUEST=None):
        """ Delete an attachment
            FIXME: Why is the 'go' parameter not an method argument?   !#&%!!
        """
        p_action = REQUEST.get('go', '')
        if p_action == 'Delete':
            self.manage_delObjects(file_id)
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(
                '%s/manage_editFeedbackForm' % self.absolute_url())

    def renderFeedbacktext(self):
        pt = ZopePageTemplate(self.id+'_tmp')
        pt.write(self.feedbacktext)
        try:
            result = pt.__of__(self)()
        except Exception:
            result = self.feedbacktext
            logger.warning(
                "Unable to render feedbacktext with translations: {}".format(
                    self.absolute_url()))
        return result

    def compileFeedbacktext(self, REQUEST):
        """ If the feedbacktext has another content type than plain text or
            HTML, it will be displayed separately on this page
        """
        response = REQUEST.RESPONSE
        response.setHeader('Content-type', self.content_type)
        # fixme: loop chunk of data to display, not all at once
        response.write(self.feedbacktext)

    def getActivityDetails(self, p_attribute):
        """ returns the activity's description """
        l_process = self.unrestrictedTraverse(
            self.getParentNode().process_path)
        return getattr(getattr(l_process, self.activity_id), p_attribute)

    security.declareProtected('View', 'get_owner')

    def get_owner(self, *args, **kwargs):
        return self.getOwner(*args, **kwargs)

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

    @RepUtils.manage_as_owner
    def unrestrict_feedback(self):
        """Remove access restriction for this feedback.
           To be called by Applications.
        """
        self.manage_unrestrict(ids=[self.id])

    @RepUtils.manage_as_owner
    def restrict_feedback(self):
        """Restrict access to this feedback.
           To be called by Applications
        """
        self.manage_restrict(ids=[self.id])

    security.declarePublic('isRestricted')

    def isRestricted(self):
        """ Returns True if the feedback is restricted, False otherwise """
        return not self.acquiredRolesAreUsedBy('View')

    security.declareProtected('View', 'index_html')
    index_html = PageTemplateFile('zpt/feedback/index', globals())

    security.declareProtected('Change Feedback', 'manage_editFeedbackForm')
    manage_editFeedbackForm = PageTemplateFile('zpt/feedback/edit', globals())

    security.declareProtected(
        'Change Feedback', 'manage_uploadAttFeedbackForm')
    manage_uploadAttFeedbackForm = PageTemplateFile(
        'zpt/feedback/uploadatt', globals())

    security.declareProtected(
        'Change Feedback', 'manage_deleteAttFeedbackForm')
    manage_deleteAttFeedbackForm = PageTemplateFile(
        'zpt/feedback/deleteatt', globals())

    security.declareProtected('View', 'rdf')

    def rdf(self, REQUEST):
        """ Returns the feedback data in RDF format.
            This will include parsing the XHTML reply from XMLCONV.
            Note that the metadata is already provided by then envelope rdf.
            If feedback is restricted the 'View' permission flag is removed.
        """
        REQUEST.RESPONSE.setHeader(
            'content-type', 'application/rdf+xml; charset=utf-8')
        engine = self.getEngine()
        http_res = getattr(engine, 'exp_httpres', False)
        # if not self.canViewContent():
        #    raise Unauthorized, "Envelope is not available"

        res = []

        res.append('<?xml version="1.0" encoding="utf-8"?>')
        res.append(
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        res.append(' xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
        res.append(' xmlns:dct="http://purl.org/dc/terms/"')
        res.append(
            ' xmlns:cr="http://cr.eionet.europa.eu/ontologies/contreg.rdf#"')
        res.append(' xmlns="http://rod.eionet.europa.eu/schema.rdf#">')

        res.append('<rdf:Description rdf:about="%s">'
                   % RepUtils.xmlEncode(parse_uri(self.absolute_url(),
                                                  http_res)))
        res.append('</rdf:Description>')
        res.append('</rdf:RDF>')
        return '\n'.join(res)


InitializeClass(ReportFeedback)
