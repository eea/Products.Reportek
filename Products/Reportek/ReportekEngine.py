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
# Miruna Badescu, Eau de Web
# Daniel Bărăgan, Eau de Web

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
import json

# Zope imports
from OFS.Folder import Folder
from AccessControl import getSecurityManager, ClassSecurityInfo
from AccessControl.Permissions import view_management_screens, view
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from App.config import getConfiguration
from config import *
import Globals
import Products
import xmlrpclib
from DateTime import DateTime
from time import time, strftime
from copy import copy

# product imports
import constants
from Products.Reportek.ContentRegistryPingger import ContentRegistryPingger
from Products.Reportek.BdrAuthorizationMiddleware import BdrAuthorizationMiddleware
from Products.Reportek.RegistryManagement import BaseRegistryAPI
from Products.Reportek.RegistryManagement import BDRRegistryAPI
from Products.Reportek.RegistryManagement import FGASRegistryAPI
import RepUtils
from Toolz import Toolz
from DataflowsManager import DataflowsManager
from CountriesManager import CountriesManager
from paginator import DiggPaginator, EmptyPage, InvalidPage
from zope.interface import implements
from interfaces import IReportekEngine
from zope.i18n.negotiator import normalize_lang
from zope.i18n.interfaces import II18nAware, INegotiator
from zope.component import getUtility
import logging
logger = logging.getLogger("Reportek")

class ReportekEngine(Folder, Toolz, DataflowsManager, CountriesManager):
    """ Stores generic attributes for Reportek """

    implements(IReportekEngine, II18nAware)
    meta_type = 'Reportek Engine'
    icon = 'misc_/Reportek/Converters'

    security = ClassSecurityInfo()

    manage_options = ( (
        {'label':'View', 'action': 'index_html'},
        {'label':'Properties', 'action': 'manage_properties'},
        {'label':'UNS settings', 'action': 'uns_settings'},
        {'label':'Migrations', 'action': 'migration_table'},
        ) + Folder.manage_options[3:]
    )

    _properties = ({'id':'title', 'type':'string', 'mode':'w', 'label':'Title'},
            {'id':'webq_url', 'type':'string', 'mode':'w'},
            {'id':'webq_envelope_menu', 'type':'string', 'mode':'w'},
            {'id':'webq_before_edit_page', 'type':'string', 'mode':'w'},
            {'id':'UNS_server', 'type':'string', 'mode':'w'},
            {'id':'UNS_username', 'type':'string', 'mode':'w'},
            {'id':'UNS_password', 'type':'string', 'mode':'w'},
            {'id':'UNS_channel_id', 'type':'string', 'mode':'w'},
            {'id':'UNS_notification_types', 'type':'lines', 'mode':'w'},
            {'id':'QA_application', 'type':'string', 'mode':'w'},
            {'id':'globally_restricted_site', 'type':'tokens', 'mode':'w'}
    )

    # The URL to the WebQ XML-RPC server
    # Empty means no WebQ available
    webq_url = 'http://cdr.eionet.europa.eu/webq/RpcRouter'
    # The URL to the WebQ page which constructs a menu for a specified envelope
    # called via HTTP GET
    webq_envelope_menu = 'http://cdr.eionet.europa.eu/webq/WebQMenu'
    # The URL to the WebQ webpage, before the user starts to use the edit form.
    # The purpose is to ask the capabilities of the user webbrowser
    # and what language the form should be in.
    # called via HTTP GET
    webq_before_edit_page = 'http://cdr.eionet.europa.eu/webq/WebQEdit'
    # The default QA application used for manual and automatic triggered QA operation
    # If this is empty, this Reportek instance does not have a QA system linked to it
    QA_application = ''
    globally_restricted_site = False
    if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
        cr_api_url = 'http://cr.eionet.europa.eu/ping'
    else:
        cr_api_url = ''
    auth_middleware_url = ''
    bdr_registry_url = ''
    bdr_registry_username = ''
    bdr_registry_password = ''
    fgas_registry_url = ''
    auth_middleware_recheck_interval = 300

    def all_meta_types(self, interfaces=None):
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
        DataflowsManager.__init__(self)
        CountriesManager.__init__(self)
        self.id = constants.ENGINE_ID
        # UNS configuration parameters
        self.UNS_server = ''
        self.UNS_username = ''
        self.UNS_password = ''
        self.UNS_channel_id = ''
        self.UNS_notification_types = ['Envelope release', 'Envelope revoke']
        #self.UNS_notification_types = ['Envelope complete', 'Envelope release', 'Envelope revoke', 'Manual feedback posted', 'Quality assessment finished']

    security.declareProtected(view_management_screens, 'index_html')
    index_html = PageTemplateFile('zpt/engine_index', globals())

    # Setters for the XMLRPC Methods properties
    @DataflowsManager.dfm_title.setter
    def dfm_title(self, value):
        xmlrpc_dataflow = getattr(self, 'xmlrpc_dataflow', None)
        if xmlrpc_dataflow:
            self.xmlrpc_dataflow.title = value

    @DataflowsManager.dfm_url.setter
    def dfm_url(self, value):
        xmlrpc_dataflow = getattr(self, 'xmlrpc_dataflow', None)
        if xmlrpc_dataflow:
            self.xmlrpc_dataflow.url = value

    @DataflowsManager.dfm_method.setter
    def dfm_method(self, value):
        xmlrpc_dataflow = getattr(self, 'xmlrpc_dataflow', None)
        if xmlrpc_dataflow:
            self.xmlrpc_dataflow.method_name = value

    @DataflowsManager.dfm_timeout.setter
    def dfm_timeout(self, value):
        xmlrpc_dataflow = getattr(self, 'xmlrpc_dataflow', None)
        if xmlrpc_dataflow:
            self.xmlrpc_dataflow.timeout = float(value)

    @CountriesManager.cm_title.setter
    def cm_title(self, value):
        xmlrpc_localities = getattr(self, 'xmlrpc_localities', None)
        if xmlrpc_localities:
            self.xmlrpc_localities.title = value

    @CountriesManager.cm_url.setter
    def cm_url(self, value):
        xmlrpc_localities = getattr(self, 'xmlrpc_localities', None)
        if xmlrpc_localities:
            self.xmlrpc_localities.url = value

    @CountriesManager.cm_method.setter
    def cm_method(self, value):
        xmlrpc_localities = getattr(self, 'xmlrpc_localities', None)
        if xmlrpc_localities:
            self.xmlrpc_localities.method_name = value

    @CountriesManager.cm_timeout.setter
    def cm_timeout(self, value):
        xmlrpc_localities = getattr(self, 'xmlrpc_localities', None)
        if xmlrpc_localities:
            self.xmlrpc_localities.timeout = float(value)

    #security stuff
    security = ClassSecurityInfo()

    security.declarePublic('getDeploymentType')
    def getDeploymentType(self):
        return Products.Reportek.REPORTEK_DEPLOYMENT

    _manage_properties = PageTemplateFile('zpt/engine/prop', globals())

    security.declareProtected(view_management_screens, 'manage_properties')
    def manage_properties(self):
        """ Manage the edited values """
        if self.REQUEST['REQUEST_METHOD'] == 'GET':
            return self._manage_properties()

        self.title = self.REQUEST.get('title', self.title)
        self.webq_url = self.REQUEST.get('webq_url', self.webq_url)
        self.webq_envelope_menu = self.REQUEST.get('webq_envelope_menu', self.webq_envelope_menu)
        self.webq_before_edit_page = self.REQUEST.get('webq_before_edit_page', self.webq_before_edit_page)
        self.QA_application = self.REQUEST.get('QA_application', self.QA_application)
        self.globally_restricted_site = bool(self.REQUEST.get('globally_restricted_site',
                                                self.globally_restricted_site))

        self.dfm_url = self.REQUEST.get('dfm_url', self.dfm_url)
        self.dfm_method = self.REQUEST.get('dfm_method', self.dfm_method)
        self.dfm_timeout = self.REQUEST.get('dfm_timeout', self.dfm_timeout)

        self.cm_url = self.REQUEST.get('cm_url', self.cm_url)
        self.cm_method = self.REQUEST.get('cm_method', self.cm_method)
        self.cm_timeout = self.REQUEST.get('cm_timeout', self.cm_timeout)

        self.cr_api_url = self.REQUEST.get('cr_api_url', self.cr_api_url)
        if self.cr_api_url:
            self.contentRegistryPingger.api_url = self.cr_api_url

        self.auth_middleware_url = self.REQUEST.get('auth_middleware_url', self.auth_middleware_url)
        if self.auth_middleware_url:
            self.auth_middleware_recheck_interval = int(self.REQUEST.get('auth_middleware_recheck_interval', self.auth_middleware_recheck_interval))
            self.authMiddlewareApi.setServiceRecheckInterval(self.auth_middleware_recheck_interval)
            self.authMiddlewareApi.setServiceUrl(self.auth_middleware_url)
        self.bdr_registry_url = self.REQUEST.get('bdr_registry_url', self.bdr_registry_url)
        self.bdr_registry_username = self.REQUEST.get('bdr_registry_username', self.bdr_registry_username)
        self.bdr_registry_password = self.REQUEST.get('bdr_registry_password', self.bdr_registry_password)
        self.fgas_registry_url = self.REQUEST.get('fgas_registry_url', self.fgas_registry_url)

        # don't send the completed from back, the values set on self must be used
        return self._manage_properties(manage_tabs_message="Properties changed")

    def canPingCR(self, envelope):
        """Check if a pingger is or can be created"""
        if getSecurityManager().checkPermission('Release Envelopes', envelope):
            return bool(self.contentRegistryPingger)

    @property
    def contentRegistryPingger(self):
        if not self.cr_api_url:
            return None
        pingger = getattr(self, '_contentRegistryPingger', None)
        if pingger:
            return pingger
        else:
            self._contentRegistryPingger = ContentRegistryPingger(self.cr_api_url)
            return self._contentRegistryPingger

    @property
    def authMiddlewareApi(self):
        if not self.auth_middleware_url:
            return None
        api = getattr(self, '_authMiddlewareApi', None)
        if api:
            return api
        else:
            self._authMiddlewareApi = BdrAuthorizationMiddleware(self.auth_middleware_url)
            return self._authMiddlewareApi

    @property
    def FGASRegistryAPI(self):
        if not getattr(self, '_FGASRegistryAPI', None):
            self._FGASRegistryAPI = FGASRegistryAPI(self.fgas_registry_url)
        return self._FGASRegistryAPI

    @property
    def BDRRegistryAPI(self):
        if not getattr(self, '_BDRRegistryAPI', None):
            self._BDRRegistryAPI = BDRRegistryAPI(self.bdr_registry_url)
        return self._BDRRegistryAPI

    def get_registry(self, dataflow_uris):
        uris = {
        'http://rod.eionet.europa.eu/obligations/713': 'FGASRegistryAPI',
        'http://rod.eionet.europa.eu/obligations/213': 'BDRRegistryAPI'
        }

        if dataflow_uris:
            registry = uris.get(dataflow_uris[0])
            return getattr(self, registry, None)

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

    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
        security.declareProtected(view_management_screens, 'update_company_collection')
        def update_company_collection(self, company_id, domain, country,
                                    name, old_collection_id=None):
            """Update information on an existing old-type collection (say, 'fgas30001')
            mainly setting it's `company_id` (the id internal to Fgas Portal for instance)
            If no `old_collection_id` is provided then a new collection will be created with
            id=company_id=provided `company_id`.
            If `old_collection_id` is provided, the the collection must exist in the expected path
            deducted from the domain/country/old_collection_id. It's company_id will be updated.
            If `old_collection_id` does not exist at the expected location nothing will happen."""
            # form path, make sure it is not absolute, else change the code below to match
            self.REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
            resp = {'status': 'fail',
                    'message': ''}
            coll_path = self.authMiddlewareApi.authMiddlewareApi.buildCollectionPath(
                    domain, country, company_id, old_collection_id)
            if not coll_path:
                msg = ("Cannot form path to collection, with details domain:"
                    " %s, country: %s, company_id: %s, old_collection_id: %s.") % (
                    domain, country, company_id, old_collection_id)
                logger.warning(msg)
                # return failure (404) to the service calling us
                self.REQUEST.RESPONSE.setStatus(404)
                resp['message'] = msg
                return json.dumps(resp)

            path_parts = coll_path.split('/')
            obligation_id= path_parts[0]
            country_id = path_parts[1]
            coll_id = path_parts[2]
            root = self.restrictedTraverse('/')
            try:
                obligation_folder = getattr(root, obligation_id)
                country_folder = getattr(obligation_folder, country_id)
            except:
                msg = "Cannot update collection %s. Path to collection does not exist" % coll_path
                logger.warning(msg)
                # return 404
                self.REQUEST.RESPONSE.setStatus(404)
                resp['message'] = msg
                return json.dumps(resp)

            # old type of collection
            if old_collection_id:
                try:
                    coll = getattr(country_folder, old_collection_id)
                    coll.company_id = company_id
                    coll.dataflow_uris = [ self.authMiddlewareApi.authMiddlewareApi.DOMAIN_TO_OBLIGATION[domain] ]
                    coll.reindex_object()
                except:
                    msg = "Cannot update collection %s Old style collection not found" % coll_path
                    logger.warning(msg)
                    self.REQUEST.RESPONSE.setStatus(404)
                    resp['message'] = msg
                    return json.dumps(resp)
            else:
                try:
                    coll = getattr(country_folder, coll_id)
                except:
                    # not there, create it
                    # Don't take obligation from parent as it can be a terminated obligation
                    try:
                        dataflow_uris = [ self.authMiddlewareApi.authMiddlewareApi.DOMAIN_TO_OBLIGATION[domain] ]
                        country_uri = country_folder.country
                        country_folder.manage_addCollection(dataflow_uris=dataflow_uris,
                            country=country_uri,
                            id=company_id,
                            title=name,
                            allow_collections=0, allow_envelopes=1,
                            descr='', locality='', partofyear='', year='', endyear='')
                        coll = getattr(country_folder, company_id)
                    except Exception as e:
                        msg = "Cannot create collection %s. " % coll_path
                        logger.warning(msg + str(e))
                        # return failure (404) to the service calling us
                        self.REQUEST.RESPONSE.setStatus(404)
                        resp['message'] = msg
                        return json.dumps(resp)
                coll.company_id = company_id
                coll.reindex_object()
            resp['status'] = 'success'
            resp['message'] = 'Collection %s updated/created succesfully' % coll_path
            return json.dumps(resp)
    else:
        security.declareProtected(view_management_screens, 'update_company_collection')
        def update_company_collection(self, company_id, domain, country,
                                  name, old_collection_id=None):
            pass

    security.declareProtected('View', 'macros')
    macros = PageTemplateFile('zpt/engineMacros', globals()).macros

    security.declareProtected('View', 'globalworklist')
    globalworklist = PageTemplateFile('zpt/engineGlobalWorklist', globals())

    security.declareProtected('View', 'searchfeedbacks')
    searchfeedbacks = PageTemplateFile('zpt/engineSearchFeedbacks', globals())

    security.declareProtected('View', 'resultsfeedbacks')
    resultsfeedbacks = PageTemplateFile('zpt/engineResultsFeedbacks', globals())

    security.declareProtected('View', 'recent')
    recent = PageTemplateFile('zpt/engineRecentUploads', globals())

    security.declareProtected('View', 'searchxml')
    searchxml = PageTemplateFile('zpt/engineSearchXml', globals())

    security.declareProtected('View', 'resultsxml')
    resultsxml = PageTemplateFile('zpt/engineResultsXml', globals())

    security.declarePublic('languages_box')
    languages_box = PageTemplateFile('zpt/languages_box', globals())

    _searchdataflow = PageTemplateFile('zpt/searchdataflow', globals())

    security.declareProtected('View', 'search_dataflow')
    search_dataflow = PageTemplateFile('zpt/search_dataflow', globals())

    security.declareProtected('View', 'searchdataflow')
    def searchdataflow(self):
        """Search the ZCatalog for Report Envelopes,
        show results and keep displaying the form """
        # show the initial default populated
        if 'sort_on' not in self.REQUEST:
            return self._searchdataflow()

        # make sure fields you are not searching for are not included
        # in the query, not even with '' or None values
        catalog_args = {
            'meta_type': ['Report Envelope', 'Repository Referral']
        }
        status = self.REQUEST.get('release_status')
        if status == 'anystatus':
            catalog_args.pop('released', None)
        elif status == 'released':
            catalog_args['released'] = 1
        elif status == 'notreleased':
            catalog_args['released'] = 0
        else:
            # FIXME this stops the view but does not display a proper error
            self.REQUEST.RESPONSE.setStatus(400, 'bla')
            return self.REQUEST.RESPONSE

        if self.REQUEST.get('query_start'):
            catalog_args['start'] = self.REQUEST['query_start']
        if self.REQUEST.get('sort_on'):
            catalog_args['sort_on'] = self.REQUEST['sort_on']
        if self.REQUEST.get('sort_order'):
            catalog_args['sort_order'] = self.REQUEST['sort_order']
        if self.REQUEST.get('dataflow_uris'):
            catalog_args['dataflow_uris'] = self.REQUEST['dataflow_uris']
        if self.REQUEST.get('country'):
            catalog_args['country'] = self.REQUEST['country']
        if self.REQUEST.get('years'):
            catalog_args['years'] = self.REQUEST['years']
        if self.REQUEST.get('partofyear'):
            catalog_args['partofyear'] = self.REQUEST['partofyear']

        reportingdate_start = self.REQUEST.get('reportingdate_start')
        reportingdate_end = self.REQUEST.get('reportingdate_end')
        dateRangeQuery = {}
        if reportingdate_start and reportingdate_end:
            dateRangeQuery['range'] = 'min:max'
            dateRangeQuery['query'] = [reportingdate_start, reportingdate_end]
        elif reportingdate_start:
            dateRangeQuery['range'] = 'min'
            dateRangeQuery['query'] = reportingdate_start
        elif reportingdate_end:
            dateRangeQuery['range'] = 'max'
            dateRangeQuery['query'] = reportingdate_end
        if dateRangeQuery:
            catalog_args['reportingdate'] = dateRangeQuery
        envelopes = self.Catalog(**catalog_args)
        envelopeObjects = []
        for eBrain in envelopes:
            o = eBrain.getObject()
            if getSecurityManager().checkPermission('View', o):
                envelopeObjects.append(o)
        return self._searchdataflow(results=envelopeObjects, **self.REQUEST.form)

    security.declareProtected('View', 'search_dataflow_url')
    def search_dataflow_url(self):
        """Search the ZCatalog for Report Envelopes,
        show results and keep displaying the form """

        catalog_args = {
            'meta_type': ['Report Envelope', 'Repository Referral'],
        }

        status = self.REQUEST.get('release_status')
        if status == 'anystatus':
            catalog_args.pop('released', None)
        elif status == 'released':
            catalog_args['released'] = 1
        elif status == 'notreleased':
            catalog_args['released'] = 0
        else:
            return json.dumps([])

        if self.REQUEST.get('query_start'):
            catalog_args['start'] = self.REQUEST['query_start']
        if self.REQUEST.get('obligation'):
            obl = self.REQUEST.get('obligation')
            obl = filter(lambda c: c.get('PK_RA_ID') == obl, self.dataflow_rod())[0]
            catalog_args['dataflow_uris'] = [obl['uri']]
        if self.REQUEST.get('countries'):
            isos = self.REQUEST.get('countries')
            countries = filter(lambda c: c.get('iso') in isos, self.localities_rod())
            catalog_args['country'] = [country['uri'] for country in countries]
        if self.REQUEST.get('years'):
            catalog_args['years'] = self.REQUEST['years']
        if self.REQUEST.get('partofyear'):
            catalog_args['partofyear'] = self.REQUEST['partofyear']

        reportingdate_start = self.REQUEST.get('reportingdate_start')
        reportingdate_end = self.REQUEST.get('reportingdate_end')
        dateRangeQuery = {}
        if reportingdate_start and reportingdate_end:
            dateRangeQuery['range'] = 'min:max'
            dateRangeQuery['query'] = [reportingdate_start, reportingdate_end]
        elif reportingdate_start:
            dateRangeQuery['range'] = 'min'
            dateRangeQuery['query'] = reportingdate_start
        elif reportingdate_end:
            dateRangeQuery['range'] = 'max'
            dateRangeQuery['query'] = reportingdate_end
        if dateRangeQuery:
            catalog_args['reportingdate'] = dateRangeQuery

        envelopes = self.Catalog(**catalog_args)
        envelopeObjects = []
        for eBrain in envelopes:
            obj = eBrain.getObject()
            if getSecurityManager().checkPermission('View', obj):
                files = []
                for fileObj in obj.objectValues('Report Document'):
                    files.append({
                        "filename": fileObj.id,
                        "title": str(fileObj.absolute_url_path()),
                        "url": str(fileObj.absolute_url_path()) + "/manage_document"
                    })

                accepted = True
                for fileObj in obj.objectValues('Report Feedback'):
                    if fileObj.title in ("Data delivery was not acceptable", "Non-acceptance of F-gas report"):
                        accepted = False

                obligations = []
                for uri in obj.dataflow_uris:
                    obligations.append(self.dataflow_lookup(uri)['TITLE'])

                countryName = ''
                if obj.meta_type == 'Report Envelope':
                    countryName = obj.getCountryName()
                else:
                    try:
                        countryName = obj.localities_dict()[obj.country]['name']
                    except KeyError:
                        countryName = "Unknowm"

                reported = obj.bobobase_modification_time()
                if obj.meta_type == 'Report Envelope':
                    reported = obj.reportingdate

                company_id = '-'
                if (hasattr(obj.aq_parent, 'company_id')):
                    company_id = obj.aq_parent.company_id

                envelopeObjects.append({
                    'company_id': company_id,
                    'released': obj.released,
                    'path': obj.absolute_url_path(),
                    'country': countryName,
                    'company': obj.aq_parent.title,
                    'userid': obj.aq_parent.id,
                    'title': obj.title,
                    'id': obj.id,
                    'years': {"start": obj.year, "end": obj.endyear},
                    'end_year': obj.endyear,
                    'reportingdate': reported.strftime('%Y-%m-%d'),
                    'files': files,
                    'obligation': obligations[0] if obligations else "Unknown",
                    'accepted': accepted
                })

        return json.dumps(envelopeObjects)

    def assign_roles(self, user, role, local_roles, doc):
        local_roles.append(role)
        doc.manage_setLocalRoles(user, local_roles)

    def remove_roles(self, user, role, local_roles, doc):
        doc.manage_delLocalRoles(userids=[user,])
        if role in local_roles:
            local_roles.remove(role)
        if local_roles:
            doc.manage_setLocalRoles(user, local_roles)

    security.declareProtected(view_management_screens, 'show_local_roles')
    def show_local_roles(self, userid=None, REQUEST=None):
        """ REST API to get local roles for user id """

        def filter_objects(root):
            accepted_meta_types = ['Report Collection', 'Report Envelope']
            for node in root.objectValues():
                if node.meta_type in accepted_meta_types:
                    yield node
                    if node.meta_type == 'Report Collection':
                        for subnode in filter_objects(node):
                            if subnode.meta_type in accepted_meta_types:
                                yield subnode

        userid = userid or REQUEST.get('userid')
        if userid:
            from collections import defaultdict
            resp = defaultdict(list)
            for country in self.getCountriesList():
                for obj in filter_objects(country):
                    role = obj.get_local_roles_for_userid(userid)
                    if role:
                        resp[userid].append({
                            'roles': role,
                            'ob_url': obj.absolute_url(),
                            'ob_title': obj.title,
                            'extra': {'country': country.title}
                        })
            try:
                import json
            except ImportError:
                return resp
            REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
            return json.dumps(resp, indent=4)
        return None

    @staticmethod
    def clean_pattern(pattern):
        pattern = pattern.strip()
        pattern = pattern.replace('\\', '/')
        dirs = [item for item in pattern.split('/') if item]
        pattern = '/'.join(dirs)
        return pattern

    def response_messages(self, crole, users, ccountries, dataflow_uris,
                          fail_pattern, success_pattern, modifier):
        messages = []
        for country in ccountries:
            query = {
              'dataflow_uris': dataflow_uris,
              'meta_type': 'Report Collection',
              'country': country
            }

            catalog = self.Catalog
            brains = catalog(**query)
            if not brains:
                message = fail_pattern %(
                            crole,
                            ', '.join(users),
                            self.localities_dict().get(country, {'name': 'Unknown'})['name']
                )
                messages.append({
                    'status': 'fail',
                    'message': message
                })
                break
            res = []
            collections = []
            for brain in brains:
                doc = brain.getObject()
                for user in users:
                    local_roles = [role for role in doc.get_local_roles_for_userid(user) if role != 'Client']
                    modifier(user, crole, local_roles, doc)
                collections.append('<li>%s</li>' %doc.absolute_url())
            message = success_pattern %( crole, ', '.join(users), ''.join(collections))
            messages.append({
                'status': 'success',
                'message': message
            })
        return messages

    security.declareProtected('View', 'getCountriesList')
    def getCountriesList(self):
        """ """
        l_countries = self.getParentNode().objectValues('Report Collection')
        return RepUtils.utSortByAttr(l_countries, 'title')

    security.declarePrivate('sitemap_filter')
    def sitemap_filter(self, objs):
        return [x for x in objs if x.meta_type in ['Report Collection', 'Report Envelope', 'Repository Referral']]

    security.declareProtected('View', 'getSitemap')
    def getSitemap(self, tree_root=None, tree_pre='tree'):
        from ZTUtils import SimpleTreeMaker
        if tree_root is None: tree_root = self.getPhysicalRoot()
        tm = SimpleTreeMaker(tree_pre)
        tm.setChildAccess(filter=self.sitemap_filter)
        tm.setSkip('')
        try:
            tree, rows = tm.cookieTree(tree_root)
        except ValueError:
            #invalid parameter; clear request and try again
            tree_root.REQUEST.form.clear()
            tree, rows = tm.cookieTree(tree_root)
        rows.pop(0)
        return {'root': tree, 'rows': rows}

    security.declareProtected('View', 'sitemap')
    sitemap = PageTemplateFile('zpt/engine/sitemap', globals())

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
        """ Deprecated - use (with care) load_from_dd() on each DataflowMappingsRecord object for similar result

            calls getXforms from the WebQ, and updates the DataflowMappingRecord table
            for the haswebform attribute
            To be called on regular basis by a cron job
        """
        raise DeprecationWarning('DataflowMappingRecord objects have been deprecated, use DataflowMappingsRecord objects instead')

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
    subscriptions_html = PageTemplateFile('zpt/engine/subscriptions', globals())

    security.declareProtected('View', 'uns_settings')
    uns_settings = PageTemplateFile('zpt/engine/unsinterface', globals())

    _migration_table = PageTemplateFile('zpt/engine/migration_table', globals())

    security.declareProtected('View', 'migration_table')
    def migration_table(self):
        """List all migrations applied to this deployment and their details"""
        migs = getattr(self, constants.MIGRATION_ID)
        migs = sorted(migs.values(), key=lambda o: o.current_ts, reverse=True)
        rows = []
        for migrationOb in migs:
            migrationItem = {
                'name': migrationOb.name,
                'version': migrationOb.version,
                'first': migrationOb.toDate(migrationOb.first_ts),
                'current': migrationOb.toDate(migrationOb.current_ts),
            }
            rows.append(migrationItem)
        return self._migration_table(migrationRows=rows)

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
            l_dataflows = [self.dataflow_lookup(x)['TITLE'] for x in envelope.dataflow_uris]
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

    security.declarePublic('getAvailableLanguages')
    def getAvailableLanguages(self):
        """Get avalilable languages as their .mo files are found in locales/<ln_code> folders
        map them to their localized name."""
        negociator = getUtility(INegotiator)
        return negociator.getAvailableLanguages()

    security.declarePublic('getSelectedLanguage')
    def getSelectedLanguage(self):
        """Get selected language for this requester. The lang is selected by
        HTTP headers, cookie or stored default"""
        negociator = getUtility(INegotiator)
        return negociator.getSelectedLanguage(self.REQUEST)

    # public access
    #security.declarePublic('setCookieLanguage')
    def setCookieLanguage(self):
        """Sets the language of the site by cookie.
        negotiator will read this pref from cookie on every request
        """
        new_lang = self.REQUEST.get('chlang')
        if new_lang:
            new_lang = normalize_lang(new_lang)
            self.REQUEST.RESPONSE.setCookie('reportek_language', new_lang, path='/')
            self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
        # make it accessible from browser
        security.declarePublic('getUserCollections')
        def getUserCollections(self):
            if not getattr(self, 'REQUEST', None):
                return []
            collections = {}
            username = self.REQUEST['AUTHENTICATED_USER'].getUserName()
            ecas = self.unrestrictedTraverse('/acl_users/'+constants.ECAS_ID)
            ecas_user_id = ecas.getEcasUserId(username)
            # these are disjunct, so it is safe to add them all together
            # normally only one of the lists will have results, but they could be all empty too
            middleware_collections = []
            logger.debug("Attempt to interrogate middleware for authorizations for user:id %s:%s" % (username, ecas_user_id))
            if ecas_user_id:
                for colPath in self.authMiddlewareApi.getUserCollectionPaths(ecas_user_id,
                            recheck_interval=self.authMiddlewareApi.recheck_interval):
                    try:
                        middleware_collections.append(self.unrestrictedTraverse('/'+str(colPath)))
                    except:
                        logger.warning("Cannot traverse path: %s" % ('/'+str(colPath)))
            catalog = getattr(self, constants.DEFAULT_CATALOG)
            old_style_collections = [ br.getObject() for br in catalog(id=username) ]
            collections['Reporter'] = middleware_collections + old_style_collections
            local_roles = ['Auditor', 'ClientFG', 'ClientODS', 'ClientCARS']
            local_r_col = catalog(meta_type='Report Collection',
                                  local_unique_roles=local_roles)

            auditor = [br.getObject() for br in local_r_col
                       if 'Auditor' in br.local_defined_roles.get(username, [])
                       and len(br.getPath().split('/')) == 3]

            def is_client(l_roles):
                c_roles = ['ClientFG', 'ClientODS', 'ClientCARS']
                return [role for role in l_roles if role in c_roles]

            client = [br.getObject() for br in local_r_col
                      if is_client(br.local_defined_roles.get(username, []))
                      and len(br.getPath().split('/')) == 3]

            collections['Auditor'] = auditor
            collections['Client'] = client

            return collections
    else:
        security.declarePublic('getUserCollections')

        def getUserCollections(self):
            raise RuntimeError('Method not allowed on this distribution.')


Globals.InitializeClass(ReportekEngine)
