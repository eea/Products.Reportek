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

__doc__ = """
      Engine for the Reportek Product
      Keeps all the global settings and implements administrative functions for the entire site
      Added in the Root folder by product's __init__
"""

from path import path
import tempfile
import os
from zipfile import *
from urlparse import urlparse

# Zope imports
from OFS.Folder import Folder
from OFS.ObjectManager import ObjectManager
from AccessControl import getSecurityManager, ClassSecurityInfo
from AccessControl.Permissions import view_management_screens, view
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Globals import DTMLFile
from App.config import getConfiguration
import Globals
import Products
import xmlrpclib
from DateTime import DateTime
from time import time, strftime
from copy import copy

# product imports
import constants
from Products.Reportek.constants import DEFAULT_CATALOG
import RepUtils
from Toolz import Toolz
from DataflowsManager import DataflowsManager
from CountriesManager import CountriesManager
from paginator import DiggPaginator, EmptyPage, InvalidPage
from zope.interface import implements
from interfaces import IReportekEngine

class ReportekEngine(Folder, Toolz, DataflowsManager, CountriesManager):
    """ Stores generic attributes for Reportek """

    implements(IReportekEngine)
    meta_type = 'Reportek Engine'
    icon = 'misc_/Reportek/Converters'

    security = ClassSecurityInfo()

    manage_options = ( ({'label':'View', 'action': 'index_html'}, ) +\
        ({'label':'Properties', 'action': 'manage_properties'}, ) +\
        ({'label':'UNS settings', 'action': 'uns_settings'}, ) +\
        Folder.manage_options[3:-1]
    )

    _properties = ({'id':'title', 'type':'string', 'mode':'w', 'label':'Title'},
            {'id':'webq_url', 'type':'string', 'mode':'w'},
            {'id':'webq_envelope_menu', 'type':'string', 'mode':'w'},
            {'id':'webq_before_edit_page', 'type':'string', 'mode':'w'}
    )

    def all_meta_types( self, interfaces=None ):
        """
            What can you put inside me? Checks if the legal products are
            actually installed in Zope
        """
        types = ['Script (Python)', 'DTML Method', 'DTML Document', 'Page Template']

        l_result = []
        for l_type in Products.meta_types:
            if l_type['name'] in types:
                l_result.append(l_type)
        return l_result

    def __init__(self, webq_url=''):
        """ constructor """
        self.id = constants.ENGINE_ID
        # The URL to the WebQ XML-RPC server
        # Empty means no WebQ available
        self.webq_url = 'http://cdr.eionet.europa.eu/webq/RpcRouter'
        # The URL to the WebQ page which constructs a menu for a specified envelope
        # called via HTTP GET
        self.webq_envelope_menu = 'http://cdr.eionet.europa.eu/webq/WebQMenu'
        # The URL to the WebQ webpage, before the user starts to use the edit form. 
        # The purpose is to ask the capabilities of the user webbrowser
        # and what language the form should be in.
        # called via HTTP GET
        self.webq_before_edit_page = 'http://cdr.eionet.europa.eu/webq/WebQEdit'
        # UNS configuration parameters
        self.UNS_server = ''
        self.UNS_username = ''
        self.UNS_password = ''
        self.UNS_channel_id = ''
        self.UNS_notification_types = ['Envelope release', 'Envelope revoke']
        #self.UNS_notification_types = ['Envelope complete', 'Envelope release', 'Manual feedback posted', 'Quality assessment finished']
        # The default QA application used for manual and automatic triggered QA operation
        # If this is empty, this Reportek instance does not have a QA system linked to it
        self.QA_application = ''

    security.declareProtected(view_management_screens, 'index_html')
    index_html = PageTemplateFile('zpt/engine_index', globals())

    def __setstate__(self,state):
        """ """
        ReportekEngine.inheritedAttribute('__setstate__')(self, state)
        if not hasattr(self, 'UNS_server'):
            self.UNS_server = 'http://uns.eionet.europa.eu'
        if not hasattr(self, 'UNS_username'):
            self.UNS_username = 'cdr'
        if not hasattr(self, 'UNS_password'):
            self.UNS_password = 'reportnet'
        if not hasattr(self, 'UNS_channel_id'):
            self.UNS_channel_id = ''
        if not hasattr(self, 'UNS_notification_types'):
            #self.UNS_notification_types = ['Envelope complete', 'Envelope release', 'Envelope revoke', 'Manual feedback posted', 'Quality assessment finished']
            self.UNS_notification_types = ['Envelope release', 'Envelope revoke']
        if not hasattr(self, 'QA_application'):
            self.QA_application = ''

    #security stuff
    security = ClassSecurityInfo()

    security.declareProtected(view_management_screens, 'manage_properties')
    manage_properties = DTMLFile('dtml/engineProp', globals())

    security.declareProtected(view_management_screens, 'manage_editEngine')
    def manage_editEngine(self, title='', webq_url='', webq_envelope_menu='', webq_before_edit_page='', QA_application='', REQUEST=None):
        """ Manage the edited values """
        self.title = title
        self.webq_url = webq_url
        self.webq_envelope_menu = webq_envelope_menu
        self.webq_before_edit_page = webq_before_edit_page
        self.QA_application = QA_application
        if REQUEST:
            message="Properties changed"
            return self.manage_properties(self,REQUEST,manage_tabs_message=message)

    security.declarePublic('getPartsOfYear')
    def getPartsOfYear(self):
        """ """
        return ['','Whole Year', 'First Half', 'Second Half',
           'First Quarter', 'Second Quarter', 'Third Quarter', 'Fourth Quarter',
           'January','February','March','April', 'May','June','July','August','September','October','November','December']

    security.declareProtected(view_management_screens, 'change_ownership')
    def change_ownership(self, obj, newuser, deluser):
        """ """
        owner = obj.getOwner()   #get the actual owner
        if str(owner) == deluser.strip():
            owners = RepUtils.utConvertToList(owner.getId())
            user = self.acl_users.getUser(newuser)
            wrapped_user = user.__of__(self.acl_users)
            if wrapped_user:
                obj.changeOwnership(wrapped_user)   #change ownership
                obj.manage_delLocalRoles(owners)    #delete the old owner
                obj.manage_setLocalRoles(wrapped_user.getId(),['Owner',])   #set local role to the new user

    security.declareProtected('View', 'macros')
    macros = PageTemplateFile('zpt/engineMacros', globals()).macros

    security.declareProtected('View', 'globalworklist')
    globalworklist = PageTemplateFile('zpt/engineGlobalWorklist', globals())

    security.declareProtected(view_management_screens, 'countryreporters')
    countryreporters = PageTemplateFile('zpt/engineCountryReporters', globals())

    security.declareProtected('View', 'searchfeedbacks')
    searchfeedbacks = PageTemplateFile('zpt/engineSearchFeedbacks', globals())

    security.declareProtected('View', 'resultsfeedbacks')
    resultsfeedbacks = PageTemplateFile('zpt/engineResultsFeedbacks', globals())

    security.declareProtected('View', 'recent')
    recent = PageTemplateFile('zpt/engineRecentUploads', globals())

    security.declareProtected('View', 'searchdataflow')
    searchdataflow = PageTemplateFile('zpt/engineSearchByObligation', globals())

    security.declareProtected('View', 'resultsdataflow')
    resultsdataflow = PageTemplateFile('zpt/engineSearchByObligationResults', globals())

    security.declareProtected('View', 'searchxml')
    searchxml = PageTemplateFile('zpt/engineSearchXml', globals())

    security.declareProtected('View', 'resultsxml')
    resultsxml = PageTemplateFile('zpt/engineResultsXml', globals())

    security.declareProtected(view_management_screens, 'Assign_client_form')
    Assign_client_form = PageTemplateFile('zpt/engineAssignClientForm', globals())

    security.declareProtected('View', 'Remove_client')
    def Remove_client(self, REQUEST=None, **kwargs):
        if REQUEST:
            kwargs.update(REQUEST.form)

        query = {
          'dataflow_uris': kwargs.get('cobligation', ''),
          'meta_type': 'Report Collection',
        }

        catalog = self.Catalog
        brains = catalog(**query)

        crole = kwargs.get('crole')
        countries = kwargs.get('ccountries', [])
        res = []
        for brain in brains:
            doc = brain.getObject()
            try:
                country = doc.getCountryCode()
            except KeyError:
                continue
            if country.lower() not in countries:
                continue
            for user in kwargs.get('dns', []):
                local_roles = [role for role in doc.get_local_roles_for_userid(user) if role != 'Client']
                doc.manage_delLocalRoles(userids=[user,])
                local_roles.remove(crole)
                if local_roles:
                    doc.manage_setLocalRoles(user, local_roles)
            res.append(doc)
        return res


    security.declareProtected('View', 'Assign_client')
    def Assign_client(self, REQUEST=None, **kwargs):
        if REQUEST:
            kwargs.update(REQUEST.form)

        crole = kwargs.get('crole','Client')
        query = {
          'dataflow_uris': kwargs.get('cobligation', ''),
          'meta_type': 'Report Collection',
        }

        catalog = self.Catalog
        brains = catalog(**query)

        countries = kwargs.get('ccountries', [])
        res = []
        for brain in brains:
            doc = brain.getObject()
            try:
                country = doc.getCountryCode()
            except KeyError:
                continue
            if country.lower() not in countries:
                continue
            for user in kwargs.get('dns', []):
                local_roles = [role for role in doc.get_local_roles_for_userid(user) if role != 'Client']
                local_roles.append(crole)
                doc.manage_setLocalRoles(user, local_roles)
            res.append(doc)
        return res


    security.declareProtected('View', 'getCountriesList')
    def getCountriesList(self):
        """ """
        l_countries = self.getParentNode().objectValues('Report Collection')
        return RepUtils.utSortByAttr(l_countries, 'title')

    security.declareProtected('View', 'getCountryByTitle')
    def getCountryByTitle(self, p_title):
        """ """
        for k in self.getCountriesList():
            if k.title_or_id() == p_title: return k

    security.declareProtected('View', 'getReportersByCountry')
    def getReportersByCountry(self, p_context, p_role):
        """ """
        reporters = {}
        try:    l_context = self.unrestrictedTraverse(p_context)
        except: return reporters
        for k in l_context.get_local_roles():
            if p_role in k[1]: reporters[k[0]] = p_role
        for k in l_context.objectValues('Report Collection'):
            reporters.update(self.getReportersByCountry(k.absolute_url(1), p_role))
        return reporters

    security.declareProtected('View', 'sitemap')
    sitemap = DTMLFile('dtml/engineSitemap', globals())

    security.declarePublic('getWebQURL')
    def getWebQURL(self):
        """ return '' if there's no WebQuestionnaire attached to this application """
        return self.webq_url

    def getNotCompletedWorkitems(self, sortby, how, REQUEST=None):
        """ Loops for all the workitems that are in the 'active','inactive','fallout' status
            and returns their list
        """
        catalog = getattr(self, constants.DEFAULT_CATALOG)

        query = {
            'meta_type':'Workitem',
            'status':['active','inactive','fallout'],
            'sort_on':sortby
            }

        if how == 'desc':
            query['sort_order'] = 'reverse'

        workitems = catalog(**query)

        if REQUEST is None:
            return [ob.getObject() for ob in workitems]

        else:
            paginator = DiggPaginator(workitems, 20, body=5, padding=2, orphans=5)

            try:
                page = int(REQUEST.get('page', '1'))
            except ValueError:
                page = 1

            try:
                workitems = paginator.page(page)
            except (EmptyPage, InvalidPage):
                workitems = paginator.page(paginator.num_pages)

            workitems.object_list = [ob.getObject() for ob in workitems.object_list]
            return workitems

    security.declareProtected(view_management_screens, 'filterNotCompletedWorkitems')
    def filterNotCompletedWorkitems(self, REQUEST=None, **kwargs):
        """ Filter not completed workitems by given filters
        """
        if REQUEST:
            kwargs.update(REQUEST.form)
        status = kwargs.get('status', '')
        obligation = kwargs.get('obligation', '')
        
        catalog = getattr(self, DEFAULT_CATALOG, None)
        if not catalog:
            return
        query = {
            'meta_type':'Workitem',
            'status':['active','inactive'],
            'sort_on': 'reportingdate',
            'sort_order': 'reverse',
        }
        brains = catalog(**query)
        try:
            age = int(kwargs.get('age', 0))
        except (TypeError, ValueError):
            age = 0
        now = DateTime()
        now = now - age
        for brain in brains:
            doc = brain.getObject()
            # Filter by status
            if status and not doc.status == status:
                continue
            # Filter by obligation
            if obligation and obligation not in doc.dataflow_uris:
                continue
            # Filter by age
            doc_time = doc.reportingdate
            if doc_time.greaterThan(now):
                continue
            # Filter inactive Drafts
            if doc.getActivityDetails('title') == 'Draft' and doc.status == 'inactive':
                continue
            yield doc
    
    security.declareProtected(view_management_screens, 'autoCompleteEnvelopes')
    def autoCompleteEnvelopes(self, REQUEST=None, **kwargs):
        """ Run autocomplete process
        """
        if REQUEST:
            kwargs.update(REQUEST.form)
        ids = kwargs.get('ids', [])
        task = kwargs.get('task', '')
        for path in ids:
            workitem = self.unrestrictedTraverse(path, None)
            if not workitem:
                continue
            if task and workitem.getActivityDetails('title') != task:
                continue
            envelope = workitem.getParentNode()
            workitem_id = workitem.getId()
            # Activate inactive workitem
            if workitem.status == 'inactive':
                envelope.activateWorkitem(workitem_id)
            # Complete envelope
            envelope.completeWorkitem(workitem_id, REQUEST=REQUEST)
            yield envelope

    security.declareProtected(view_management_screens, 'envelopes_autocomplete')
    envelopes_autocomplete = PageTemplateFile('zpt/envelopes_autocomplete', globals())

    def zipEnvelopes(self, envelopes=[], REQUEST=None, RESPONSE=None):
        """ Zip several envelopes together with the metadata """
        import zip_content

        envelopes = RepUtils.utConvertToList(envelopes)

        temp_dir = path(CLIENT_HOME)/'zip_cache'
        if not temp_dir.isdir():
            temp_dir.mkdir()
        tmpfile = tempfile.mktemp(".temp", dir=str(temp_dir))

        if len(envelopes) == 0:
            return

        #get envelopes
        env_objs = [ self.unrestrictedTraverse(env, None) for env in envelopes ]

        outzd = ZipFile(tmpfile, "w", ZIP_DEFLATED)

        for env_ob in env_objs:
            if env_ob is None:
                continue

            if env_ob.released:
                env_name = env_ob.title
                for doc in env_ob.objectValues('Report Document'):
                    if getSecurityManager().checkPermission(view, doc):
                        with doc.data_file.open() as doc_file:
                            tmp_copy = RepUtils.temporary_named_copy(doc_file)

                        with tmp_copy:
                            outzd.write(tmp_copy.name,
                                        "%s/%s" % (env_name, str(doc.getId())))

                #write metadata.txt
                metadata_file = RepUtils.TmpFile(
                    zip_content.get_metadata_content(env_ob))
                outzd.write(str(metadata_file),
                            "%s/%s" % (env_name, 'metadata.txt'))

                #write README.txt
                readme_file = RepUtils.TmpFile(
                    zip_content.get_readme_content(env_ob))
                outzd.write(str(readme_file),
                            "%s/%s" % (env_name, 'README.txt'))

                #write history.txt
                history_file = RepUtils.TmpFile(
                    zip_content.get_history_content(env_ob))
                outzd.write(str(history_file),
                            "%s/%s" % (env_name, 'history.txt'))

        outzd.close()
        stat = os.stat(tmpfile)

        RESPONSE.setHeader('Content-Type', 'application/x-zip')
        RESPONSE.setHeader('Content-Disposition',
             'attachment; filename="%s.zip"' % 'envelopes')
        RESPONSE.setHeader('Content-Length', stat[6])
        RepUtils.copy_file(tmpfile, RESPONSE)
        os.unlink(tmpfile)
        return ''

    def __getObjects(self, p_brains):
        """ Get objects from catalog identifiers.
            Skip over the ones that don't really exist.
        """
        l_catalog = getattr(self, constants.DEFAULT_CATALOG)
        records = map(getattr, p_brains, ('data_record_id_',)*len(p_brains))
        objects = []
        for record in records:
            try:
                objects.append(l_catalog.getobject(record))
            except:
                pass
        return objects

    def runAutomaticApplications(self, p_applications, REQUEST=None):
        """ Searches for the active workitems of activities that need triggering
            on regular basis and calls triggerApplication for them
            Example of activity that needs further triggering: AutomaticQA

            Note: Since this method is called using a HTTP get, the p_applications
                  parameter cannot be a list, but a string. To include more than one
                  applications, separate them by ||
        """
        l_catalog = getattr(self, constants.DEFAULT_CATALOG)
        l_result = l_catalog(meta_type='Workitem', status='active')
        l_list = []
        workitems_list = map(getattr, l_result, ('data_record_id_',)*len(l_result))
        l_applications = p_applications.split('||')

        for workitemptr in workitems_list:
            try:
                workitem = l_catalog.getobject(workitemptr)
                if workitem.activity_id in l_applications:
                    l_list.append(workitem.absolute_url())
                    workitem.triggerApplication(workitem.id, REQUEST)
            except:
                # TODO transaction savepoint restore
                # TODO log the error (see r29924)
                pass   # Bad zcatalog, but we ignore it
        return l_list

    def _xmlrpc_search_delivery(self, dataflow_uris, country):
        """ Looks for Report Envelopes with the given attributes
        """
        l_catalog = getattr(self, constants.DEFAULT_CATALOG)
        l_result = []
        l_deliveries = l_catalog(meta_type='Report Envelope', country=country)
        for l_delivery in l_deliveries:
            l_obj = l_delivery.getObject()
            if RepUtils.utIsSubsetOf(l_obj.dataflow_uris, dataflow_uris):
                l_result.append(l_obj)
        return l_result

    security.declareProtected('View', 'lookup_last_delivery')
    def lookup_last_delivery(self, dataflow_uris, country, reporting_period=''):
        """ Find the newest delivery with the same location and dataflows, 
            but is older than the reporting_period in the argument
            If the reporting_period is not provided, finds them all until today
        """
        if reporting_period:
            l_reporting_period = DateTime(reporting_period)
        else:
            l_reporting_period = DateTime()
        l_deliveries = self._xmlrpc_search_delivery(dataflow_uris=dataflow_uris, country=country)
        if l_deliveries:
            # order all envelopes by start data in reverse and 
            # filter only the ones that have the start date previous than l_reporting_period
            return RepUtils.utSortByMethod(l_deliveries, 'getStartDate', l_reporting_period, 1)
        return []

    security.declareProtected(view_management_screens, 'harvestXforms')
    def harvestXforms(self):
        """ calls getXforms from the WebQ, and updates the DataflowMappingRecord table 
            for the haswebform attribute 
            To be called on regular basis by a cron job
        """
        if self.webq_url:
            l_dataflow_mappings_container = getattr(self, constants.DATAFLOW_MAPPINGS)
            l_maprecords = l_dataflow_mappings_container.objectValues('Reportek Dataflow Mapping Record')
            l_valid_schemas = l_dataflow_mappings_container.getXMLSchemasForAllDataflows()
            try:
                l_server = xmlrpclib.ServerProxy(self.webq_url)
                # GetXForm returns a dictionary {'XML_schema':'Form_name'}
                l_ret = l_server.WebQService.getXForm(l_valid_schemas)
            except xmlrpclib.Fault, l_fault:
                return str(l_fault)
            # An HTTP protocol error - retry later
            except xmlrpclib.ProtocolError, l_protocol:
                return str(l_protocol)
            # A broken response package - critical, do not retry
            except xmlrpclib.ResponseError, l_response:
                return str(l_response)
            # Generic client error - critical, do not retry
            except xmlrpclib.Error, err:
                return str(err)
        # Update the dataflow mappings
        for l_item in l_maprecords:
            for schema_url in l_item.allowedSchemas + l_item.webformSchemas:
                if l_ret.has_key(schema_url):
                    l_item.set_schema_type(schema_url, l_ret[schema_url] != '')
        return '1'

    ################################################################################
    #
    # Interface for the DMM integration
    #
    ################################################################################

    security.declareProtected('View', 'getEnvelopesInfo')
    def getEnvelopesInfo(self, obligation):
        """ Returns a list with all information about envelopes for a certain obligation, 
            including the XML files inside 
        """
        reslist = []
        l_catalog = getattr(self, constants.DEFAULT_CATALOG)
        l_params = {'meta_type':'Report Envelope', 'dataflow_uris':obligation, 'released':1}

        for obj in self.__getObjects(l_catalog.searchResults(l_params)):
            res = { 'url': obj.absolute_url(0),
                'title': obj.title,
                'description': obj.descr,
                'dataflow_uris': obj.dataflow_uris,
                'country': obj.country,
                'country_name': obj.getCountryName(),
                'country_code': obj.getCountryCode(),
                'locality': obj.locality,
                'released': obj.reportingdate.HTML4(),
                'startyear': obj.year,
                'endyear': obj.endyear,
                'partofyear': obj.partofyear,
            }
            filelist = []
            for file in obj.objectValues('Report Document'):
                if file.content_type == 'text/xml':
                    if file.acquiredRolesAreUsedBy('View'):
                        restricted = 0
                    else:
                        restricted = 1
                    filelist.append([file.id,file.content_type,file.xml_schema_location, file.title, restricted])
            res['files'] = filelist
            reslist.append(res)
        return reslist

    ################################################################################
    #
    # Interface for the UNS integration
    #
    ################################################################################

    security.declareProtected('View', 'subscriptions_html')
    subscriptions_html = DTMLFile('dtml/engineSubscriptions', globals())

    security.declareProtected('View', 'uns_settings')
    uns_settings = DTMLFile('dtml/engineUNSInterface', globals())

    security.declareProtected('View management screens', 'manage_editUNSInterface')
    def manage_editUNSInterface(self, UNS_server, UNS_username, UNS_password, UNS_password_confirmation, UNS_channel_id, UNS_notification_types, REQUEST=None):
        """ Edit the UNS related properties """
        if UNS_password != UNS_password_confirmation:
            if REQUEST is not None:
                REQUEST.RESPONSE.redirect('uns_settings?manage_tabs_message=Password and confirmation do not match!')
            return 0
        self.UNS_server = UNS_server
        self.UNS_username = UNS_username
        self.UNS_password = UNS_password
        self.UNS_channel_id = UNS_channel_id
        self.UNS_notification_types = [x for x in UNS_notification_types if x != '']
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect('uns_settings?manage_tabs_message=Saved changes')
        return 1

    def uns_notifications_enabled(self):
        env = getattr(getConfiguration(), 'environment', {})
        return bool(env.get('UNS_NOTIFICATIONS', 'off') == 'on')

    security.declarePrivate('get_uns_xmlrpc_server')
    def get_uns_xmlrpc_server(self):
        if self.uns_notifications_enabled():
            url = self.UNS_server + '/rpcrouter'
            if self.UNS_username:
                frag = '%s:%s@' % (self.UNS_username, self.UNS_password)
                url = url.replace('http://', 'http://'+frag)
                url = url.replace('https://', 'https://'+frag)
        else:
            url = ''
        return xmlrpclib.Server(url)

    security.declareProtected('View', 'canUserSubscribeToUNS')
    def canUserSubscribeToUNS(self, user_id='', REQUEST=None):
        """ Indicates if the user given as parameter or authenticated 
            is allowed to subscribe to UNS for this channel
        """
        if not user_id:
            user_id = self.REQUEST['AUTHENTICATED_USER'].getUserName()
            if user_id == 'Anonymous User':
                return 0
        # TODO: cache results for a few minutes
        try:
            l_server = self.get_uns_xmlrpc_server()
            l_ret = l_server.UNSService.canSubscribe(self.UNS_channel_id, user_id)
            return l_ret
        except Exception, err:
            return 0

    security.declareProtected('View', 'subscribeToUNS')
    def subscribeToUNS(self, filter_country='', filter_dataflows=[], filter_event_types=[], REQUEST=None):
        """ Creates new or updates existing subscription to the specified
            If there is a request, returns a message, otherwise, returns 
            (1, '') for success
            (0, error_description) for failure
        """
        l_filters = []
        if filter_dataflows not in [[], ['']]:
            for l_filter_dataflow in filter_dataflows:
                if filter_country:
                    l_filters.append({'http://rod.eionet.europa.eu/schema.rdf#obligation': l_filter_dataflow, \
                        'http://rod.eionet.europa.eu/schema.rdf#locality':filter_country})
                else:
                    l_filters.append({'http://rod.eionet.europa.eu/schema.rdf#obligation': l_filter_dataflow})
        elif filter_country:
            l_filters.append({'http://rod.eionet.europa.eu/schema.rdf#locality':filter_country})

        l_filters_final = []
        if l_filters != []:
            for l_filter_event_type in filter_event_types:
                for l_filter in l_filters:
                    l_tmp = copy(l_filter)
                    l_tmp['http://rod.eionet.europa.eu/schema.rdf#event_type'] = l_filter_event_type
                    l_filters_final.append(l_tmp)
        else:
            for l_filter_event_type in filter_event_types:
                l_filters_final.append({'http://rod.eionet.europa.eu/schema.rdf#event_type':l_filter_event_type})

        try:
            l_server = self.get_uns_xmlrpc_server()
            #l_ret = l_server.UNSService.makeSubscription(self.UNS_channel_id, self.REQUEST['AUTHENTICATED_USER'].getUserName(), l_filters)
            l_ret = l_server.UNSService.makeSubscription(self.UNS_channel_id, self.REQUEST['AUTHENTICATED_USER'].getUserName(), l_filters_final)
            if REQUEST is not None:
                REQUEST.RESPONSE.redirect('subscriptions_html?info_title=Information&info_msg=Subscription made successfully')
            return (1, '')
        except Exception, err:
            if REQUEST is not None:
                REQUEST.RESPONSE.redirect('subscriptions_html?info_title=Error&info_msg=Your subscription could not be made because of the following error: %s' % str(err))
            return (0, str(err))

    security.declareProtected('View', 'sendNotificationToUNS')
    def sendNotificationToUNS(self, envelope, notification_type, notification_label, actor='system'):
        """ Sends events data to the specified UNS's push channel """
        try:
            l_server = self.get_uns_xmlrpc_server()
            # create unique notification identifier
            # Envelope URL + time + notification_type
            l_time = str(time())
            l_id = "%s/events#ts%s" % (envelope.absolute_url(), l_time )
            #l_id = "http://rod.eionet.europa.eu/events/%s" % l_time
            l_res = []
            l_res.append([l_id, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type', 'http://rod.eionet.europa.eu/schema.rdf#Workflowevent'])
            l_res.append([l_id, 'http://purl.org/dc/elements/1.1/title', notification_label])
            l_res.append([l_id, 'http://purl.org/dc/elements/1.1/identifier', envelope.absolute_url()])
            l_res.append([l_id, 'http://purl.org/dc/elements/1.1/date', strftime('%Y-%b-%d %H:%M:%S')])
            #l_res.append([l_id, 'http://rod.eionet.europa.eu/schema.rdf#label', notification_label])
            l_dataflows = [envelope.dataflow_lookup(x)['TITLE'] for x in envelope.dataflow_uris]
            for l_dataflow in l_dataflows:
                l_res.append([l_id, 'http://rod.eionet.europa.eu/schema.rdf#obligation', str(l_dataflow)])
            l_res.append([l_id, 'http://rod.eionet.europa.eu/schema.rdf#locality', str(envelope.getCountryName())])
            l_res.append([l_id, 'http://rod.eionet.europa.eu/schema.rdf#actor', actor])
            l_res.append([l_id, 'http://rod.eionet.europa.eu/schema.rdf#event_type', notification_type])
            l_ret = l_server.UNSService.sendNotification(self.UNS_channel_id, l_res)
            return 1
        except:
            return 0

    security.declarePrivate('uns_subscribe_actors')
    def uns_subscribe_actors(self, actors, filters):
        server = self.get_uns_xmlrpc_server()
        for act in actors:
            server.UNSService.makeSubscription(self.UNS_channel_id, act, filters)

    ################################################################################
    #
    # Utils
    #
    ################################################################################

    def getListAsDict(self, ob_list=[], key=''):
        """ Get a list of dictionaries and return a tuple of (key, value)
        """
        groups = list(set([x.get(key, '') for x in ob_list]))
        groups.sort()
        for group in groups:
            yield group, [x for x in ob_list if x.get(key, '') == group]

    security.declareProtected('View', 'messageDialog')
    def messageDialog(self, message='', action='./manage_main', REQUEST=None):
        """ displays a message dialog """
        return self.message_dialog(message=message, action=action)

    message_dialog = PageTemplateFile('zpt/message_dialog', globals())

    security.declarePublic('getEnvelopeByURL')
    def getEnvelopeByURL(self, file_url, REQUEST=None):
        """ return the URL of an envelope based on a contained object URL """
        REQUEST.RESPONSE.setHeader('Content-type', 'text/xml')
        parsde_url = urlparse(file_url)
        file_obj = self.unrestrictedTraverse(parsde_url[2], None)
        return """<envelope>
            <rel_uri>/%s</rel_uri>
        </envelope>""" % file_obj.getMySelf().absolute_url(1)

    security.declareProtected('View management screens', 'manage_raise_exception')
    def manage_raise_exception(self):
        """ Generate exception to check that it's handled properly """
        raise ValueError('hello world')

    security.declareProtected('View', 'getSearchResults')
    def getSearchResults(self, **kwargs):
        [kwargs.pop(el) for el in kwargs.keys() if not kwargs[el]]
        catalog = self.Catalog(**kwargs)
        return catalog

    security.declareProtected('View', 'getUniqueValuesFor')
    def getUniqueValuesFor(self, value):
        return self.Catalog.uniqueValuesFor(value)

Globals.InitializeClass(ReportekEngine)
