# -*- coding: utf-8 -*-
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
# Soren Roug, EEA
# Daniel Bărăgan, Eau de Web


"""Envelope object

Envelopes are the basic container objects and are analogous to directories.

$Id$"""

__version__='$Revision$'[11:-2]


import os, types, tempfile, string
from path import path
from zipstream import ZipFile
from zipstream import ZIP_DEFLATED
from zipfile import BadZipfile

import Globals, OFS.SimpleItem, OFS.ObjectManager
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl.Permissions import view_management_screens
import AccessControl.Role

from AccessControl import ClassSecurityInfo, Unauthorized
from AccessControl.SecurityManagement import getSecurityManager
from Products.Reportek import permission_manage_properties_envelopes
from Products.Reportek.exceptions import ApplicationException
from Products.Reportek.vocabularies import REPORTING_PERIOD_DESCRIPTION
from Products.PythonScripts.standard import url_quote
from zExceptions import Forbidden
from DateTime import DateTime
from DateTime.interfaces import SyntaxError
from StringIO import StringIO
from ZPublisher.Iterators import filestream_iterator
import logging
import xlwt
logger = logging.getLogger("Reportek")

# Product specific imports
from Products.Reportek import RepUtils
from Products.Reportek import Document
from Products.Reportek import Hyperlink
from Products.Reportek import Feedback
from Products.Reportek.BaseDelivery import BaseDelivery
from Products.Reportek.config import ZIP_CACHE_THRESHOLD
from Products.Reportek.config import ZIP_CACHE_ENABLED
from Products.Reportek.RepUtils import get_zip_cache
import RepUtils
import Document
import Hyperlink
import Feedback
from constants import WORKFLOW_ENGINE_ID, ENGINE_ID
from exceptions import InvalidPartOfYear
from EnvelopeInstance import EnvelopeInstance
from EnvelopeRemoteServicesManager import EnvelopeRemoteServicesManager
from EnvelopeCustomDataflows import EnvelopeCustomDataflows
import zip_content
from zope.interface import implements
from interfaces import IEnvelope
from paginator import DiggPaginator, EmptyPage, InvalidPage
from Products.Reportek.config import XLS_HEADINGS
import transaction


manage_addEnvelopeForm = PageTemplateFile('zpt/envelope/add', globals())

def manage_addEnvelope(self, title, descr, year, endyear, partofyear, locality,
        REQUEST=None, previous_delivery=''):
    """ Add a new Envelope object with id *id*.
    """
    id= RepUtils.generate_id('env')
    if not REQUEST:
        actor = self.REQUEST.AUTHENTICATED_USER.getUserName()
    else:
        actor = REQUEST.AUTHENTICATED_USER.getUserName()
    # finds the (a !) process suited for this envelope
    l_err_code, l_result = getattr(self, WORKFLOW_ENGINE_ID).findProcess(self.dataflow_uris, self.country)
    if l_err_code == 0:
        process = self.unrestrictedTraverse(l_result, None)
    else:
        raise l_result[0], l_result[1]

    if valid_year(year):
        year = int(year)
    else:
        year = ''
    if valid_year(endyear):
        endyear = int(endyear)
    else:
        endyear = ''
    if not year and endyear:
        year = endyear
    now = DateTime()
    preliminary_obl = False

    engine = getattr(self, ENGINE_ID)
    for uri in self.dataflow_uris:
        if uri in engine.preliminary_obligations:
            preliminary_obl = True

    if year and year > now.year() and not preliminary_obl:
        if REQUEST is not None:
            error_msg = 'You cannot submit a report which relates to a future\
                         year. Please fill in the correct year!'
            return self.manage_addEnvelopeForm(error=error_msg)
        else:
            raise ValueError('Cannot create envelope which relates to a future year')

    year_parts = ['WHOLE_YEAR', 'FIRST_HALF', 'SECOND_HALF',
                  'FIRST_QUARTER', 'SECOND_QUARTER', 'THIRD_QUARTER',
                  'FOURTH_QUARTER']
    months = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
              "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]

    if partofyear and not partofyear in (year_parts + months):
        raise InvalidPartOfYear

    dataflow_uris = getattr(self,'dataflow_uris',[])   # Get it from collection
    ob = Envelope(process, title, actor, year, endyear, partofyear, self.country, locality, descr, dataflow_uris)
    ob.id = id
    self._setObject(id, ob)
    ob = self._getOb(id)
    if previous_delivery:
        l_envelope = self.restrictedTraverse(previous_delivery)
        l_data = l_envelope.manage_copyObjects(l_envelope.objectIds('Report Document'))
        ob.manage_pasteObjects(l_data)
    ob.startInstance(REQUEST)  # Start the instance
    if REQUEST is not None:
        return REQUEST.RESPONSE.redirect(self.absolute_url())
    else:
        return ob.absolute_url()


def valid_year(year_str):
    try:
        year = int(year_str) #Checks conversion
        DateTime('%s/01/01' %year) #Raises SyntaxError below year 1000
        return True
    except ValueError as ex:
        return False
    except SyntaxError as ex:
        raise ex


def get_first_accept(req_dict):
    """ Figures out which type of content the webbrowser prefers
        If it is 'application/rdf+xml', then send RDF
    """
    s = req_dict.get_header('HTTP_ACCEPT','*/*')
    segs = s.split(',')
    firstseg = segs[0].split(';')
    return firstseg[0].strip()

class Envelope(EnvelopeInstance, EnvelopeRemoteServicesManager, EnvelopeCustomDataflows, BaseDelivery):
    """ Envelopes are basic container objects that provide a standard
        interface for object management. Envelope objects also implement
        a management interface
    """
    implements(IEnvelope)
    meta_type='Report Envelope'
    icon = 'misc_/Reportek/envelope.gif'

    # location of the file-repository
    _repository = ['reposit']

    security = ClassSecurityInfo()

    security.setPermissionDefault('Audit Envelopes', ('Manager', 'Owner'))

    manage_options=(
        (OFS.ObjectManager.ObjectManager.manage_options[0],)+
        (
        {'label':'View', 'action':'index_html', 'help':('OFSP','Envelope_View.stx')},
        {'label':'Properties', 'action':'manage_prop', 'help':('OFSP','Envelope_View.stx')},
        )+
        EnvelopeInstance.manage_options+
        AccessControl.Role.RoleManager.manage_options+
        OFS.SimpleItem.Item.manage_options
        )

    security.declareProtected('Change Envelopes', 'manage_cutObjects')
    security.declareProtected('Change Envelopes', 'manage_copyObjects')
    security.declareProtected('Change Envelopes', 'manage_pasteObjects')
    security.declareProtected('Change Envelopes', 'manage_renameForm')
    security.declareProtected('Change Envelopes', 'manage_renameObject')
    security.declareProtected('Change Envelopes', 'manage_renameObjects')

    macros = PageTemplateFile('zpt/envelope/macros', globals()).macros

    def __init__(self, process, title, authUser, year, endyear, partofyear, country, locality, descr, dataflow_uris=None):
        """ Envelope constructor
        """
        BaseDelivery.__init__(self, title=title, year=year, endyear=endyear,
                              partofyear=partofyear, country=country,
                              locality=locality, descr=descr,
                              dataflow_uris=dataflow_uris)
        self.reportingdate = DateTime()

        self.released = 0
        # workflow part
        self.customer = authUser
        EnvelopeInstance.__init__(self, process)

    def get_qa_workitems(self):
        """Return a list of AutomaticQA workitems."""
        return [
            wi for wi in self.getMySelf().getListOfWorkitems()
            if wi.activity_id == 'AutomaticQA'
        ]

    @property
    def is_blocked(self):
        """Returns True if the last AutomaticQA workitem of the envelope
        has a blocker feedback."""
        QA_workitems = self.get_qa_workitems()
        if not QA_workitems:
            return False
        else:
            return getattr(QA_workitems[-1], 'blocker', False)

    def get_qa_feedbacks(self):
        """Return a list containing all AutomaticQA feedback objects."""
        return [rf for rf in self.objectValues('Report Feedback')
                if getattr(rf, 'title', '').startswith('AutomaticQA')]

    @property
    def has_unknown_qa_result(self):
        """ Returns True if an AutomaticQA feedback object has an 'UNKNOWN'
            feedback status. Every feedback_status other than the ones defined
            in VALID_FB_STATUSES is treated as 'UNKNOWN'.
        """
        VALID_FB_STATUSES = [
            'INFO',
            'SKIPPED',
            'OK',
            'WARNING',
            'ERROR',
            'FAILED',
            'BLOCKER'
        ]

        aqa_fbs = self.get_qa_feedbacks()

        for fb in aqa_fbs:
            fb_status = getattr(fb, 'feedback_status', 'UNKNOWN')
            if fb_status not in VALID_FB_STATUSES:
                return True

    @property
    def has_unacceptable_qa_result(self):
        """Return True if AutomaticQA feedback object has an 'ERROR', 'BLOCKER'
        or 'FAILED' feedback status."""

        UNACCEPTABLE_FB_STATUSES = [
            'BLOCKER',
            'ERROR',
            'FAILED'
        ]

        aqa_fbs = self.get_qa_feedbacks()

        for fb in aqa_fbs:
            fb_status = getattr(fb, 'feedback_status', 'UNKNOWN')
            if fb_status in UNACCEPTABLE_FB_STATUSES:
                return True

    def get_fb_with_status(self, status):
        """Returns a list of fb ids with status status."""
        aqa_fbs = self.get_qa_feedbacks()
        fb_ids = []
        for fb in aqa_fbs:
            fb_status = getattr(fb, 'feedback_status', 'UNKNOWN')
            if fb_status == status:
                fb_ids.append(fb.getId())

        return fb_ids

    @property
    def has_no_qa_result(self):
        """Return True if an AutomaticQA feedback has no feedback status."""
        QA_workitems = self.get_qa_workitems()
        if QA_workitems:
            aqa_fbs = self.get_qa_feedbacks()
            if not aqa_fbs:
                return True
            else:
                aqa_no_fbstatus = [fb for fb in aqa_fbs
                                   if not getattr(fb, 'feedback_status', None)]
                if aqa_no_fbstatus:
                    return True

    @property
    def has_failed_qa(self):
        """Return True if the last AutomaticQA has failed and given up."""
        QA_workitems = self.get_qa_workitems()
        if not QA_workitems:
            return False

        last_qa = QA_workitems[-1]
        return last_qa.failure

    @property
    def successful_qa(self):
        """Return True if not has_no_qa_result and not has_failed_qa."""

        if not self.has_no_qa_result and not self.has_failed_qa:
            return True

    def uns_is_set(self):
        """ Returns True if UNS server is set """
        engine = getattr(self, ENGINE_ID)
        if engine and getattr(engine, 'UNS_server', False):
            return True
        else:
            return False

    def has_blocker_feedback(self, REQUEST=None):
        """ web callable version of is_blocked """
        return self.is_blocked

    def is_acceptable(self):
        """ Returns acceptability status: 
            True: definitly blocked
            False: definitely not blocked
            None: no completed AutomaticQA activity established if the envelope is blocked or not 
        """
        if self.is_blocked:
            return False
        completed_automaticQA_workitems = [
            wi for wi in self.getMySelf().getListOfWorkitems()
               if wi.activity_id == 'AutomaticQA' and wi.status == 'complete'
        ]
        if completed_automaticQA_workitems:
            return True
        else:
            return None

    def all_meta_types( self, interfaces=None ):
        """ Called by Zope to determine what kind of object the envelope can contain
        """
        y = [  {'name': 'Report Document', 'action': 'manage_addDocumentForm', 'permission': 'Add Envelopes'},
               {'name': 'Report Hyperlink', 'action': 'manage_addHyperlinkForm', 'permission': 'Add Envelopes'},
               {'name': 'Report Feedback', 'action': 'manage_addFeedbackForm', 'permission': 'Add Feedback'}]
        return y

    # This next lines are bogus but needed for Zope to register the permission
    security.declareProtected('Audit Envelopes', 'bogus_function')
    def bogus_function(self):
        return

    security.declarePublic('getMySelf')
    def getMySelf(self):
        """ Used to retrieve the envelope object from the workitem """
        return self

    security.declarePublic('getActorDraft')
    def getActorDraft(self):
        """ Used to retrieve draft Actor """
        draft_workitems = [wi for wi in self.getListOfWorkitems()
                           if wi.activity_id == 'Draft']
        if draft_workitems:
            latestDraftWorkitem = draft_workitems[-1]

            return latestDraftWorkitem.actor

    security.declareProtected('View', 'getSubmittedDocs')
    def getSubmittedDocs(self):
        documents_list = self.objectValues(['Report Document',
                                            'Report Hyperlink'])
        documents_list.sort(key=lambda ob: ob.getId().lower())
        return documents_list

    security.declarePublic('getEnvelopeOwner')
    def getEnvelopeOwner(self):
        """ """
        return self.getOwner()

    security.declareProtected('Change Envelopes', 'manage_copyDelivery')
    def manage_copyDelivery(self, previous_delivery, REQUEST=None):
        """ Copies files from another envelope """
        l_envelope = self.unrestrictedTraverse(previous_delivery)
        l_files_ids = l_envelope.objectIds(['Report Document','Report Hyperlink'])
        if len(l_files_ids) > 0:
            l_data = l_envelope.manage_copyObjects(l_files_ids)
            self.manage_pasteObjects(l_data)
            if REQUEST is not None:
                return self.messageDialog(
                                message="The files were copied here",
                                action=REQUEST['HTTP_REFERER'])
        else:
                return self.messageDialog(
                                message="No files available for this delivery",
                                action=REQUEST['HTTP_REFERER'])

    ##################################################
    # Interface components
    ##################################################

    # When the user enters an envelope that he has to do work in,
    # then he should be redirected to the special work page
    # But he should still be able to see the overview page.
    security.declareProtected('View', 'overview')
    overview = PageTemplateFile('zpt/envelope/overview', globals())

    security.declareProtected('View', 'index_html')
    def index_html(self, REQUEST=None):
        """ """
        if REQUEST is None:
            REQUEST = self.REQUEST
        session = getattr(REQUEST, 'SESSION', None)
        if session and session.has_key('status_extra'):
            session.delete('status_extra')
        status_extra = None
        browser_accept_type = get_first_accept(REQUEST)
        if browser_accept_type == 'application/rdf+xml':
            REQUEST.RESPONSE.redirect(self.absolute_url() + '/rdf', status=303) # The Linked Data guys want status 303
            return ''

        l_current_actor = REQUEST['AUTHENTICATED_USER'].getUserName()
        l_no_active_workitems = 0
        for w in self.objectValues('Workitem'):
            if w.status == 'active' and w.actor!= 'openflow_engine' and (w.actor == l_current_actor or getSecurityManager().checkPermission('Change Envelopes', self)):
                l_application_url = self.getApplicationUrl(w.id)
                if l_application_url:
                    # if more workitems are active for the current user, the overview is returned
                    l_no_active_workitems += 1
                    l_default_tab = w.id
        if l_no_active_workitems == 1:
            application = self.getPhysicalRoot().restrictedTraverse(l_application_url)
            params = {
                'workitem_id': l_default_tab,
                'client': self,
                'document_title': application.title,
                'REQUEST': REQUEST,
                'RESPONSE': REQUEST.RESPONSE
            }
            try:
                return application(**params)
            except Exception as e:
                msg = "ApplicationException while trying to display: {} "\
                      "for envelope: {}, with workitem_id: {} - Error: {}"\
                      .format(l_application_url, self.absolute_url(),
                              l_default_tab, e)
                logger.exception(msg)
                status_extra = ('error',
                                'A system error occured and an alert has been'
                                ' triggered for the administrators!')
                REQUEST.SESSION.set('status_extra', status_extra)

        return self.overview(REQUEST)

    security.declareProtected('View management screens', 'manage_main_inh')
    manage_main_inh = EnvelopeInstance.manage_main
    EnvelopeInstance.manage_main._setName('manage_main')

    security.declareProtected('View', 'manage_main')
    def manage_main(self,*args,**kw):
        """ Define manage main to be context aware """

        if getSecurityManager().checkPermission('View management screens',self):
            return apply(self.manage_main_inh,(self,)+ args,kw)
        else:
            # args is a tuple, the first element being the object instance, the second the REQUEST
            if len(args) > 1:
                return apply(self.index_html, (args[1],))
            else:
                return apply(self.index_html, ())

    security.declareProtected('View', 'getDocuments')
    def getDocuments(self, REQUEST):
        """ return the list of documents """
        documents_list = self.objectValues(['Report Document', 'Report Hyperlink'])
        documents_list.sort(key=lambda ob: ob.getId().lower())
        paginator = DiggPaginator(documents_list, 20, body=5, padding=2, orphans=5)   #Show 10 documents per page

        # Make sure page request is an int. If not, deliver first page.
        try:
            page = int(REQUEST.get('page', '1'))
        except ValueError:
            page = 1

        # If page request (9999) is out of range, deliver last page of results.
        try:
            documents = paginator.page(page)
        except (EmptyPage, InvalidPage):
            documents = paginator.page(paginator.num_pages)

        return documents

    security.declareProtected('View', 'documents_section')
    documents_section = PageTemplateFile('zpt/envelope/documents_section', globals())

    security.declareProtected('View', 'documents_pagination')
    documents_pagination = PageTemplateFile('zpt/envelope/documents_pagination', globals())

    security.declareProtected('View', 'documents_management_section')
    documents_management_section = PageTemplateFile('zpt/envelope/documentsmanagement_section', globals())

    security.declareProtected('View', 'feedback_section')
    feedback_section = PageTemplateFile('zpt/envelope/feedback_section', globals())

    security.declareProtected('View', 'envelope_tabs')
    envelope_tabs = PageTemplateFile('zpt/envelope/tabs', globals())

    security.declareProtected('Change Envelopes', 'manage_prop')
    manage_prop = PageTemplateFile('zpt/envelope/properties', globals())

    security.declareProtected('Change Envelopes', 'envelope_previous')
    envelope_previous = PageTemplateFile('zpt/envelope/earlierreleases', globals())

    security.declareProtected('View', 'data_quality')
    data_quality = PageTemplateFile('zpt/envelope/data_quality', globals())


    security.declareProtected('Release Envelopes', 'content_registry_ping')
    def content_registry_ping(self, delete=False, async=True):
        """ Instruct ReportekEngine to ping CR.

            `delete` instructs the envelope to don't ping CR on
            create or update but for delete.
            `async` tells it to do it async or not.

            Note that on delete, CR does not actually fetch envelope contents
            from CDR thus we can make the CR calls async even in that case
            when the envelope would not be available to the public anymore.
        """

        engine = getattr(self, ENGINE_ID)
        crPingger = engine.contentRegistryPingger
        if not crPingger:
            logger.debug("Not pingging Content Registry.")
            return

        ping_argument = 'delete' if delete else 'create'
        # the main uri - the rdf listing everything inside
        uris = [ self.absolute_url() + '/rdf' ]
        innerObjsByMetatype = self._getObjectsForContentRegistry()
        # ping CR for inner uris
        uris.extend( o.absolute_url() for objs in innerObjsByMetatype.values() for o in objs )
        if async:
            crPingger.content_registry_ping_async(uris,
                    ping_argument=ping_argument, envPathName=self.absolute_url())
        else:
            crPingger.content_registry_ping(uris, ping_argument=ping_argument)
        return


    ##################################################
    # Manage release status
    # The release-flag locks the envelope from getting new files.
    # It thereby prevents the clients from downloading incomplete envelopes.
    ##################################################
    security.declareProtected(view_management_screens, 'release_envelope_manual')
    def release_envelope_manual(self):
        """ Releases an envelope to the public
            Must also set the "View" permission on the object?
        """
        return self.release_envelope()

    security.declareProtected('Release Envelopes', 'release_envelope')
    ##################################################
    # Releases an envelope to the public
    # Must also set the "View" permission on the object?
    ##################################################
    def release_envelope(self):
        # no doc string - don't call this from browser
        if self.released != 1:
            self.released = 1
            self.reportingdate = DateTime()
            # update ZCatalog
            self.reindex_object()
            self._invalidate_zip_cache()
            # make this change visible right away (for the CR ping following this call for instance)
            # otherwise the envelope will really be released only after the calling view
            # of this function will finish, and ZPublisher will commit automatically
            transaction.commit()
            logger.debug("Releasing Envelope: %s" % self.absolute_url())
        if self.REQUEST is not None:
            return self.messageDialog(
                            message="The envelope has now been released to the public!",
                            action='./manage_main')

    security.declareProtected(view_management_screens, 'unrelease_envelope_manual')
    def unrelease_envelope_manual(self):
        """ Unreleases an envelope to the public
            Must also remove the "View" permission on the object?
        """
        return self.unrelease_envelope()

    security.declareProtected('Release Envelopes', 'unrelease_envelope')
    ##################################################
    # Unreleases an envelope to the public
    # Must also remove the "View" permission on the object?
    ##################################################
    def unrelease_envelope(self):
        # no doc string - don't call this from browser
        if self.released != 0:
            self.released = 0
            # update ZCatalog
            self.reindex_object()
            transaction.commit()
            logger.debug("UNReleasing Envelope: %s" % self.absolute_url())
        if self.REQUEST is not None:
            return self.messageDialog(
                            message="The envelope is no longer available to the public!",
                            action='./manage_main')

    # See if this is really used somewhere
    security.declareProtected('View', 'delivery_status')
    def delivery_status(self):
        """ Status value of the delivery envelope
            Used for security reasons managing access rights,
            for tracking whether the delivery is ready to be released,
            for managing the dataflow by checking what is the next step in the dataflow process
        """
        return self.released

    ##################################################
    # Edit metadata
    ##################################################

    security.declareProtected(permission_manage_properties_envelopes, 'manage_editEnvelope')
    def manage_editEnvelope(self, title, descr,
            year, endyear, partofyear, country, locality, dataflow_uris=[],
            REQUEST=None):
        """ Manage the edited values
        """
        if not dataflow_uris:
            if not self.dataflow_uris:
                if REQUEST:
                    return self.messageDialog(
                        "You must specify at least one obligation. Settings not saved!",
                        action='./manage_prop')
                return
        else:
            self.dataflow_uris = dataflow_uris

        self.title=title
        try: self.year = int(year)
        except: self.year = ''
        try: self.endyear = int(endyear)
        except: self.endyear = ''
        self._check_year_range()
        self.partofyear=partofyear
        self.country=country
        self.locality=locality
        self.descr=descr
        # update ZCatalog
        self.reindex_object()
        if REQUEST is not None:
            return self.messageDialog(
                            message="The properties of %s have been changed!" % self.id,
                            action='./')

    security.declareProtected(permission_manage_properties_envelopes, 'manage_changeEnvelope')
    def manage_changeEnvelope(self, title=None, descr=None,
            year=None, endyear=None, country=None, dataflow_uris=None,
            reportingdate=None,
            REQUEST=None):
        """ Manage the changed values
        """
        if title is not None:
            self.title=title
        if year is not None:
            try: self.year = int(year)
            except: self.year = ''
        if endyear is not None:
            try: self.endyear = int(endyear)
            except: self.endyear = ''
        self._check_year_range()
        if country is not None:
            self.country=country
        if dataflow_uris is not None:
            self.dataflow_uris = dataflow_uris
        if reportingdate is not None:
            self.reportingdate = DateTime(reportingdate)
        if descr is not None:
            self.descr=descr
        # update ZCatalog
        self.reindex_object()
        if REQUEST is not None:
            return self.messageDialog(
                            message="The properties of %s have been changed!" % self.id,
                            action='./')

    ##################################################
    # These methods represent the outcome of the CDR discussion.
    # It is necessary to set acquire=0. Otherwise Anonymous would still
    # have View access.
    ##################################################

    security.declareProtected('Change Envelopes', 'manage_restrict')
    def manage_restrict(self, ids=None, REQUEST=None):
        """
            Restrict access to the named objects.
            Figure out what roles exist, but don't give access to
            anonymous and authenticated
        """
        vr = list(self.valid_roles())
        for item in ('Anonymous', 'Authenticated'):
            try: vr.remove(item)
            except: pass
        return self._set_restrictions(ids, roles=vr, acquire=0, permission='View', REQUEST=REQUEST)

    security.declareProtected('Change Envelopes', 'manage_unrestrict')
    def manage_unrestrict(self, ids=None, REQUEST=None):
        """
            Remove access restriction to the named objects.
        """
        # if this is called via HTTP, the list will just be a string
        if type(ids) == type(''):
            l_ids = ids[1:-1].split(', ')
            l_ids = [x[1:-1] for x in l_ids]
        else:
            l_ids = ids
        return self._set_restrictions(l_ids,roles=[], acquire=1, permission='View', REQUEST=REQUEST)

    security.declareProtected('Change Envelopes', 'restrict_editing_files')
    def restrict_editing_files(self, REQUEST=None):
        """
            Restrict permission to change files' content.
        """
        ids = self.objectIds('Document')
        vr = list(self.valid_roles())
        for item in ('Anonymous', 'Authenticated'):
            try: vr.remove(item)
            except: pass
        return self._set_restrictions(ids, roles=vr, acquire=0, permission='Change Reporting Documents', REQUEST=REQUEST)

    security.declareProtected('Change Envelopes', 'unrestrict_editing_files')
    def unrestrict_editing_files(self, REQUEST=None):
        """
            Remove restriction to change files' content.
        """
        return self._set_restrictions(self.objectIds('Document'), roles=[], acquire=1, permission='Change Reporting Documents', REQUEST=REQUEST)

    def _set_restrictions(self, ids, roles=[], acquire=0, permission='View', REQUEST=None):
        """
            Set access to the named objects.
            This basically finds the objects named in ids and
            calls the manage_permission on it.
        """
        if ids is None and REQUEST is not None:
            return self.messageDialog(
                            message="You must select one or more items to perform this operation.",
                            action='manage_main')
        elif ids is None:
            raise ValueError, 'ids must be specified'

        if type(ids) is type(''):
            ids=[ids]
        for id in ids:
            ob=self._getOb(id)
            ob.manage_permission(permission, roles=roles, acquire=acquire)
        if REQUEST is not None:
            return self.messageDialog(
                            message="The files are now restricted!")

    security.declarePublic('areRestrictions')
    def areRestrictions(self):
        """ Returns 1 if at least a file is restricted from the public, 0 otherwise """
        for doc in self.objectValues(['Report Document','Report Hyperlink']):
            if not doc.acquiredRolesAreUsedBy('View'):
                return 1
        return 0

    ##################################################
    # Determine various permissions - used in DTML
    ##################################################

    security.declarePublic('canViewContent')
    def canViewContent(self):
        """ Determine whether or not the content of the envelope can be seen by the current user """
        hasThisPermission = getSecurityManager().checkPermission
        return hasThisPermission('Change Envelopes', self) or hasThisPermission('Release Envelopes', self) \
                or hasThisPermission('Audit Envelopes', self) or hasThisPermission('Add Feedback', self) \
                or self.released

    security.declarePublic('canAddFiles')
    def canAddFiles(self):
        """ Determine whether or not the content of the envelope can be seen by the current user """
        hasThisPermission = getSecurityManager().checkPermission
        return hasThisPermission('Change Envelopes', self) and not self.released

    security.declarePublic('canAddFeedback')
    def canAddFeedback(self):
        """ Determine whether or not the current user can add manual feedback """
        hasThisPermission = getSecurityManager().checkPermission

        request = getattr(self, 'REQUEST', None)
        can_add_fb = False
        if request:
            session = getattr(request, 'SESSION', None)
            if session:
                can_add_fb = session.get('can_add_feedback_before_release',
                                         False)

        return hasThisPermission('Add Feedback', self) and (self.released or can_add_fb)

    security.declarePublic('canEditFeedback')
    def canEditFeedback(self):
        """ Determine whether or not the current user can edit existing manual feedback """
        hasThisPermission = getSecurityManager().checkPermission
        return hasThisPermission('Change Feedback', self) and self.released

    security.declarePublic('canChangeEnvelope')
    def canChangeEnvelope(self):
        """ Determine whether or not the current user can change the properties of the envelope """
        hasThisPermission = getSecurityManager().checkPermission
        return hasThisPermission('Change Envelopes', self)

    ##################################################
    # Feedback operations
    ##################################################

    security.declareProtected('View', 'getFeedbacks')
    def getFeedbacks(self):
        """ return all the feedbacks """
        return self.objectValues('Report Feedback')

    security.declareProtected('View', 'feedback_objects_details')
    def feedback_objects_details(self):
        """ xml-rpc interface to get feedbacks details """
        result = {'feedbacks': []}
        feedbacks = self.objectValues('Report Feedback')
        for item in feedbacks:
            if item.document_id:
                referred_file = '%s/%s' %(self.absolute_url(), item.document_id)
            else:
                referred_file = ''
            if 'qa-output' in item.objectIds():
                qa_output_url = '%s/qa-output' %item.absolute_url()
            else:
                qa_output_url = '%s' %item.absolute_url()
            result['feedbacks'].append(
                {
                  'title'         : item.title,
                  'releasedate'   : item.releasedate.HTML4(),
                  'isautomatic'   : item.automatic,
                  'content_type'  : item.content_type,
                  'referred_file' : referred_file,
                  'qa_output_url' : qa_output_url
                },
            )
        return result

    security.declareProtected('View', 'getFeedbackObjects')
    def getFeedbackObjects(self):
        """ return sorted feedbacks by their 'title' property, the manual feedback if always first """
        res = []
        feedback_list = self.getFeedbacks()
        manual_feedback = self.getManualFeedback()
        if manual_feedback:
            res.append(manual_feedback)
            auto_feedbacks = RepUtils.utSortByAttr(self.getFeedbacks(), 'title')
            auto_feedbacks.remove(manual_feedback)
            res.extend(auto_feedbacks)
        else:
            res = RepUtils.utSortByAttr(self.getFeedbacks(), 'title')
        return res

    security.declareProtected('View', 'getManualFeedback')
    def getManualFeedback(self):
        """ return manual feedback"""
        res = None
        for obj in self.getFeedbacks():
            if obj.releasedate == self.reportingdate and not obj.automatic:
                res = obj
                break
        return res

    #obsolete
    security.declareProtected('View', 'hasFeedbackForThisRelease')
    def hasFeedbackForThisRelease(self):
        """ Returns true if the envelope contains a Report Feedback
            for the current release date
        """
        bResult = 0
        for obj in self.getFeedbacks():
            if obj.releasedate == self.reportingdate and not obj.automatic:
                bResult = 1
        return bResult

    security.declareProtected('Add Feedback', 'manage_deleteFeedback')
    def manage_deleteFeedback(self, file_id='', REQUEST=None):
        """ """
        self.manage_delObjects(file_id)
        REQUEST.RESPONSE.redirect(self.absolute_url())

    @RepUtils.manage_as_owner
    def delete_feedbacks(self, fb_ids):
        """Delete the feedbacks with fb_ids."""
        self.manage_delObjects(fb_ids)

    @RepUtils.manage_as_owner
    def add_feedback(self, **kwargs):
        """Add feedback. To be called by Applications."""
        self.manage_addFeedback(**kwargs)

    security.declareProtected('Add Feedback', 'manage_addFeedbackForm')
    manage_addFeedbackForm = Feedback.manage_addFeedbackForm
    security.declareProtected('Add Feedback', 'manage_addFeedback')
    manage_addFeedback = Feedback.manage_addFeedback
    security.declareProtected('View management screens', 'manage_addManualQAFeedback')
    manage_addManualQAFeedback = Feedback.manage_addManualQAFeedback
    security.declareProtected('Add Feedback', 'manage_deleteFeedbackForm')
    manage_deleteFeedbackForm = PageTemplateFile('zpt/feedback/delete', globals())

    security.declareProtected('Change Envelopes', 'manage_addDocumentForm')
    manage_addDocumentForm = Document.manage_addDocumentForm
    security.declareProtected('Change Envelopes', 'manage_addDocument')
    manage_addDocument = Document.manage_addDocument

    security.declareProtected('Add Envelopes', 'manage_addHyperlinkForm')
    manage_addHyperlinkForm = Hyperlink.manage_addHyperlinkForm
    security.declareProtected('Add Envelopes', 'manage_addHyperlink')
    manage_addHyperlink = Hyperlink.manage_addHyperlink

    ##################################################
    # Zip/unzip functions
    ##################################################

    security.declareProtected('Add Envelopes', 'manage_addzipfileform')
    manage_addzipfileform = PageTemplateFile('zpt/envelope/add_zip', globals())

    security.declareProtected('View', 'envelope_zip')
    def envelope_zip(self, REQUEST, RESPONSE):
        """ Go through the envelope and find all the external documents
            then zip them and send the result to the user.
            It is meant for humans, so it's ok to only allow them to download
            envelopes they need to work on (e.g. reporters) or are released.

            fixme: It is not impossible that the client only wants part of the
            zipfile, as in index_html of Document.py due to the partial
            requests that can be made with HTTP
        """

        if not self.canViewContent():
            raise Unauthorized, "Envelope is not available"

        public_docs = []
        restricted_docs = []

        for doc in self.objectValues('Report Document'):
            if getSecurityManager().checkPermission('View', doc):
                public_docs.append(doc)
            else:
                restricted_docs.append(doc)

        zip_cache = get_zip_cache()
        envelope_path = '/'.join(self.getPhysicalPath())
        if restricted_docs:
            flag = 'all'
            response_zip_name = self.getId() + '-all.zip'
        else:
            flag = 'public'
            response_zip_name = self.getId() + '.zip'
        cache_key = zip_content.encode_zip_name(envelope_path, flag)
        cached_zip_path = zip_cache/cache_key

        if cached_zip_path.isfile():
            with cached_zip_path.open('rb') as data_file:
                return stream_response(RESPONSE, data_file,
                                       response_zip_name, 'application/x-zip')

        with tempfile.NamedTemporaryFile(suffix='.temp', dir=zip_cache) as tmpfile:
            with ZipFile(mode="w", compression=ZIP_DEFLATED, allowZip64=True) as outzd:
                try:
                    for doc in public_docs:
                        outzd.write_iter(doc.getId(),
                                         RepUtils.iter_file_data(doc.data_file.open()))

                    for fdbk in self.objectValues('Report Feedback'):
                        if getSecurityManager().checkPermission('View', fdbk):
                            outzd.writestr('%s.html' % fdbk.getId(),
                                           zip_content.get_feedback_content(fdbk))

                            for attachment in fdbk.objectValues(['File', 'File (Blob)']):
                                if attachment.meta_type == 'File (Blob)':
                                    outzd.write_iter(attachment.getId(),
                                                     RepUtils.iter_file_data(attachment.data_file.open()))
                                else:
                                    outzd.write_iter(attachment.getId(),
                                                     RepUtils.iter_ofs_file_data(attachment))
                    metadata = {
                        'feedbacks.html': zip_content.get_feedback_list,
                        'metadata.txt': zip_content.get_metadata_content,
                        'README.txt': zip_content.get_readme_content,
                        'history.txt': zip_content.get_history_content
                    }
                    # write metadata files
                    for meta in metadata:
                        outzd.writestr(meta, metadata[meta](self))

                    # write to temporary file before streaming the response
                    # otherwise we wont have the needed content length
                    for data in outzd:
                        tmpfile.write(data)

                except Exception as e:
                    raise ValueError("An error occurred while preparing the zip file. {}".format(str(e)))

                else:
                    # only save cache file if greater than threshold
                    if os.stat(tmpfile.name).st_size > ZIP_CACHE_THRESHOLD and ZIP_CACHE_ENABLED:
                        os.link(tmpfile.name, cached_zip_path)

                    tmpfile.seek(0)
                    return stream_response(RESPONSE, tmpfile,
                                           response_zip_name, 'application/x-zip')

    def _invalidate_zip_cache(self):
        """ delete zip cache files """
        zip_cache = get_zip_cache()
        envelope_path = '/'.join(self.getPhysicalPath())
        for flag in ['public', 'all']:
            cache_key = zip_content.encode_zip_name(envelope_path, flag)
            cached_zip_path = zip_cache/cache_key
            if cached_zip_path.isfile():
                cached_zip_path.unlink()

    def _add_file_from_zip(self,zipfile,name, restricted=''):
        """ Generate id from filename and make sure,
            there are no spaces in the id.
        """
        id = self.cook_file_id(name)
        self.manage_addDocument(id=id, title=id, file=zipfile, restricted=restricted)

    security.declareProtected('Add Envelopes', 'manage_addzipfile')
    def manage_addzipfile(self, file='', content_type='', restricted='', REQUEST=None):
        """ Expands a zipfile into a number of Documents.
            Goes through the zipfile and calls manageaddDocument
            This function does not apply any special treatment to XML files,
            use manage_addDDzipfile for that
        """

        if type(file) is not type('') and hasattr(file,'filename'):
            # According to the zipfile.py ZipFile just needs a file-like object
            zf = zip_content.ZZipFileRaw(file)
            for name in zf.namelist():
                # test that the archive is not hierarhical
                if name[-1] == '/' or name[-1] == '\\':
                    return self.messageDialog(
                                    message="The zip file you specified is hierarchical. It contains folders.\nPlease upload a non-hierarchical structure of files.",
                                    action='./index_html')

            for name in zf.namelist():
                zf.setcurrentfile(name)
                self._add_file_from_zip(zf, name, restricted)
                transaction.commit()

            if REQUEST is not None:
                return self.messageDialog(
                                message="The file(s) were successfully created!",
                                action='./manage_main')

        elif REQUEST is not None:
            return self.messageDialog(
                            message="You must specify a file!",
                            action='./manage_main')

    security.declareProtected('View', 'getZipInfo')
    def getZipInfo(self, document):
        """ Lists the contents of a zip file """
        files = []
        # FIXME Why is application/octet-stream here? this might fix a glitch, so we'll keep it for now
        if document.content_type in ['application/octet-stream', 'application/zip', 'application/x-compressed']:
            try:
                data_file = document.data_file.open()
                zf = zip_content.ZZipFile(data_file)
                for zipinfo in zf.infolist():
                    files.append(zipinfo.filename)
                zf.close()
                data_file.close()
            # This version of Python reports IOError on empty files
            # We might get Value error if the opened zip was not an actual zip
            except (BadZipfile, IOError, ValueError):
                pass
        return files

    ##################################################
    # metadata envelope functions
    ##################################################

    security.declareProtected('View', 'xml')
    def xml(self, inline='false', REQUEST=None):
        """ Returns the envelope metadata in XML format.
            It is meant for web services, so it only filters what the account
            has the rights to access and does not look for release status.
        """
        from XMLMetadata import XMLMetadata
        xml = XMLMetadata(self)
        REQUEST.RESPONSE.setHeader('content-type', 'text/xml; charset=utf-8')
        return xml.envelopeMetadata(inline)

    def _getObjectsForContentRegistry(self):
        objByMetatype = {}
        metatypes = ['Report Document', 'Report Hyperlink', 'Report Feedback']
        for t in metatypes:
            objByMetatype[t] = [ o for o in self.objectValues(t) ]
        return objByMetatype

    security.declareProtected('View', 'get_custom_rdf_meta')
    def get_custom_rdf_meta(self):
        """Return custom envelope type metadata for RDF export."""
        objsByType = self._getObjectsForContentRegistry()
        res = []
        creator = self.getActorDraft()
        if not creator:
            creator = self.customer
        res.append('<dct:creator>%s</dct:creator>' % RepUtils.xmlEncode(creator))

    security.declareProtected('View', 'get_custom_delivery_rdf_meta')
    def get_custom_delivery_rdf_meta(self):
        """Return custom content type metadata for RDF export."""
        res = []
        objsByType = self._getObjectsForContentRegistry()
        creator = self.getActorDraft()
        if not creator:
            creator = self.customer

        res.append('<dct:creator>%s</dct:creator>' % RepUtils.xmlEncode(creator))
        res.append('<released rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</released>' % self.reportingdate.HTML4())
        res.append('<link>%s</link>' % RepUtils.xmlEncode(self.absolute_url()))

        for o in objsByType.get('Report Document', []):
            res.append('<hasFile rdf:resource="%s"/>' % RepUtils.xmlEncode(o.absolute_url()) )
        for o in objsByType.get('Report Feedback', []):
            res.append('<cr:hasFeedback rdf:resource="%s/%s"/>' % (RepUtils.xmlEncode(self.absolute_url()), o.id))
        res.append('<blockedByQA rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">%s</blockedByQA>' % repr(self.is_blocked).lower())

        return res

    security.declareProtected('View', 'get_custom_cobjs_rdf_meta')
    def get_custom_cobjs_rdf_meta(self):
        """Return custom child objects metadata for RDF export."""
        res = []
        objsByType = self._getObjectsForContentRegistry()

        for metatype, objs in objsByType.items():
            for o in objs:
                xmlChunk = []
                if metatype == 'Report Document':
                    try:
                        xmlChunk.append('<File rdf:about="%s">' % o.absolute_url())
                        xmlChunk.append('<rdfs:label>%s</rdfs:label>' % RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:title>%s</dct:title>' % RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dcat:byteSize>%s</dcat:byteSize>' % RepUtils.xmlEncode(o.data_file.size))
                        xmlChunk.append('<dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:issued>' % o.upload_time().HTML4())
                        xmlChunk.append('<dct:date rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:date>' % o.upload_time().HTML4())
                        xmlChunk.append('<dct:isPartOf rdf:resource="%s"/>' % RepUtils.xmlEncode(self.absolute_url()))
                        xmlChunk.append('<cr:mediaType>%s</cr:mediaType>' % o.content_type)
                        xmlChunk.append('<restricted rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">%s</restricted>' % repr(o.isRestricted()).lower())
                        if o.content_type == "text/xml":
                            for location in RepUtils.xmlEncode(o.xml_schema_location).split():
                                xmlChunk.append('<cr:xmlSchema rdf:resource="%s"/>' % location)
                        xmlChunk.append('</File>')
                    except:
                        xmlChunk = []
                elif metatype == 'Report Hyperlink':
                    try:
                        xmlChunk.append('<File rdf:about="%s">' % o.hyperlinkurl())
                        xmlChunk.append('<rdfs:label>%s</rdfs:label>' % RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:title>%s</dct:title>' % RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:issued>' % o.upload_time().HTML4())
                        xmlChunk.append('<dct:date rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:date>' % o.upload_time().HTML4())
                        xmlChunk.append('<dct:isPartOf rdf:resource="%s"/>' % RepUtils.xmlEncode(self.absolute_url()))
                        xmlChunk.append('</File>')
                    except:
                        xmlChunk = []
                elif metatype == 'Report Feedback':
                    try:
                        xmlChunk.append('<cr:Feedback rdf:about="%s">' % o.absolute_url())
                        xmlChunk.append('<rdfs:label>%s</rdfs:label>' % RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:title>%s</dct:title>' % RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:issued>' % o.postingdate.HTML4())
                        xmlChunk.append('<released rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</released>' % o.releasedate.HTML4())
                        xmlChunk.append('<dct:isPartOf rdf:resource="%s"/>' % RepUtils.xmlEncode(self.absolute_url()))
                        xmlChunk.append('<cr:feedbackStatus>%s</cr:feedbackStatus>' % RepUtils.xmlEncode(getattr(o, 'feedback_status', '')))
                        xmlChunk.append('<cr:feedbackMessage>%s</cr:feedbackMessage>' % RepUtils.xmlEncode(getattr(o, 'message', '')))
                        xmlChunk.append('<cr:mediaType>%s</cr:mediaType>' % o.content_type)
                        xmlChunk.append('<restricted rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">%s</restricted>' % repr(o.isRestricted()).lower())
                        if o.document_id not in [None, 'xml']:
                            xmlChunk.append('<cr:feedbackFor rdf:resource="%s/%s"/>' % (RepUtils.xmlEncode(self.absolute_url()),
                                    RepUtils.xmlEncode(url_quote(o.document_id)) ))
                        for attachment in o.objectValues(['File', 'File (Blob)']):
                            xmlChunk.append('<cr:hasAttachment rdf:resource="%s"/>' % attachment.absolute_url())
                        xmlChunk.append('</cr:Feedback>')
                        for attachment in o.objectValues(['File', 'File (Blob)']):
                            xmlChunk.append('<cr:FeedbackAttachment rdf:about="%s">' % attachment.absolute_url())
                            xmlChunk.append('<rdfs:label>%s</rdfs:label>' % RepUtils.xmlEncode(attachment.title_or_id()))
                            xmlChunk.append('<dct:title>%s</dct:title>' % RepUtils.xmlEncode(attachment.title_or_id()))
                            xmlChunk.append('<cr:mediaType>%s</cr:mediaType>' % attachment.content_type)
                            xmlChunk.append('<cr:attachmentOf rdf:resource="%s"/>' % o.absolute_url())
                            xmlChunk.append('</cr:FeedbackAttachment>')
                    except:
                        xmlChunk = []
                res.extend(xmlChunk)

        return res

    security.declareProtected('View', 'rdf')
    def rdf(self, REQUEST):
        """ Returns the envelope metadata in RDF format.
            This includes files and feedback objects.
            It is meant for triple stores, so there no point in returning
            anything until the envelope is released, because only released
            content should be indexed.
        """
        if not self.canViewContent():
            raise Unauthorized, "Envelope is not available"

        return BaseDelivery.rdf(self, REQUEST)

    @property
    def friendlypartofyear(self):
        return REPORTING_PERIOD_DESCRIPTION.get(self.partofyear)

    security.declareProtected('View', 'get_export_data')
    def get_export_data(self, format='xls'):
        """ Return data for export
        """
        env_data = BaseDelivery.get_export_data(self, format=format)
        if getSecurityManager().checkPermission('View', self):
            if format == 'xls':
                env_data.update({
                    'released': self.released,
                    'reported': self.reportingdate.strftime('%Y-%m-%d'),
                    'files': self.get_files_info(),
                })

        return env_data

    security.declareProtected('View', 'get_files_info')
    def get_files_info(self):
        files = []
        for fileObj in self.objectValues('Report Document'):
            files.append(fileObj.absolute_url_path())

        return files


    security.declareProtected('View', 'xls')
    def xls(self):
        """ xls export view
        """
        engine = getattr(self, ENGINE_ID)
        wb = xlwt.Workbook()
        sheet = wb.add_sheet('Envelope')
        filename = 'envelope-{0}.xls'.format(self.id)
        data = self.get_export_data()
        if data:
            header = dict(RepUtils.write_xls_header(sheet))
            RepUtils.write_xls_data(data, sheet, header, 1)

        return engine.download_xls(wb, filename)

    def has_dataflow(self, dataflow_uri):
        """Return True if dataflow_uri in envelope's dataflow_uris."""
        return dataflow_uri in self.dataflow_uris

    ##################################################
    # documents accepted status functions
    ##################################################

    security.declareProtected('Change Feedback', 'envelope_status')
    envelope_status = PageTemplateFile('zpt/envelope/statuses_section', globals())

    security.declareProtected('Change Feedback', 'envelope_status_bulk')
    envelope_status_bulk = PageTemplateFile('zpt/envelope/statusesbulk', globals())

    security.declareProtected('Change Feedback', 'getEnvelopeDocuments')
    def getEnvelopeDocuments(self, sortby='id', how='desc', start=1, howmany=10):
        """ """
        if how == 'desc': how = 0
        else:             how = 1
        objects = self.objectValues(['Report Document'])
        objects = RepUtils.utSortByAttr(objects, sortby, how)
        try: start = abs(int(start))
        except: start = 1
        try: howmany = abs(int(howmany))
        except: howmany = 10
        pginf = DiggPaginator(objects, howmany, body=5, padding=1, margin=2)
        if start<=0: start = 1
        if start>pginf.num_pages: start = pginf.num_pages
        pg = pginf.page(start)
        return {'total': pginf.count, 'num_pages': pginf.num_pages, 'pages': pg.page_range, 'start': pg.number,
            'start_index': pg.start_index(), 'end_index': pg.end_index(),
            'has_next': pg.has_next(), 'next_page_number': pg.next_page_number(),
            'has_previous': pg.has_previous(), 'previous_page_number': pg.previous_page_number(),
            'result': pg.object_list}

    security.declareProtected('Change Feedback', 'setAcceptTime')
    def setAcceptTime(self, ids='', sortby='id', how='desc', qs=1, size=20,  REQUEST=None):
        """ set accepted status """
        for k in self.getEnvelopeDocuments(sortby, how, qs, size)['result']:
            if k.id in ids: k.set_accept_time()
            else:           k.set_accept_time(0)
        if REQUEST: REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    def bulkAcceptTime(self, ids, action, REQUEST=None):
        """ """
        msg = {'info':{}, 'err':{}}

        for k in RepUtils.utConvertLinesToList(ids):
            doc = getattr(self, k, None)
            if doc == None:
                msg['err'][k] = 1
            else:
                if action == 'accept':
                    doc.set_accept_time()
                    msg['info'][k] = 'accept'
                else:
                    doc.set_accept_time(0)
                    msg['info'][k] = 'unaccept'

        if REQUEST:
            REQUEST.SESSION.set('msg', msg)
            REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected('View', 'has_permission')
    def has_permission(self, *args, **kwargs):
        return self.acquiredRolesAreUsedBy(*args, **kwargs)

    @property
    def Description(self):
        if isinstance(self.descr, unicode):
            return self.descr.encode('utf-8')

        return self.descr

# Initialize the class in order the security assertions be taken into account
Globals.InitializeClass(Envelope)

def movedEnvelope(ob, event):
    """ A Reportek Document was removed.
        If the attribute 'can_move_released' is found in a parent folder,
        and is true, then it it legal to move the envelope
    """
    if getattr(ob, 'can_move_released', False) == True:
        return
    if ob.released:
        raise Forbidden, "Envelope is released"


def copy_file_data(in_file, out_file):
    for chunk in RepUtils.iter_file_data(in_file):
        out_file.write(chunk)


def stream_response(response, data_file, attach_name, content_type):
    stat = os.fstat(data_file.fileno())
    response.setHeader('Content-Type', content_type)
    response.setHeader('Content-Disposition',
                       'attachment; filename="%s"' % attach_name)
    response.setHeader('Content-Length', stat[6])
    return filestream_iterator(data_file.name)
