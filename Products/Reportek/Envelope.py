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
from zipfile import *
import Globals, OFS.SimpleItem, OFS.ObjectManager
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl.Permissions import view_management_screens
import AccessControl.Role
from AccessControl import getSecurityManager, ClassSecurityInfo, Unauthorized
from Products.Reportek import permission_manage_properties_envelopes
from Products.PythonScripts.standard import url_quote
from zExceptions import Forbidden
from DateTime import DateTime
from DateTime.interfaces import SyntaxError
from ZPublisher.Iterators import filestream_iterator
import logging
logger = logging.getLogger("Reportek")

# Product specific imports
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
import transaction


ZIP_CACHE_THRESHOLD = 100000000 # 100 MB


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
    year_parts = ['Whole Year', 'First Half', 'Second Half',
                  'First Quarter', 'Second Quarter', 'Third Quarter',
                  'Fourth Quarter']
    months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    if not partofyear in (year_parts + months):
        raise InvalidPartOfYear

    ob = Envelope(process, title, actor, year, endyear, partofyear, self.country, locality, descr)
    ob.id = id
    self._setObject(id, ob)
    ob = self._getOb(id)
    ob.dataflow_uris = getattr(self,'dataflow_uris',[])   # Get it from collection
    if previous_delivery:
        l_envelope = self.restrictedTraverse(previous_delivery)
        l_data = l_envelope.manage_copyObjects(l_envelope.objectIds('Report Document'))
        ob.manage_pasteObjects(l_data)
    ob.startInstance(REQUEST)  # Start the instance
    if REQUEST is not None:
        return REQUEST.RESPONSE.redirect('manage_main')
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

class Envelope(EnvelopeInstance, EnvelopeRemoteServicesManager, EnvelopeCustomDataflows):
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

    def __init__(self, process, title, authUser, year, endyear, partofyear, country, locality, descr):
        """ Envelope constructor
        """
        self.year = year
        self.endyear = endyear
        self._check_year_range()
        self.title = title
        self.partofyear = partofyear
        self.country = country
        self.locality = locality
        self.descr = descr
        self.reportingdate = DateTime()
        self.released = 0
        # workflow part
        self.customer = authUser
        EnvelopeInstance.__init__(self, process)

    @property
    def is_blocked(self):
        """ Returns True if the last AutomaticQA workitem of the envelope has a blocker feedback """
        QA_workitems = [
            wi for wi in self.getMySelf().getListOfWorkitems()
               if wi.activity_id == 'AutomaticQA'
        ]
        if not QA_workitems:
            return False
        else:
            return getattr(QA_workitems[-1], 'blocker', False)

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

    def __setstate__(self,state):
        """ """
        Envelope.inheritedAttribute('__setstate__')(self, state)

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

    security.declareProtected('View', 'getObligations')
    def getObligations(self):
        lookup = self.ReportekEngine.dataflow_lookup
        return [(lookup(obl)['TITLE'], obl) for obl in self.dataflow_uris]

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
                    # if nore workitems are active for the current user, the overview is returned
                    l_no_active_workitems += 1
                    l_default_tab = w.id
        if l_no_active_workitems == 1:
            application = self.getPhysicalRoot().restrictedTraverse(l_application_url)
            params = {'workitem_id': l_default_tab,
                      'client': self,
                      'document_title': application.title,
                      'REQUEST': REQUEST,
                      'RESPONSE': REQUEST.RESPONSE
            }
            return self.getPhysicalRoot().restrictedTraverse(l_application_url)(**params)
        else:
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

    ##################################################
    # Manage period
    ##################################################

    def _check_year_range(self):
        """ Swap years if start bigger than end """
        if type(self.year) is types.IntType and type(self.endyear) is types.IntType:
            try:
                if self.year > self.endyear:
                    y = self.year
                    self.year = self.endyear
                    self.endyear = y
            except:
                pass

    security.declarePublic('years')
    def years(self):
        """ Return the range of years the object pertains to
        """
        if self.year == '':
            return ''
        if self.endyear == '':
            return [ self.year ]
        if int(self.year) > int(self.endyear):
            return range(int(self.endyear),int(self.year)+1)
        else:
            return range(int(self.year),int(self.endyear)+1)

    def getStartDate(self):
        """ returns the start date in DateTime format
            Returns None if there is no start date
        """
        if self.year:
            l_year = str(self.year)
            if self.partofyear in ['', 'Whole Year', 'First Half', 'First Quarter', 'January']:
                return DateTime(l_year + '/01/01')
            elif self.partofyear == 'February':
                return DateTime(l_year + '/02/01')
            elif self.partofyear == 'March':
                return DateTime(l_year + '/03/01')
            elif self.partofyear in ['April', 'Second Quarter']:
                return DateTime(l_year + '/04/01')
            elif self.partofyear == 'May':
                return DateTime(l_year + '/05/01')
            elif self.partofyear == 'June':
                return DateTime(l_year + '/06/01')
            elif self.partofyear in ['July', 'Third Quarter', 'Second Half']:
                return DateTime(l_year + '/07/01')
            elif self.partofyear == 'August':
                return DateTime(l_year + '/08/01')
            elif self.partofyear == 'September':
                return DateTime(l_year + '/09/01')
            elif self.partofyear in ['October', 'Fourth Quarter']:
                return DateTime(l_year + '/10/01')
            elif self.partofyear == 'November':
                return DateTime(l_year + '/11/01')
            elif self.partofyear == 'December':
                return DateTime(l_year + '/12/01')
        return None

    def getEndDate(self):
        endmonths = {
         '': '12-31',
         'Whole Year': '12/31',
         'First Half': '06/30',
         'Second Half': '12/31',
         'First Quarter': '03/31',
         'Second Quarter': '06/30',
         'Third Quarter': '09/30',
         'Fourth Quarter': '12/31',
         'January': '01/31',
         'February': '02/28', # Fix leap year?
         'March': '03/31',
         'April': '04/30',
         'May': '05/31',
         'June': '06/30',
         'July': '07/31',
         'August': '08/31',
         'September': '09/30',
         'October': '10/31',
         'November': '11/30',
         'December': '12/31'
        }
        if self.endyear != '':
            try:
                if self.endyear >= self.year:
                    return DateTime(str(self.endyear) + '/12/31')
            except:
                pass
        if self.year != '':
            startDT = self.getStartDate() # returns DateTime
            return DateTime(startDT.strftime('%Y/') + endmonths.get(self.partofyear,'12/31'))
        return None

    # Constructs periodical coverage from start/end dates
    def getPeriod(self):
        startDT = self.getStartDate()
        if startDT:
            startDate = startDT.strftime('%Y-%m-%d')
        else:
            return str(self.endyear)
        if self.endyear != '':
            try:
                if self.endyear > self.year:
                    return startDate + '/P' + str(self.endyear - self.year + 1) + 'Y'
                if self.endyear == self.year:
                    return startDate
            except:
                pass
        if self.partofyear in ['', 'Whole Year']:
            return startDate + '/P1Y'
        if self.partofyear in ['First Half', 'Second Half']:
            return startDate + '/P6M'
        if self.partofyear in ['First Quarter', 'Second Quarter', 'Third Quarter', 'Fourth Quarter']:
            return startDate + '/P3M'
        if self.partofyear in ['January', 'February', 'March', 'April',
          'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December' ]:
            return startDate + '/P1M'
        return startDate


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
                            action='./manage_main')

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
                            action='./manage_main')

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
        return hasThisPermission('Add Feedback', self) and self.released

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

    security.declareProtected('Add Feedback', 'manage_addFeedbackForm')
    manage_addFeedbackForm = Feedback.manage_addFeedbackForm
    security.declareProtected('Add Feedback', 'manage_addFeedback')
    manage_addFeedback = Feedback.manage_addFeedback
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

    def _get_zip_cache(self):
        zip_cache = path(CLIENT_HOME)/'zip_cache'
        if not zip_cache.isdir():
            zip_cache.mkdir()
        return zip_cache

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

        zip_cache = self._get_zip_cache()
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

        tmpfile = tempfile.NamedTemporaryFile(suffix='.temp', dir=zip_cache)

        try:
            outzd = ZipFile(tmpfile, "w", compression=ZIP_DEFLATED, allowZip64=True)

            for doc in public_docs:
                outzd.writestr(doc.getId(), doc.data_file.open().read())

            for fdbk in self.objectValues('Report Feedback'):
                if getSecurityManager().checkPermission('View', fdbk):
                    outzd.writestr('%s.html' % fdbk.getId(),
                                zip_content.get_feedback_content(fdbk))

                    for attachment in fdbk.objectValues(['File', 'File (Blob)']):
                        tmp_data = RepUtils.ofs_file_content_tmp(attachment)
                        outzd.write(tmp_data.name, attachment.getId())
                        tmp_data.close()

            #write feedback, metadata, README and history
            outzd.writestr('feedbacks.html', zip_content.get_feedback_list(self))
            outzd.writestr('metadata.txt', zip_content.get_metadata_content(self))
            outzd.writestr('README.txt', zip_content.get_readme_content(self))
            outzd.writestr('history.txt', zip_content.get_history_content(self))

        except:
            outzd.close()
            raise ValueError("An error occurred while preparing the zip file.")

        else:
            outzd.close()
            # only save cache file if greater than threshold
            if os.stat(tmpfile.name).st_size > ZIP_CACHE_THRESHOLD:
                os.link(tmpfile.name, cached_zip_path)

            tmpfile.seek(0)
            return stream_response(RESPONSE, tmpfile,
                                   response_zip_name, 'application/x-zip')

        finally:
            tmpfile.close()

    def _invalidate_zip_cache(self):
        """ delete zip cache files """
        zip_cache = self._get_zip_cache()
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
        id=name[max(string.rfind(name,'/'),
                  string.rfind(name,'\\'),
                  string.rfind(name,':')
                 )+1:]
        id = RepUtils.cleanup_id(id)
        self.manage_addDocument(id=id, title=id, file=zipfile, restricted=restricted)

    security.declareProtected('Add Envelopes', 'manage_addzipfile')
    def manage_addzipfile(self, file='', content_type='', restricted='', REQUEST=None):
        """ Expand a zipfile into a number of Documents.
            Go through the zipfile and for each file in there call
            self.manage_addProduct['Report Document'].manageaddDocument(id,...
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
                self._add_file_from_zip(zf,name, restricted)
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


    security.declareProtected('View', 'rdf')
    def rdf(self, REQUEST):
        """ Returns the envelope metadata in RDF format.
            This includes files and feedback objects.
            It is meant for triple stores, so there no point in returning
            anything until the envelope is released, because only released
            content should be indexed.
        """
        REQUEST.RESPONSE.setHeader('content-type', 'application/rdf+xml; charset=utf-8')
        if not self.canViewContent():
            raise Unauthorized, "Envelope is not available"

        objsByType = self._getObjectsForContentRegistry()
        res = []
        creator = self.getActorDraft()
        if not creator:
            creator = self.customer

        res.append('<?xml version="1.0" encoding="utf-8"?>')
        res.append('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        res.append(' xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
        res.append(' xmlns:dct="http://purl.org/dc/terms/"')
        res.append(' xmlns:cr="http://cr.eionet.europa.eu/ontologies/contreg.rdf#"')
        res.append(' xmlns="http://rod.eionet.europa.eu/schema.rdf#">')

        res.append('<Delivery rdf:about="%s">' % RepUtils.xmlEncode(self.absolute_url()))
        res.append('<rdfs:label>%s</rdfs:label>' % RepUtils.xmlEncode(self.title_or_id()))
        res.append('<dct:title>%s</dct:title>' % RepUtils.xmlEncode(self.title_or_id()))
        res.append('<dct:creator>%s</dct:creator>' % RepUtils.xmlEncode(creator))
        if self.descr:
             res.append('<dct:description>%s</dct:description>' % RepUtils.xmlEncode(self.descr))

        res.append('<released rdf:datatype="http://www.w3.org/2001/XMLSchema#dateTime">%s</released>' % self.reportingdate.HTML4())

        res.append('<link>%s</link>' % RepUtils.xmlEncode(self.absolute_url()))
        if self.country:
            res.append('<locality rdf:resource="%s" />' % self.country.replace('eionet.eu.int','eionet.europa.eu'))
        if self.locality != '':
            res.append('<coverageNote>%s</coverageNote>' % RepUtils.xmlEncode(self.locality))

        period = self.getPeriod()
        if period != '':
            res.append('<period>%s</period>' % period)

        startDT = self.getStartDate()
        if startDT:
            res.append('<startOfPeriod rdf:datatype="http://www.w3.org/2001/XMLSchema#date">%s</startOfPeriod>' % startDT.strftime('%Y-%m-%d'))

        endDT = self.getEndDate()
        if endDT:
            res.append('<endOfPeriod rdf:datatype="http://www.w3.org/2001/XMLSchema#date">%s</endOfPeriod>' % endDT.strftime('%Y-%m-%d'))

        for flow in self.dataflow_uris:
            res.append('<obligation rdf:resource="%s"/>' % RepUtils.xmlEncode(flow.replace('eionet.eu.int','eionet.europa.eu')))

        for o in objsByType.get('Report Document', []):
            res.append('<hasFile rdf:resource="%s"/>' % RepUtils.xmlEncode(o.absolute_url()) )
        for o in objsByType.get('Report Feedback', []):
            res.append('<cr:hasFeedback rdf:resource="%s/%s"/>' % (RepUtils.xmlEncode(self.absolute_url()), o.id))
        # In wich tag should we include this information??
        res.append('<blockedByQA rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">%s</blockedByQA>' % repr(self.is_blocked).lower())
        res.append('</Delivery>')
        for metatype, objs in objsByType.items():
            for o in objs:
                xmlChunk = []
                if metatype == 'Report Document':
                    try:
                        xmlChunk.append('<File rdf:about="%s">' % o.absolute_url())
                        xmlChunk.append('<rdfs:label>%s</rdfs:label>' % RepUtils.xmlEncode(o.title_or_id()))
                        xmlChunk.append('<dct:title>%s</dct:title>' % RepUtils.xmlEncode(o.title_or_id()))
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
                        xmlChunk.append('<cr:feedbackStatus>%s</cr:feedbackStatus>' % RepUtils.xmlEncode(o.feedback_status))
                        xmlChunk.append('<cr:feedbackMessage>%s</cr:feedbackMessage>' % RepUtils.xmlEncode(o.message))
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

        res.append('</rdf:RDF>')
        return '\n'.join(res)


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
