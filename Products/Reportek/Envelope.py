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

from ZPublisher.Iterators import filestream_iterator
from zope.lifecycleevent import ObjectModifiedEvent
from zope.interface import implements
from zope.event import notify
from zipstream import ZIP_DEFLATED, ZipFile
from zExceptions import Forbidden
from Products.Reportek.vocabularies import REPORTING_PERIOD_DESCRIPTION
from Products.Reportek.RepUtils import (DFlowCatalogAware, get_zip_cache,
                                        parse_uri)
from Products.Reportek.constants import DF_URL_PREFIX
from Products.Reportek.config import (DEPLOYMENT_BDR, REPORTEK_DEPLOYMENT,
                                      ZIP_CACHE_ENABLED,
                                      ZIP_CACHE_THRESHOLD,
                                      permission_manage_properties_envelopes)
from Products.Reportek.BaseDelivery import BaseDelivery
from Products.Reportek import (Document, Feedback, Hyperlink, RepUtils,
                               zip_content)
from Products.Reportek.events import (EnvelopeReleasedEvent,
                                      EnvelopeUnReleasedEvent)
from Products.PythonScripts.standard import url_quote
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from paginator import DiggPaginator, EmptyPage, InvalidPage
from interfaces import IEnvelope
from EnvelopeRemoteServicesManager import EnvelopeRemoteServicesManager
from EnvelopeInstance import EnvelopeInstance
from EnvelopeCustomDataflows import EnvelopeCustomDataflows
from DateTime.interfaces import SyntaxError
from DateTime import DateTime
from constants import ENGINE_ID, WORKFLOW_ENGINE_ID
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.Permissions import view_management_screens
from AccessControl import ClassSecurityInfo, Unauthorized
from zope.component import getMultiAdapter
from plone.protect.interfaces import IDisableCSRFProtection
import plone.protect.interfaces
from zope.interface import alsoProvides
import xlwt
import transaction
import OFS.SimpleItem
import OFS.ObjectManager
import Globals
import AccessControl.Role
from zipfile import BadZipfile
from exceptions import InvalidPartOfYear
import tempfile
import os
import logging
import json
__version__ = '$Revision$'[11:-2]


# Product specific imports

logger = logging.getLogger("Reportek")


def error_response(exc, message, REQUEST):
    """Return an error"""
    if REQUEST is not None:
        accept = REQUEST.environ.get("HTTP_ACCEPT")
        if accept == 'application/json':
            REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
            if hasattr(exc, '__name__'):
                error_type = exc.__name__
            else:
                error_type = str(exc)
            error = {
                'title': error_type,
                'description': message
            }
            data = {
                'errors': [error],
            }
            return json.dumps(data, indent=4)

    raise exc(message)


manage_addEnvelopeForm = PageTemplateFile('zpt/envelope/add', globals())


def manage_addEnvelope(self, title, descr, year, endyear, partofyear, locality,
                       REQUEST=None, previous_delivery='', metadata=None):
    """ Add a new Envelope object with id *id*.
    """
    id = RepUtils.generate_id('env')
    if 'IDisableCSRFProtection' in dir(plone.protect.interfaces):
        if REQUEST:
            alsoProvides(REQUEST,
                         plone.protect.interfaces.IDisableCSRFProtection)
    if not REQUEST:
        actor = self.REQUEST.AUTHENTICATED_USER.getUserName()
    else:
        actor = REQUEST.AUTHENTICATED_USER.getUserName()
    # finds the (a !) process suited for this envelope
    l_err_code, l_result = getattr(self, WORKFLOW_ENGINE_ID).findProcess(
        self.get_dataflow_uris(), self.country)
    if l_err_code == 0:
        process = self.unrestrictedTraverse(l_result, None)
    else:
        return error_response(l_result[0], l_result[1], REQUEST)

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
    for uri in self.get_dataflow_uris():
        if uri in engine.preliminary_obligations:
            preliminary_obl = True

    if year and year > now.year() and not preliminary_obl:
        if (REQUEST is not None
            and 'manage_addEnvelopeForm' in REQUEST.environ.get(
                "HTTP_REFERER")):
            error_msg = 'You cannot submit a report which relates to a future\
                         year. Please fill in the correct year!'
            return self.manage_addEnvelopeForm(error=error_msg)
        else:
            return error_response(
                ValueError,
                'Cannot create envelope which relates to a future year',
                REQUEST)

    year_parts = ['WHOLE_YEAR', 'FIRST_HALF', 'SECOND_HALF',
                  'FIRST_QUARTER', 'SECOND_QUARTER', 'THIRD_QUARTER',
                  'FOURTH_QUARTER']
    months = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
              "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]

    if partofyear and partofyear not in (year_parts + months):
        return error_response(InvalidPartOfYear,
                              'Invalid Part of Year', REQUEST)

    dataflow_uris = self.get_dataflow_uris()
    ob = Envelope(process, title, actor, year, endyear, partofyear,
                  self.country, locality, descr, dataflow_uris)
    ob.id = id
    # Get the restricted property from the parent collection
    self._setObject(id, ob)
    ob = self._getOb(id)
    if previous_delivery:
        l_envelope = self.restrictedTraverse(previous_delivery)
        l_data = l_envelope.manage_copyObjects(
            l_envelope.objectIds('Report Document'))
        ob.manage_pasteObjects(l_data)
    ob.startInstance(REQUEST)  # Start the instance
    if REQUEST is not None:
        if REQUEST.environ.get("HTTP_ACCEPT") == 'application/json':
            REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
            REQUEST.RESPONSE.setStatus(201)
            obls = [obl.split(DF_URL_PREFIX)[-1]
                    for obl in ob.dataflow_uris]
            env = {
                'url': ob.absolute_url(),
                'title': ob.title,
                'description': ob.descr,
                'countryCode': self.getCountryCode(ob.country),
                'isReleased': ob.released,
                'reportingDate': ob.reportingdate.HTML4(),
                'modifiedDate': ob.bobobase_modification_time().HTML4(),
                'obligations': obls,
                'periodStartYear': ob.year,
                'periodEndYear': ob.endyear,
                'periodDescription': REPORTING_PERIOD_DESCRIPTION.get(
                    ob.partofyear),
            }
            if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                metadata = ob.get_export_data()
                c_id = metadata.get('company_id')
                c_name = metadata.get('company')
                if c_id and c_name:
                    env['companyId'] = c_id
                    env['companyName'] = c_name
            data = {
                'envelopes': [env],
                'errors': [],
            }
            return json.dumps(data, indent=4)
        return REQUEST.RESPONSE.redirect(self.absolute_url())
    else:
        return ob.absolute_url()


def valid_year(year_str):
    try:
        year = int(year_str)  # Checks conversion
        DateTime('%s/01/01' % year)  # Raises SyntaxError below year 1000
        return True
    except ValueError as ex:
        return False
    except SyntaxError as ex:
        raise ex


def get_first_accept(req_dict):
    """ Figures out which type of content the webbrowser prefers
        If it is 'application/rdf+xml', then send RDF
    """
    s = req_dict.get_header('HTTP_ACCEPT', '*/*')
    segs = s.split(',')
    firstseg = segs[0].split(';')
    return firstseg[0].strip()


class Envelope(EnvelopeInstance, EnvelopeRemoteServicesManager,
               EnvelopeCustomDataflows, BaseDelivery, DFlowCatalogAware):
    """ Envelopes are basic container objects that provide a standard
        interface for object management. Envelope objects also implement
        a management interface
    """
    implements(IEnvelope)
    meta_type = 'Report Envelope'
    icon = 'misc_/Reportek/envelope.gif'

    # location of the file-repository
    _repository = ['reposit']

    security = ClassSecurityInfo()

    security.setPermissionDefault('Audit Envelopes', ('Manager', 'Owner'))

    manage_options = (
        (OFS.ObjectManager.ObjectManager.manage_options[0],) +
        (
            {'label': 'View', 'action': 'index_html',
                'help': ('OFSP', 'Envelope_View.stx')},
            {'label': 'Properties', 'action': 'manage_prop',
                'help': ('OFSP', 'Envelope_View.stx')},
        ) +
        EnvelopeInstance.manage_options +
        AccessControl.Role.RoleManager.manage_options +
        OFS.SimpleItem.Item.manage_options
    )

    security.declareProtected('Change Envelopes', 'manage_cutObjects')
    security.declareProtected('Change Envelopes', 'manage_copyObjects')
    security.declareProtected('Change Envelopes', 'manage_pasteObjects')
    security.declareProtected('Change Envelopes', 'manage_renameForm')
    security.declareProtected('Change Envelopes', 'manage_renameObject')
    security.declareProtected('Change Envelopes', 'manage_renameObjects')

    macros = PageTemplateFile('zpt/envelope/macros', globals()).macros

    def __init__(self, process, title, authUser, year, endyear, partofyear,
                 country, locality, descr, dataflow_uris=None):
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

    @property
    def is_audit_assigned(self):
        """Returns True if the envelope is assigned to an auditor"""
        return getattr(self, '_is_audit_assigned', False)

    @is_audit_assigned.setter
    def is_audit_assigned(self, value):
        """Set the is_audit_assigned status of the envelope."""
        self._is_audit_assigned = bool(value)

    @property
    def audit_info(self):
        """Returns short audit info if the envelope"""
        return getattr(self, '_audit_info', {})

    @audit_info.setter
    def audit_info(self, value):
        """Set the audit_info of the envelope."""
        self._audit_info = value

    def get_qa_feedbacks(self):
        """Return a list containing all AutomaticQA feedback objects."""
        return (rf for rf in self.objectValues('Report Feedback')
                if getattr(rf, 'title', '').startswith('AutomaticQA'))

    @property
    def has_unknown_qa_result(self):
        """ Returns True if an AutomaticQA feedback object has an 'UNKNOWN'
            feedback status. Every feedback_status other than the ones defined
            in VALID_FB_STATUSES is treated as 'UNKNOWN'.
        """
        VALID_FB_STATUSES = [
            'BLOCKER',
            'ERROR',
            'FAILED',
            'INFO',
            'OK',
            'REGERROR',
            'SKIPPED',
            'WARNING',
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
            'FAILED',
            'REGERROR'
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
            aqa_fbs = list(self.get_qa_feedbacks())
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

    def uns_notifications_are_on(self):
        return bool(os.environ.get('UNS_NOTIFICATIONS', 'off') == 'on')

    def has_blocker_feedback(self, REQUEST=None):
        """ web callable version of is_blocked """
        return self.is_blocked

    def is_acceptable(self):
        """ Returns acceptability status:
            True: definitly blocked
            False: definitely not blocked
            None: no completed AutomaticQA activity established if the
            envelope is blocked or not
        """
        if self.is_blocked:
            return False
        completed_automaticQA_workitems = (
            wi for wi in self.getMySelf().get_qa_workitems()
            if wi.status == 'complete')
        if next(completed_automaticQA_workitems, None):
            return True
        else:
            return None

    def all_meta_types(self, interfaces=None):
        """ Called by Zope to determine what kind of object the envelope can
            contain
        """
        y = [{'name': 'Report Document', 'action': 'manage_addDocumentForm',
              'permission': 'Add Envelopes'},
             {'name': 'Report Hyperlink', 'action': 'manage_addHyperlinkForm',
              'permission': 'Add Envelopes'},
             {'name': 'Report Feedback', 'action': 'manage_addFeedbackForm',
              'permission': 'Add Feedback'}]
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
        l_files_ids = l_envelope.objectIds(
            ['Report Document', 'Report Hyperlink'])
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
        if session and 'status_extra' in session.keys():
            session.delete('status_extra')
        status_extra = None
        browser_accept_type = get_first_accept(REQUEST)
        if browser_accept_type == 'application/rdf+xml':
            # The Linked Data guys want status 303
            REQUEST.RESPONSE.redirect(self.absolute_url() + '/rdf', status=303)
            return ''

        l_current_actor = REQUEST['AUTHENTICATED_USER'].getUserName()
        l_no_active_workitems = 0
        for w in self.getListOfWorkitems():
            if (w.status == 'active' and w.actor != 'openflow_engine'
                and (w.actor == l_current_actor
                     or getSecurityManager().checkPermission(
                        'Change Envelopes', self))):
                l_application_url = self.getApplicationUrl(w.id)
                if l_application_url:
                    # if more workitems are active for the current user,
                    # the overview is returned
                    l_no_active_workitems += 1
                    l_default_tab = w.id
        if l_no_active_workitems == 1:
            application = self.getPhysicalRoot().restrictedTraverse(
                l_application_url)
            params = {
                'workitem_id': l_default_tab,
                'REQUEST': REQUEST,
            }
            if isinstance(application, ZopePageTemplate):
                params['client'] = self
                params['document_title'] = application.title
                params['RESPONSE'] = REQUEST.RESPONSE
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

    def manage_main(self, *args, **kw):
        """ Define manage main to be context aware """

        if getSecurityManager().checkPermission('View management screens',
                                                self):
            return apply(self.manage_main_inh, (self,) + args, kw)
        else:
            # args is a tuple, the first element being the object instance,
            # the second the REQUEST
            if len(args) > 1:
                return apply(self.index_html, (args[1],))
            else:
                return apply(self.index_html, ())

    security.declareProtected('View', 'getDocuments')

    def getDocuments(self, REQUEST):
        """ return the list of documents """
        documents_list = self.objectValues(
            ['Report Document', 'Report Hyperlink'])
        documents_list.sort(key=lambda ob: ob.getId().lower())
        # Show 10 documents per page
        paginator = DiggPaginator(
            documents_list, 20, body=5, padding=2, orphans=5)

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
    documents_section = PageTemplateFile(
        'zpt/envelope/documents_section', globals())

    security.declareProtected('View', 'documents_pagination')
    documents_pagination = PageTemplateFile(
        'zpt/envelope/documents_pagination', globals())

    security.declareProtected('View', 'documents_management_section')
    documents_management_section = PageTemplateFile(
        'zpt/envelope/documentsmanagement_section', globals())

    security.declareProtected('View', 'feedback_section')
    feedback_section = PageTemplateFile(
        'zpt/envelope/feedback_section', globals())

    security.declareProtected('View', 'envelope_tabs')
    envelope_tabs = PageTemplateFile('zpt/envelope/tabs', globals())

    security.declareProtected('Change Envelopes', 'manage_prop')
    manage_prop = PageTemplateFile('zpt/envelope/properties', globals())

    security.declareProtected('Change Envelopes', 'envelope_previous')
    envelope_previous = PageTemplateFile(
        'zpt/envelope/earlierreleases', globals())

    security.declareProtected('View', 'data_quality')
    data_quality = PageTemplateFile('zpt/envelope/data_quality', globals())

    security.declareProtected('Use OpenFlow', 'get_current_workitem')

    def get_current_workitem(self, REQUEST=None):
        """ Return last workitem JSON metadata
        """
        wks = self.getListOfWorkitems()
        if wks:
            return self.handle_wk_response(wks[-1])
        if getattr(self, 'REQUEST'):
            if self.REQUEST.environ.get("HTTP_ACCEPT") == 'application/json':
                self.REQUEST.RESPONSE.setHeader('Content-Type',
                                                'application/json')
        return json.dumps({})

    security.declareProtected('Release Envelopes', 'content_registry_ping')

    def content_registry_ping(self, delete=False, async=False, wk=None,
                              silent=True):
        """ Instruct ReportekEngine to ping CR.

            `delete` instructs the envelope to don't ping CR on
            create or update but for delete.
            `async` tells it to do it async or not.

            Note that on delete, CR does not actually fetch envelope contents
            from CDR thus we can make the CR calls async even in that case
            when the envelope would not be available to the public anymore.
            Return a message with the state of the ping
        """

        engine = getattr(self, ENGINE_ID)
        crPingger = engine.contentRegistryPingger
        if not crPingger or self.restricted:
            logger.debug("Not pingging Content Registry.")
            return

        ping_argument = 'delete' if delete else 'create'
        # the main uri - the rdf listing everything inside
        uris = [self.absolute_url() + '/rdf']
        innerObjsByMetatype = self._getObjectsForContentRegistry()
        # ping CR for inner uris
        uris.extend(o.absolute_url()
                    for objs in innerObjsByMetatype.values() for o in objs)
        if async:
            crPingger.content_registry_ping_async(
                uris,
                ping_argument=ping_argument,
                envPathName=self.absolute_url(),
                wk=wk)
            message = "Async content registry ping requested"
        else:
            success, message = crPingger.content_registry_ping(
                uris, ping_argument=ping_argument, wk=wk)
            if not silent and not success:
                raise Exception('CR Ping failed! Please try again later!')

        return message

    ##################################################
    # Manage release status
    # The release-flag locks the envelope from getting new files.
    # It thereby prevents the clients from downloading incomplete envelopes.
    ##################################################
    security.declareProtected(view_management_screens,
                              'release_envelope_manual')

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
            self.reindexObject()
            self._invalidate_zip_cache()
            notify(ObjectModifiedEvent(self))
            notify(EnvelopeReleasedEvent(self))
        if self.REQUEST is not None:
            return self.messageDialog(
                message="The envelope has now been released to the public!",
                action='./manage_main')

    security.declareProtected(view_management_screens,
                              'unrelease_envelope_manual')

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
            self.reindexObject()
            transaction.commit()
            logger.debug("UNReleasing Envelope: %s" % self.absolute_url())
            notify(ObjectModifiedEvent(self))
            notify(EnvelopeUnReleasedEvent(self))
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
            for managing the dataflow by checking what is the next step in the
            dataflow process
        """
        return self.released

    ##################################################
    # Edit metadata
    ##################################################

    security.declareProtected(
        permission_manage_properties_envelopes, 'manage_editEnvelope')

    def manage_editEnvelope(self, title, descr,
                            year, endyear, partofyear, country, locality,
                            dataflow_uris=[], sync_process='', REQUEST=None):
        """ Manage the edited values
        """
        if not dataflow_uris:
            if not self.dataflow_uris:
                if REQUEST:
                    return self.messageDialog(
                        '''You must specify at least one obligation. '''
                        '''Settings not saved!''',
                        action='./manage_prop')
                return
        else:
            # If sync workflow is checked, change the workflow if required and
            # fallin to the first activity of the new workflow
            if sync_process == 'sync':
                wf_engine = self.unrestrictedTraverse(WORKFLOW_ENGINE_ID, None)
                if wf_engine:
                    obl_process = wf_engine.findProcess(dataflow_uris, country)
                    obl_process = self.unrestrictedTraverse(
                        obl_process[-1], None)
                    if (obl_process
                            and obl_process.absolute_url(
                                1) != self.process_path
                            and self.status != 'complete'):
                        self.setProcess(obl_process.absolute_url(1))
                        begin_act = obl_process.begin
                        wk = self.getListOfWorkitems()[-1]
                        self.falloutWorkitem(wk.id)
                        self.fallinWorkitem(wk.id, begin_act)
                        self.endFallinWorkitem(wk.id)

            self.dataflow_uris = dataflow_uris

        self.title = title
        try:
            self.year = int(year)
        except Exception:
            self.year = ''
        try:
            self.endyear = int(endyear)
        except Exception:
            self.endyear = ''
        self._check_year_range()
        self.partofyear = partofyear
        self.country = country
        self.locality = locality
        self.descr = descr
        # update ZCatalog
        self.reindexObject()
        notify(ObjectModifiedEvent(self))
        if REQUEST is not None:
            return self.messageDialog(
                message="The properties of %s have been changed!" % self.id,
                action='./')

    security.declareProtected(
        permission_manage_properties_envelopes, 'manage_changeEnvelope')

    def manage_changeEnvelope(self, title=None, descr=None,
                              year=None, endyear=None, country=None,
                              dataflow_uris=None, reportingdate=None,
                              REQUEST=None):
        """ Manage the changed values
        """
        if title is not None:
            self.title = title
        if year is not None:
            try:
                self.year = int(year)
            except Exception:
                self.year = ''
        if endyear is not None:
            try:
                self.endyear = int(endyear)
            except Exception:
                self.endyear = ''
        self._check_year_range()
        if country is not None:
            self.country = country
        if dataflow_uris is not None:
            self.dataflow_uris = dataflow_uris
        if reportingdate is not None:
            self.reportingdate = DateTime(reportingdate)
        if descr is not None:
            self.descr = descr
        # update ZCatalog
        self.reindexObject()
        notify(ObjectModifiedEvent(self))
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
        acquire = 0
        vr = list(self.valid_roles())
        if self.restricted:
            # If dealing with a restricted collection:
            #   - if acquire is 0, get the Roles with assigned View permission
            col = self.aq_parent
            if not col.acquiredRolesAreUsedBy('View'):
                # If the acquire is not set for collection, get the explicitly
                # set Roles with View Permission
                vr = [r.get('name') for r in col.rolesOfPermission('View')
                      if r.get('selected')]
        for item in ('Anonymous', 'Authenticated'):
            try:
                vr.remove(item)
            except Exception:
                pass
        return self._set_restrictions(ids, roles=vr, acquire=acquire,
                                      permission='View', REQUEST=REQUEST)

    security.declareProtected('Change Envelopes', 'apply_restrictions')

    def apply_restrictions(self):
        """ Apply restrictions to envelope's contents
        """
        ids = self.objectIds(['Report Document',
                              'Report Feedback',
                              'Report Hyperlink'])
        self.manage_restrict(ids)
        self.reindexObject()

    security.declareProtected('Change Envelopes', 'manage_unrestrict')

    def manage_unrestrict(self, ids=None, REQUEST=None):
        """
            Remove access restriction to the named objects.
        """
        # if this is called via HTTP, the list will just be a string
        if isinstance(ids, str):
            l_ids = ids[1:-1].split(', ')
            l_ids = [x[1:-1] for x in l_ids]
        else:
            l_ids = ids
        process = None
        restricted = []
        if getattr(self, 'process_path'):
            process = self.unrestrictedTraverse(self.process_path)
        else:
            # finds the (a !) process suited for this envelope
            l_err_code, l_result = getattr(
                self, WORKFLOW_ENGINE_ID).findProcess(
                self.dataflow_uris, self.country)
            if l_err_code == 0:
                process = self.unrestrictedTraverse(l_result, None)
        if not process:
            return error_response(ValueError,
                                  '''Unable to find the workflow associated '''
                                  '''with this envelope''', REQUEST)

        if (process.restricted
                and not getSecurityManager().checkPermission(
                    'View management screens', self)):
            for oid in l_ids:
                obj = self.unrestrictedTraverse(oid)
                m_types = [
                    'Report Document',
                    'Report Feedback',
                    'Report Hyperlink'
                ]
                if getattr(obj, 'meta_type', None) in m_types:
                    restricted.append(oid)
        if restricted:
            msg = ('''This is a restricted workflow, '''
                   '''unable to make objects public!''')
            l_ids = [oid for oid in l_ids if oid not in restricted]
            if l_ids:
                self._set_restrictions(
                    l_ids, roles=[], acquire=1, permission='View')
                msg = ('''This is a restricted workflow, some object '''
                       '''types restricted status have not been altered!''')
            return error_response(ValueError, msg, REQUEST)

        return self._set_restrictions(l_ids, roles=[], acquire=1,
                                      permission='View', REQUEST=REQUEST)

    security.declareProtected('Change Envelopes', 'restrict_editing_files')

    def restrict_editing_files(self, REQUEST=None):
        """
            Restrict permission to change files' content.
        """
        ids = self.objectIds('Document')
        vr = list(self.valid_roles())
        for item in ('Anonymous', 'Authenticated'):
            try:
                vr.remove(item)
            except Exception:
                pass
        return self._set_restrictions(ids, roles=vr, acquire=0,
                                      permission='Change Reporting Documents',
                                      REQUEST=REQUEST)

    security.declareProtected('Change Envelopes', 'unrestrict_editing_files')

    def unrestrict_editing_files(self, REQUEST=None):
        """
            Remove restriction to change files' content.
        """
        return self._set_restrictions(
            self.objectIds('Document'), roles=[], acquire=1,
            permission='Change Reporting Documents', REQUEST=REQUEST)

    def _set_restrictions(self, ids, roles=[], acquire=0,
                          permission='View', REQUEST=None):
        """
            Set access to the named objects.
            This basically finds the objects named in ids and
            calls the manage_permission on it.
        """
        if ids is None and REQUEST is not None:
            return self.messageDialog(
                message=('''You must select one or more items to '''
                         '''perform this operation.'''),
                action='manage_main')
        elif ids is None:
            raise ValueError('Ids must be specified')

        if isinstance(ids, str):
            ids = [ids]
        for id in ids:
            ob = self._getOb(id)
            ob.manage_permission(permission, roles=roles, acquire=acquire)
        if REQUEST is not None:
            return self.messageDialog(
                message="The files are now restricted!")

    security.declarePublic('areRestrictions')

    def areRestrictions(self):
        """ Returns 1 if at least a file is restricted from the public,
            0 otherwise
        """
        for doc in self.objectValues(['Report Document', 'Report Hyperlink']):
            if not doc.acquiredRolesAreUsedBy('View'):
                return 1
        return 0

    ##################################################
    # Determine various permissions - used in DTML
    ##################################################

    security.declarePublic('canViewContent')

    def canViewContent(self):
        """ Determine whether or not the content of the envelope can be seen
            by the current user
        """
        hasThisPermission = getSecurityManager().checkPermission
        return (hasThisPermission('Change Envelopes', self)
                or hasThisPermission('Release Envelopes', self)
                or hasThisPermission('Audit Envelopes', self)
                or hasThisPermission('Add Feedback', self)
                or self.released)

    security.declarePublic('canAddFiles')

    def canAddFiles(self):
        """ Determine whether or not the content of the envelope can be seen
            by the current user
        """
        hasThisPermission = getSecurityManager().checkPermission
        return (hasThisPermission('Change Envelopes', self)
                and not self.released)

    security.declarePublic('canAddFeedback')

    def canAddFeedback(self):
        """ Determine whether or not the current user can add manual feedback
        """
        hasThisPermission = getSecurityManager().checkPermission

        request = getattr(self, 'REQUEST', None)
        can_add_fb = False
        if request:
            session = getattr(request, 'SESSION', None)
            if session:
                can_add_fb = getattr(session,
                                     'can_add_feedback_before_release',
                                     False)

        return (hasThisPermission('Add Feedback', self)
                and (self.released or can_add_fb))

    security.declarePublic('canEditFeedback')

    def canEditFeedback(self):
        """ Determine whether or not the current user can edit existing manual
            feedback
        """
        hasThisPermission = getSecurityManager().checkPermission
        return hasThisPermission('Change Feedback', self) and self.released

    security.declarePublic('canChangeEnvelope')

    def canChangeEnvelope(self):
        """ Determine whether or not the current user can change the
            properties of the envelope
        """
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
                referred_file = '%s/%s' % (self.absolute_url(),
                                           item.document_id)
            else:
                referred_file = ''
            if 'qa-output' in item.objectIds():
                qa_output_url = '%s/qa-output' % item.absolute_url()
            else:
                qa_output_url = '%s' % item.absolute_url()
            result['feedbacks'].append(
                {
                    'title': item.title,
                    'releasedate': item.releasedate.HTML4(),
                    'isautomatic': item.automatic,
                    'content_type': item.content_type,
                    'referred_file': referred_file,
                    'qa_output_url': qa_output_url
                },
            )
        return result

    security.declareProtected('View', 'getFeedbackObjects')

    def getFeedbackObjects(self):
        """ return sorted feedbacks by their 'title' property, the manual
            feedback if always first
        """
        res = []
        feedback_list = self.getFeedbacks()
        manual_feedback = self.getManualFeedback()
        if manual_feedback:
            res.append(manual_feedback)
            auto_feedbacks = RepUtils.utSortByAttr(feedback_list, 'title')
            auto_feedbacks.remove(manual_feedback)
            res.extend(auto_feedbacks)
        else:
            res = RepUtils.utSortByAttr(feedback_list, 'title')
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

    # obsolete
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
        # Delete the feedbacks with fb_ids.
        self.manage_delObjects(fb_ids)

    @RepUtils.manage_as_owner
    def add_feedback(self, **kwargs):
        # Add feedback. To be called by Applications.
        self.manage_addFeedback(**kwargs)

    security.declareProtected('Add Feedback', 'manage_addFeedbackForm')
    manage_addFeedbackForm = Feedback.manage_addFeedbackForm
    security.declareProtected('Add Feedback', 'manage_addFeedback')
    manage_addFeedback = Feedback.manage_addFeedback
    security.declareProtected(
        'View management screens', 'manage_addManualQAFeedback')
    manage_addManualQAFeedback = Feedback.manage_addManualQAFeedback
    security.declareProtected('Add Feedback', 'manage_deleteFeedbackForm')
    manage_deleteFeedbackForm = PageTemplateFile(
        'zpt/feedback/delete', globals())

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
        # Verify access permissions
        self._check_zip_access(REQUEST)

        # Collect and categorize documents
        public_docs, restricted_docs = self._get_accessible_documents()

        # Determine zip type and filename based on document restrictions
        is_restricted = bool(restricted_docs)
        zip_type = 'all' if is_restricted else 'public'
        response_zip_name = self.getId() + (
            '-all.zip' if is_restricted else '.zip')

        # Try to get from cache first
        cached_response = self._get_cached_zip(
            zip_type, response_zip_name, RESPONSE)
        if cached_response:
            return cached_response

        # Create and return the zip file
        return self._create_zip_file(
            public_docs, zip_type, response_zip_name, RESPONSE)

    def _check_zip_access(self, REQUEST):
        """Verify user has permission to access the zip file."""
        if REQUEST.method == 'POST':
            # For POST requests, require CSRF protection
            if not IDisableCSRFProtection.providedBy(REQUEST):
                authenticator = getMultiAdapter(
                    (self, REQUEST), name=u"authenticator")
                if not authenticator.verify('envelope_zip'):
                    raise Unauthorized("Unable to verify authenticator")
        else:
            # For GET requests, explicitly check that the user is authenticated
            if REQUEST['AUTHENTICATED_USER'].getUserName() == 'Anonymous User':
                raise Unauthorized(
                    "Authentication required for this operation")

        # For both GET and POST, verify user can view the content
        if not self.canViewContent():
            raise Unauthorized("Envelope is not available")

    def _get_accessible_documents(self):
        """Return lists of accessible and restricted documents."""
        public_docs = []
        restricted_docs = []

        security_manager = getSecurityManager()
        for doc in self.objectValues('Report Document'):
            if security_manager.checkPermission('View', doc):
                public_docs.append(doc)
            else:
                restricted_docs.append(doc)

        return public_docs, restricted_docs

    def _get_cached_zip(self, zip_type, response_zip_name, RESPONSE):
        """Try to retrieve the zip file from cache."""
        zip_cache = get_zip_cache()
        envelope_path = '/'.join(self.getPhysicalPath())
        cache_key = zip_content.encode_zip_name(envelope_path, zip_type)
        cached_zip_path = zip_cache / cache_key

        if cached_zip_path.isfile():
            with cached_zip_path.open('rb') as data_file:
                return stream_response(
                    RESPONSE, data_file, response_zip_name,
                    'application/x-zip')
        return None

    def _create_zip_file(self, public_docs, zip_type, response_zip_name,
                         RESPONSE):
        """Create the zip file with documents and metadata."""
        zip_cache = get_zip_cache()
        envelope_path = '/'.join(self.getPhysicalPath())
        cache_key = zip_content.encode_zip_name(envelope_path, zip_type)
        cached_zip_path = zip_cache / cache_key

        with tempfile.NamedTemporaryFile(suffix='.temp', dir=zip_cache)\
                as tmpfile:
            with ZipFile(mode="w", compression=ZIP_DEFLATED, allowZip64=True)\
                    as outzd:
                try:
                    # Add document files to zip
                    self._add_documents_to_zip(outzd, public_docs)

                    # Add feedback files to zip
                    self._add_feedback_to_zip(outzd)

                    # Add metadata files to zip
                    self._add_metadata_to_zip(outzd)

                    # Write the zip data to the temporary file
                    for data in outzd:
                        tmpfile.write(data)

                except Exception as e:
                    raise ValueError(
                        'An error occurred while preparing '
                        'the zip file. {}'.format(str(e)))
                else:
                    # Save to cache if file is large enough
                    if (os.stat(tmpfile.name).st_size > ZIP_CACHE_THRESHOLD and
                            ZIP_CACHE_ENABLED):
                        os.link(tmpfile.name, cached_zip_path)

                    # Stream the response
                    tmpfile.seek(0)
                    return stream_response(
                        RESPONSE, tmpfile, response_zip_name,
                        'application/x-zip')

    def _add_documents_to_zip(self, zip_file, documents):
        """Add document files to the zip archive."""
        for doc in documents:
            zip_file.write_iter(
                doc.getId(),
                RepUtils.iter_file_data(doc.data_file.open())
            )

    def _add_feedback_to_zip(self, zip_file):
        """Add feedback content to the zip archive."""
        security_manager = getSecurityManager()

        for feedback in self.objectValues('Report Feedback'):
            if security_manager.checkPermission('View', feedback):
                # Add the feedback content as HTML
                zip_file.writestr(
                    '{}.html'.format(feedback.getId()),
                    zip_content.get_feedback_content(feedback)
                )

                # Add feedback attachments
                for attachment in feedback.objectValues(
                        ['File', 'File (Blob)']):
                    if attachment.meta_type == 'File (Blob)':
                        zip_file.write_iter(
                            attachment.getId(),
                            RepUtils.iter_file_data(
                                attachment.data_file.open())
                        )
                    else:
                        zip_file.write_iter(
                            attachment.getId(),
                            RepUtils.iter_ofs_file_data(attachment)
                        )

    def _add_metadata_to_zip(self, zip_file):
        """Add metadata files to the zip archive."""
        metadata = {
            'feedbacks.html': zip_content.get_feedback_list,
            'metadata.txt': zip_content.get_metadata_content,
            'README.txt': zip_content.get_readme_content,
            'history.txt': zip_content.get_history_content
        }

        for filename, content_generator in metadata.items():
            zip_file.writestr(filename, content_generator(self))

    def _invalidate_zip_cache(self):
        """ delete zip cache files """
        zip_cache = get_zip_cache()
        envelope_path = '/'.join(self.getPhysicalPath())
        for flag in ['public', 'all']:
            cache_key = zip_content.encode_zip_name(envelope_path, flag)
            cached_zip_path = zip_cache/cache_key
            if cached_zip_path.isfile():
                cached_zip_path.unlink()

    def _add_file_from_zip(self, zipfile, name, restricted=''):
        """ Generate id from filename and make sure,
            there are no spaces in the id.
        """
        id = self.cook_file_id(name)
        filename = getattr(zipfile, 'filename', None)
        if not filename:
            filename = id
        self.manage_addDocument(id=id, title=id, file=zipfile,
                                filename=filename, restricted=restricted)
        return id

    security.declareProtected('Add Envelopes', 'manage_addzipfile')

    def manage_addzipfile(self, file='', content_type='', restricted='',
                          REQUEST=None):
        """ Expands a zipfile into a number of Documents.
            Goes through the zipfile and calls manageaddDocument
            This function does not apply any special treatment to XML files,
            use manage_addDDzipfile for that
        """

        if not isinstance(file, str) and hasattr(file, 'filename'):
            # According to the zipfile.py ZipFile just needs a file-like object
            zf = zip_content.ZZipFileRaw(file)
            for name in zf.namelist():
                # test that the archive is not hierarhical
                if name[-1] == '/' or name[-1] == '\\':
                    return self.messageDialog(
                        message=('''The zip file you specified is '''
                                 '''hierarchical. It contains folders. '''
                                 '''Please upload a non-hierarchical '''
                                 '''structure of files.'''),
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
        # FIXME Why is application/octet-stream here? this might fix a glitch,
        # so we'll keep it for now
        if document.content_type in ['application/octet-stream',
                                     'application/zip',
                                     'application/x-compressed',
                                     'application/x-zip-compressed']:
            try:
                data_file = document.data_file.open()
                zf = zip_content.ZZipFile(data_file)
                for zipinfo in zf.infolist():
                    fname = zipinfo.filename
                    if isinstance(fname, unicode):
                        fname = fname.encode('utf-8')
                    files.append(fname)
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
            objByMetatype[t] = [o for o in self.objectValues(t)]
        return objByMetatype

    security.declareProtected('View', 'get_custom_rdf_meta')

    def get_custom_rdf_meta(self):
        """Return custom envelope type metadata for RDF export."""
        res = []
        creator = self.getActorDraft()
        if not creator:
            creator = self.customer
        res.append('<dct:creator>%s</dct:creator>' %
                   RepUtils.xmlEncode(creator))

    security.declareProtected('View', 'get_custom_delivery_rdf_meta')

    def get_custom_delivery_rdf_meta(self):
        """Return custom content type metadata for RDF export."""
        res = []
        objsByType = self._getObjectsForContentRegistry()
        creator = self.getActorDraft()
        engine = self.getEngine()
        http_res = getattr(engine, 'exp_httpres', False)
        if not creator:
            creator = self.customer

        res.append('<dct:creator>%s</dct:creator>' %
                   RepUtils.xmlEncode(creator))
        res.append('<released rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</released>' %  # noqa
                   self.reportingdate.HTML4())
        res.append('<link>%s</link>' %
                   RepUtils.xmlEncode(parse_uri(self.absolute_url(),
                                                http_res)))

        for o in objsByType.get('Report Document', []):
            res.append('<hasFile rdf:resource="%s"/>' %
                       RepUtils.xmlEncode(parse_uri(o.absolute_url(),
                                                    http_res)))
        for o in objsByType.get('Report Feedback', []):
            res.append('<cr:hasFeedback rdf:resource="%s/%s"/>' %
                       (RepUtils.xmlEncode(
                        parse_uri(self.absolute_url(), http_res)), o.id))
        res.append('<blockedByQA rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">%s</blockedByQA>' %  # noqa
                   repr(self.is_blocked).lower())

        return res

    security.declareProtected('View', 'get_custom_cobjs_rdf_meta')

    def get_custom_cobjs_rdf_meta(self):
        """Return custom child objects metadata for RDF export."""
        res = []
        objsByType = self._getObjectsForContentRegistry()
        engine = self.getEngine()
        http_res = getattr(engine, 'exp_httpres', False)
        for metatype, objs in objsByType.items():
            for o in objs:
                xmlChunk = []
                if metatype == 'Report Document':
                    try:
                        xmlChunk.append('<File rdf:about="%s">' %
                                        parse_uri(o.absolute_url(), http_res))
                        xmlChunk.append('<rdfs:label>%s</rdfs:label>' %
                                        RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:title>%s</dct:title>' %
                                        RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dcat:byteSize>%s</dcat:byteSize>' %
                                        RepUtils.xmlEncode(o.data_file.size))
                        xmlChunk.append(
                            '<dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:issued>' % o.upload_time().HTML4())  # noqa
                        xmlChunk.append(
                            '<dct:date rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:date>' % o.upload_time().HTML4())  # noqa
                        xmlChunk.append('<dct:isPartOf rdf:resource="%s"/>' %
                                        RepUtils.xmlEncode(
                                            parse_uri(self.absolute_url(),
                                                      http_res)))
                        xmlChunk.append('<cr:mediaType>%s</cr:mediaType>' %
                                        RepUtils.xmlEncode(o.content_type))
                        xmlChunk.append(
                            '<restricted rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">%s</restricted>' % repr(o.isRestricted()).lower())  # noqa
                        if o.content_type == "text/xml":
                            for location in RepUtils.xmlEncode(
                                    o.xml_schema_location).split():
                                xmlChunk.append(
                                    '<cr:xmlSchema rdf:resource="%s"/>' % location)  # noqa
                        xmlChunk.append('</File>')
                    except Exception:
                        xmlChunk = []
                elif metatype == 'Report Hyperlink':
                    try:
                        xmlChunk.append('<File rdf:about="%s">' %
                                        o.hyperlinkurl())
                        xmlChunk.append('<rdfs:label>%s</rdfs:label>' %
                                        RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:title>%s</dct:title>' %
                                        RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append(
                            '<dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:issued>' % o.upload_time().HTML4())  # noqa
                        xmlChunk.append(
                            '<dct:date rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:date>' % o.upload_time().HTML4())  # noqa
                        xmlChunk.append('<dct:isPartOf rdf:resource="%s"/>' %
                                        RepUtils.xmlEncode(
                                            parse_uri(self.absolute_url(),
                                                      http_res)))
                        xmlChunk.append('</File>')
                    except Exception:
                        xmlChunk = []
                elif metatype == 'Report Feedback':
                    try:
                        xmlChunk.append('<cr:Feedback rdf:about="%s">' %
                                        parse_uri(o.absolute_url(), http_res))
                        xmlChunk.append('<rdfs:label>%s</rdfs:label>' %
                                        RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:title>%s</dct:title>' %
                                        RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append(
                            '<dct:issued rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</dct:issued>' % o.postingdate.HTML4())  # noqa
                        xmlChunk.append(
                            '<released rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</released>' % o.releasedate.HTML4())  # noqa
                        xmlChunk.append('<dct:isPartOf rdf:resource="%s"/>' %
                                        RepUtils.xmlEncode(
                                            parse_uri(self.absolute_url(),
                                                      http_res)))
                        xmlChunk.append('<cr:feedbackStatus>%s</cr:feedbackStatus>' %  # noqa
                                        RepUtils.xmlEncode(
                                            getattr(o, 'feedback_status', '')))
                        xmlChunk.append('<cr:feedbackMessage>%s</cr:feedbackMessage>' %  # noqa
                                        RepUtils.xmlEncode(
                                            getattr(o, 'message', '')))
                        xmlChunk.append('<cr:mediaType>%s</cr:mediaType>' %
                                        RepUtils.xmlEncode(o.content_type))
                        xmlChunk.append(
                            '<restricted rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">%s</restricted>' % repr(o.isRestricted()).lower())  # noqa
                        if o.document_id and o.document_id != 'xml':
                            xmlChunk.append('<cr:feedbackFor rdf:resource="%s/%s"/>' % (RepUtils.xmlEncode(parse_uri(self.absolute_url(), http_res)),  # noqa
                                                                                        RepUtils.xmlEncode(url_quote(o.document_id))))  # noqa
                        for attachment in o.objectValues(['File',
                                                          'File (Blob)']):
                            xmlChunk.append('<cr:hasAttachment rdf:resource="%s"/>' %  # noqa
                                            parse_uri(
                                                attachment.absolute_url(),
                                                http_res))
                        xmlChunk.append('</cr:Feedback>')
                        for attachment in o.objectValues(['File',
                                                          'File (Blob)']):
                            xmlChunk.append('<cr:FeedbackAttachment rdf:about="%s">' % parse_uri(  # noqa
                                attachment.absolute_url(), http_res))
                            xmlChunk.append('<rdfs:label>%s</rdfs:label>' %
                                            RepUtils.xmlEncode(
                                                attachment.title_or_id()))
                            xmlChunk.append('<dct:title>%s</dct:title>' %
                                            RepUtils.xmlEncode(
                                                attachment.title_or_id()))
                            xmlChunk.append(
                                '<cr:mediaType>%s</cr:mediaType>' % RepUtils.xmlEncode(attachment.content_type))  # noqa
                            xmlChunk.append(
                                '<cr:attachmentOf rdf:resource="%s"/>' % parse_uri(o.absolute_url(), http_res))  # noqa
                            xmlChunk.append('</cr:FeedbackAttachment>')
                    except Exception:
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
            raise Unauthorized("Envelope is not available")

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
                engine = getattr(self, ENGINE_ID)
                domain = engine.get_df_domain(
                    self.dataflow_uris, 'undertakings')
                if domain == 'FGAS':
                    acts = self.get_pretty_activities()
                    gases = self.get_fgas_reported_gases()
                    gas_tmpl = (u"Gas name: {}\n"
                                "Gas ID: {}\n"
                                "Gas Group: {}\n"
                                "Gas Group ID: {}\n\n"
                                )
                    pretty_gases = ''

                    def parse_gas_data(data):
                        if not data:
                            data = 'N/A'
                        return data

                    if gases:
                        pretty_gases = ''.join(
                            [gas_tmpl.format(parse_gas_data(g.get('Name')),
                             parse_gas_data(
                                g.get('GasId')),
                             parse_gas_data(
                                g.get('GasGroup')),
                             parse_gas_data(g.get('GasGroupId')))
                             for g in gases])
                    if not acts:
                        acts = ''
                    else:
                        acts = ', '.join(self.get_pretty_activities())
                    env_data.update({
                        'activities': acts,
                        'gases': pretty_gases,
                        'i_authorisations': str(
                            self.get_fgas_i_authorisations()),
                        'a_authorisations': str(
                            self.get_fgas_a_authorisations())
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
    envelope_status = PageTemplateFile(
        'zpt/envelope/statuses_section', globals())

    security.declareProtected('Change Feedback', 'envelope_status_bulk')
    envelope_status_bulk = PageTemplateFile(
        'zpt/envelope/statusesbulk', globals())

    security.declareProtected('Change Feedback', 'getEnvelopeDocuments')

    def getEnvelopeDocuments(self, sortby='id', how='desc', start=1,
                             howmany=10):
        """ """
        if how == 'desc':
            how = 0
        else:
            how = 1
        objects = self.objectValues(['Report Document'])
        objects = RepUtils.utSortByAttr(objects, sortby, how)
        try:
            start = abs(int(start))
        except Exception:
            start = 1
        try:
            howmany = abs(int(howmany))
        except Exception:
            howmany = 10
        pginf = DiggPaginator(objects, howmany, body=5, padding=1, margin=2)
        if start <= 0:
            start = 1
        if start > pginf.num_pages:
            start = pginf.num_pages
        pg = pginf.page(start)
        return {'total': pginf.count, 'num_pages': pginf.num_pages,
                'pages': pg.page_range, 'start': pg.number,
                'start_index': pg.start_index(), 'end_index': pg.end_index(),
                'has_next': pg.has_next(),
                'next_page_number': pg.next_page_number(),
                'has_previous': pg.has_previous(),
                'previous_page_number': pg.previous_page_number(),
                'result': pg.object_list}

    security.declareProtected('Change Feedback', 'setAcceptTime')

    def setAcceptTime(self, ids='', sortby='id', how='desc', qs=1, size=20,
                      REQUEST=None):
        """ set accepted status """
        for k in self.getEnvelopeDocuments(sortby, how, qs, size)['result']:
            if k.id in ids:
                k.set_accept_time()
            else:
                k.set_accept_time(0)
        if REQUEST:
            REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    def bulkAcceptTime(self, ids, action, REQUEST=None):
        """ """
        msg = {'info': {}, 'err': {}}

        for k in RepUtils.utConvertLinesToList(ids):
            doc = getattr(self, k, None)
            if doc is None:
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
    if getattr(ob, 'can_move_released', False) is True:
        return
    if ob.released:
        raise Forbidden("Envelope is released")


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
