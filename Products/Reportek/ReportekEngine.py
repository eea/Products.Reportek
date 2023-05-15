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

import importlib
import json
import logging
import os
import requests
import tempfile
import xmlrpclib
from copy import copy, deepcopy
from operator import itemgetter
from StringIO import StringIO
from time import strftime, time
from urlparse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED

# product imports
import constants
import Globals
import Products
import RepUtils
import transaction
import xlwt
from AccessControl import ClassSecurityInfo, SpecialUsers, getSecurityManager
from AccessControl.Permissions import view, view_management_screens
from AccessControl.SecurityManagement import (newSecurityManager,
                                              setSecurityManager)
from config import REPORTEK_DEPLOYMENT, DEPLOYMENT_BDR, DEPLOYMENT_CDR
from CountriesManager import CountriesManager
from DataflowsManager import DataflowsManager
from DateTime import DateTime
from interfaces import IReportekEngine
# Zope imports
from OFS.Folder import Folder
from paginator import DiggPaginator, EmptyPage, InvalidPage
from plone.memoize import ram
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.BdrAuthorizationMiddleware import \
    BdrAuthorizationMiddleware
from Products.Reportek.clamav import AVService
from Products.Reportek.constants import ECAS_ID
from Products.Reportek.ContentRegistryPingger import ContentRegistryPingger
from Products.Reportek.RegistryManagement import (BDRRegistryAPI,
                                                  FGASRegistryAPI)
from Toolz import Toolz
from Products.Reportek.catalog import searchResults
from ZODB.PersistentList import PersistentList
from ZODB.PersistentMapping import PersistentMapping
from zope.component import getUtility
from zope.i18n.interfaces import II18nAware, INegotiator
from zope.i18n.negotiator import normalize_lang
from zope.interface import implements

__doc__ = """
      Engine for the Reportek Product
      Keeps all the global settings and implements administrative functions
      for the entire site
      Added in the Root folder by product's __init__
"""

logger = logging.getLogger("Reportek")


class ReportekEngine(Folder, Toolz, DataflowsManager, CountriesManager):
    """ Stores generic attributes for Reportek """

    implements(IReportekEngine, II18nAware)
    meta_type = 'Reportek Engine'
    icon = 'misc_/Reportek/Converters'

    security = ClassSecurityInfo()

    manage_options = ((
        {'label': 'View', 'action': 'index_html'},
        {'label': 'Properties', 'action': 'manage_properties'},
        {'label': 'UNS settings', 'action': 'uns_settings'},
        {'label': 'Migrations', 'action': 'migration_table'},
    ) + Folder.manage_options[3:]
    )

    _properties = ({'id': 'title',
                    'type': 'string',
                    'mode': 'w',
                    'label': 'Title'},
                   {'id': 'webq_url',
                    'type': 'string',
                    'mode': 'w'},
                   {'id': 'webq_envelope_menu',
                    'type': 'string',
                    'mode': 'w'},
                   {'id': 'webq_before_edit_page',
                    'type': 'string',
                    'mode': 'w'},
                   {'id': 'UNS_server',
                    'type': 'string',
                    'mode': 'w'},
                   {'id': 'UNS_username',
                    'type': 'string',
                    'mode': 'w'},
                   {'id': 'UNS_password',
                    'type': 'string',
                    'mode': 'w'},
                   {'id': 'UNS_channel_id',
                    'type': 'string',
                    'mode': 'w'},
                   {'id': 'UNS_notification_types',
                    'type': 'lines',
                    'mode': 'w'},
                   {'id': 'QA_application',
                    'type': 'string',
                    'mode': 'w'},
                   {'id': 'globally_restricted_site',
                    'type': 'tokens',
                    'mode': 'w'}
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
    # The default QA application used for manual and automatic triggered
    # QA operation
    # If this is empty, this Reportek instance does not have a QA system
    # linked to it
    QA_application = ''
    qa_httpres = False
    exp_httpres = False
    globally_restricted_site = False
    cr_rmq = False
    env_fwd_rmq = False
    env_fwd_rmq_queue = 'fwd_envelopes'
    col_sync_rmq = False
    col_sync_rmq_pub = False
    col_role_sync_rmq = False
    if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
        cr_api_url = 'http://cr.eionet.europa.eu/ping'
    else:
        cr_api_url = ''
    auth_middleware_url = ''
    bdr_registry_url = ''
    bdr_registry_token = ''
    bdr_registry_obligations = []
    er_fgas_obligations = []
    er_ods_obligations = []
    preliminary_obligations = []
    er_url = ''
    er_token = ''
    auth_middleware_recheck_interval = 300
    XLS_max_rows = 1000
    clamav_rest_host = ''
    clamd_host = ''
    clamd_port = 3310
    clamd_timeout = None
    clam_max_file_size = None
    dfm_type = 'dfm_xmlrpc'
    cm_type = 'cm_xmlrpc'

    def all_meta_types(self, interfaces=None):
        """
            What can you put inside me? Checks if the legal products are
            actually installed in Zope
        """
        types = ['Script (Python)', 'DTML Method',
                 'DTML Document', 'Page Template']

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

    security.declareProtected(view_management_screens, 'index_html')
    index_html = PageTemplateFile('zpt/engine_index', globals())

    # Setters for the Dataflows and Country Manager properties
    @DataflowsManager.dfm_type.setter
    def dfm_type(self, value):
        self._dfm_type = value

    @DataflowsManager.dfm_rest_url.setter
    def dfm_rest_url(self, value):
        self._dfm_rest_url = value

    @DataflowsManager.dfm_obl_url_prefix.setter
    def dfm_obl_url_prefix(self, value):
        self._dfm_obl_url_prefix = value

    @DataflowsManager.dfm_rest_timeout.setter
    def dfm_rest_timeout(self, value):
        self._dfm_rest_timeout = value

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

    @CountriesManager.cm_type.setter
    def cm_type(self, value):
        self._cm_type = value

    @CountriesManager.cm_rest_url.setter
    def cm_rest_url(self, value):
        self._cm_rest_url = value

    @CountriesManager.cm_rest_timeout.setter
    def cm_rest_timeout(self, value):
        self._cm_rest_timeout = value

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

    # security stuff
    security = ClassSecurityInfo()

    security.declarePublic('getDeploymentType')

    def getDeploymentType(self):
        return Products.Reportek.REPORTEK_DEPLOYMENT

    security.declareProtected('View', 'get_rod_obligations')

    def get_rod_obligations(self):
        """ Returns a sorted list of obligations from ROD
        """
        obligations = [(o.get('uri'), o.get('TITLE'))
                       for o in self.dataflow_rod()]
        data = []

        if obligations:
            data = sorted(obligations, key=itemgetter(1))

        return data

    _manage_properties = PageTemplateFile('zpt/engine/prop', globals())

    security.declareProtected(view_management_screens, 'manage_properties')

    def manage_properties(self):
        """ Manage the edited values """
        if self.REQUEST['REQUEST_METHOD'] == 'GET':
            return self._manage_properties()

        self.title = self.REQUEST.get('title', self.title)
        self.webq_url = self.REQUEST.get('webq_url', self.webq_url)
        self.webq_envelope_menu = self.REQUEST.get(
            'webq_envelope_menu', self.webq_envelope_menu)
        self.webq_before_edit_page = self.REQUEST.get(
            'webq_before_edit_page', self.webq_before_edit_page)
        self.QA_application = self.REQUEST.get(
            'QA_application', self.QA_application)
        self.qa_httpres = bool(self.REQUEST.get('qa_httpres', False))
        self.exp_httpres = bool(self.REQUEST.get('exp_httpres', False))
        self.globally_restricted_site = bool(
            self.REQUEST.get('globally_restricted_site',
                             self.globally_restricted_site))
        self.dfm_url = self.REQUEST.get('dfm_url', self.dfm_url)
        self.dfm_type = self.REQUEST.get('dfm_type', self.dfm_type)
        self.dfm_method = self.REQUEST.get('dfm_method', self.dfm_method)
        self.dfm_obl_url_prefix = self.REQUEST.get(
            'dfm_obl_url_prefix', self.dfm_obl_url_prefix)
        self.dfm_timeout = self.REQUEST.get('dfm_timeout', self.dfm_timeout)
        self.dfm_rest_url = self.REQUEST.get('dfm_rest_url', self.dfm_rest_url)
        self.dfm_rest_timeout = self.REQUEST.get(
            'dfm_rest_timeout', self.dfm_rest_timeout)

        self.cm_type = self.REQUEST.get('cm_type', self.cm_type)
        self.cm_url = self.REQUEST.get('cm_url', self.cm_url)
        self.cm_method = self.REQUEST.get('cm_method', self.cm_method)
        self.cm_timeout = self.REQUEST.get('cm_timeout', self.cm_timeout)
        self.cm_rest_url = self.REQUEST.get('cm_rest_url', self.cm_rest_url)
        self.cm_rest_timeout = self.REQUEST.get(
            'cm_rest_timeout', self.cm_rest_timeout)

        self.cr_api_url = self.REQUEST.get('cr_api_url', self.cr_api_url)
        self.cr_rmq = bool(self.REQUEST.get('cr_rmq', False))
        self.env_fwd_rmq = bool(self.REQUEST.get('env_fwd_rmq', False))
        self.env_fwd_rmq_queue = self.REQUEST.get('env_fwd_rmq_queue',
                                                  'fwd_envelopes')
        self.col_sync_rmq = bool(self.REQUEST.get('col_sync_rmq', False))
        self.col_sync_rmq_pub = bool(self.REQUEST.get('col_sync_rmq_pub',
                                                      False))
        self.col_role_sync_rmq = bool(self.REQUEST.get(
            'col_role_sync_rmq', False))
        if self.cr_api_url:
            self.contentRegistryPingger.api_url = self.cr_api_url
            self.contentRegistryPingger.cr_rmq = self.cr_rmq

        self.auth_middleware_url = self.REQUEST.get(
            'auth_middleware_url', self.auth_middleware_url)
        if self.auth_middleware_url:
            self.auth_middleware_recheck_interval = int(self.REQUEST.get(
                'auth_middleware_recheck_interval',
                self.auth_middleware_recheck_interval))
            self.authMiddleware.setServiceRecheckInterval(
                self.auth_middleware_recheck_interval)
        self.bdr_registry_url = self.REQUEST.get(
            'bdr_registry_url', self.bdr_registry_url)
        self.bdr_registry_token = self.REQUEST.get(
            'bdr_registry_token', self.bdr_registry_token)
        self.bdr_registry_obligations = self.REQUEST.get(
            'bdr_registry_obligations', self.bdr_registry_obligations)
        self.er_url = self.REQUEST.get('er_url', self.er_url)
        self.er_token = self.REQUEST.get('er_token', self.er_token)
        self.er_fgas_obligations = self.REQUEST.get(
            'er_fgas_obligations', self.er_fgas_obligations)
        self.er_ods_obligations = self.REQUEST.get(
            'er_ods_obligations', self.er_ods_obligations)
        xls_max_rows = self.REQUEST.get('xls_max_rows', self.XLS_max_rows)
        try:
            self.rdf_export_envs_age = int(
                self.REQUEST.get('rdf_export_envs_age', None))
        except ValueError:
            self.rdf_export_envs_age = None

        try:
            xls_max_rows = int(xls_max_rows)
        except ValueError:
            xls_max_rows = None
        self.XLS_max_rows = xls_max_rows

        self.preliminary_obligations = self.REQUEST.get(
            'preliminary_obligations', self.preliminary_obligations)

        self.clamav_rest_host = self.REQUEST.get(
            'clamav_rest_host', self.clamav_rest_host)
        self.clamd_host = self.REQUEST.get('clamd_host', self.clamd_host)
        try:
            self.clamd_port = int(self.REQUEST.get(
                'clamd_port', self.clamd_port))
        except ValueError:
            self.clamd_port = 3310
        try:
            self.clamd_timeout = float(self.REQUEST.get(
                'clamd_timeout', self.clamd_timeout))
        except (ValueError, TypeError):
            self.clamd_timeout = None
        try:
            self.clam_max_file_size = int(self.REQUEST.get(
                'clam_max_file_size', self.clam_max_file_size))
        except (ValueError, TypeError):
            self.clam_max_file_size = None
        self._AVService = AVService(self.clamav_rest_host,
                                    self.clamd_host,
                                    self.clamd_port,
                                    self.clamd_timeout,
                                    self.clam_max_file_size)
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            self.BDRRegistryAPI.set_base_url(self.bdr_registry_url)
            self.FGASRegistryAPI.set_base_url(self.er_url, self.er_token)

        # don't send the completed from back, the values set on self
        # must be used
        return self._manage_properties(
            manage_tabs_message="Properties changed")

    def canPingCR(self, envelope):
        """Check if a pingger is or can be created"""
        if getSecurityManager().checkPermission('Release Envelopes', envelope):
            return bool(self.contentRegistryPingger)

    @property
    def contentRegistryPingger(self):
        if not self.cr_api_url and not self.cr_rmq:
            return None
        pingger = getattr(self, '_contentRegistryPingger', None)
        if pingger:
            return pingger
        else:
            self._contentRegistryPingger = ContentRegistryPingger(
                self.cr_api_url, self.cr_rmq)
            return self._contentRegistryPingger

    @property
    def authMiddleware(self):
        if not self.auth_middleware_url:
            return None
        api = getattr(self, '_authMiddleware', None)
        if api:
            return api
        else:
            self._authMiddleware = BdrAuthorizationMiddleware(
                self.auth_middleware_url)
            return self._authMiddleware

    @property
    def FGASRegistryAPI(self):
        if not getattr(self, '_FGASRegistryAPI', None):
            self._FGASRegistryAPI = FGASRegistryAPI(
                'FGAS Registry', self.er_url, self.er_token)
        return self._FGASRegistryAPI

    @property
    def BDRRegistryAPI(self):
        if not getattr(self, '_BDRRegistryAPI', None):
            self._BDRRegistryAPI = BDRRegistryAPI(
                'BDR Registry', self.bdr_registry_url)
        return self._BDRRegistryAPI

    @property
    def AVService(self):
        if not getattr(self, '_AVService', None):
            self._AVService = AVService(self.clamav_rest_host,
                                        self.clamd_host,
                                        self.clamd_port,
                                        self.clamd_timeout)
        return self._AVService

    @property
    def cols_sync_history(self):
        return getattr(self, '_cols_sync_history', None)

    def get_col_sync_history(self, path=None):
        hist = self.cols_sync_history
        result = {}
        if not hist:
            self._cols_sync_history = self.init_cols_sync()
            transaction.commit()
            hist = self.cols_sync_history
        if path:
            result[path] = hist[path]
        else:
            result = hist
        return result

    def add_new_col_sync(self, path, m_time):
        if getattr(self, 'col_sync_rmq', False):
            self.cols_sync_history[path] = {
                'modified': m_time,
                'ack': PersistentList()
            }
            self._p_changed = True

    def set_depl_col_synced(self, depl, path, m_time):
        if getattr(self, 'col_sync_rmq', False):
            if self.cols_sync_history[path].get('modified') != m_time:
                self.add_new_col_sync(path, m_time)
            if depl not in self.cols_sync_history[path]['ack']:
                self.cols_sync_history[path]['ack'].append(depl)
                self._p_changed = True

    def get_registry(self, collection):
        registry = ''
        obl = collection.dataflow_uris
        if obl:
            if obl[0] in self.bdr_registry_obligations:
                registry = 'BDRRegistryAPI'
            else:
                for obl in self.dataflow_uris:
                    if (obl in self.er_ods_obligations
                            or obl in self.er_fgas_obligations):
                        registry = "FGASRegistryAPI"
                        break
                if (not getattr(collection, '_company_id', None)
                        and getattr(collection, 'old_company_id', None)):
                    registry = 'BDRRegistryAPI'
        return getattr(self, registry, None)

    security.declarePublic('getPartsOfYear')

    def getPartsOfYear(self):
        """ """
        return [''] + self.partofyear_table

    security.declareProtected(view_management_screens,
                              'update_company_collection')

    security.declareProtected(view_management_screens, 'change_ownership')

    def change_ownership(self, obj, newuser, deluser):
        """ """
        owner = obj.getOwner()  # get the actual owner
        if str(owner) == deluser.strip():
            owners = RepUtils.utConvertToList(owner.getId())
            user = self.acl_users.getUser(newuser)
            wrapped_user = user.__of__(self.acl_users)
            if wrapped_user:
                obj.changeOwnership(wrapped_user)  # change ownership
                obj.manage_delLocalRoles(owners)  # delete the old owner
                # set local role to the new user
                obj.manage_setLocalRoles(wrapped_user.getId(), ['Owner', ])

    def create_subcollection(self, parent_coll, title, dataflow_uris,
                             company_id=None, allow_envelopes=1,
                             allow_collections=1, suffix=None,
                             descr='', locality='', partofyear='',
                             year='', endyear=''):
        """Create subcollection in parent_coll"""
        for coll in parent_coll.objectValues('Report Collection'):
            if coll.title == title:
                return coll
        p_allow_c = getattr(parent_coll, 'allow_collections', 0)
        if not p_allow_c:
            parent_coll.allow_collections = 1
        sc_id = RepUtils.generate_id('col')
        if suffix:
            sc_id = ''.join([sc_id, suffix])
        parent_coll.manage_addCollection(dataflow_uris=dataflow_uris,
                                         country=parent_coll.country,
                                         id=sc_id, title=title,
                                         allow_collections=allow_collections,
                                         allow_envelopes=allow_envelopes,
                                         descr=descr, locality=locality,
                                         partofyear=partofyear,
                                         year=year, endyear=endyear)
        sc = getattr(parent_coll, sc_id)
        if company_id:
            sc = getattr(parent_coll, sc_id)
            sc.company_id = company_id
            sc.reindex_object()
        if not p_allow_c:
            parent_coll.allow_collections = 0
            parent_coll.reindex_object()
        return sc

    def create_fgas_collections(self, ctx, country_uri, company_id, name,
                                old_company_id=None):
        # Hardcoded obligations should be fixed and retrieved automatically
        parent_coll_df = ['http://rod.eionet.europa.eu/obligations/713']
        eq_imports_df = ['http://rod.eionet.europa.eu/obligations/765']
        bulk_imports_df = ['http://rod.eionet.europa.eu/obligations/764']
        if old_company_id:
            main_env_id = old_company_id
        else:
            main_env_id = company_id
        ctx.manage_addCollection(dataflow_uris=parent_coll_df,
                                 country=country_uri,
                                 id=main_env_id,
                                 title=name,
                                 allow_collections=1, allow_envelopes=1,
                                 descr='', locality='', partofyear='', year='',
                                 endyear='', old_company_id=old_company_id)
        coll = getattr(ctx, main_env_id)
        coll.company_id = company_id
        ei_id = ''.join([RepUtils.generate_id('col'), 'ei'])
        coll.manage_addCollection(
            dataflow_uris=eq_imports_df,
            country=country_uri,
            id=ei_id,
            title='Upload of verification documents (equipment importers)',
            allow_collections=0, allow_envelopes=1,
            descr='', locality='', partofyear='', year='', endyear='',
            old_company_id=old_company_id)
        bi_id = ''.join([RepUtils.generate_id('col'), 'bi'])
        coll.manage_addCollection(
            dataflow_uris=bulk_imports_df,
            country=country_uri,
            id=bi_id,
            title='''Upload of verification documents'''
                  ''' (HFC producers and bulk importers)''',
            allow_collections=0, allow_envelopes=1,
            descr='', locality='', partofyear='', year='', endyear='',
            old_company_id=old_company_id)
        ei = getattr(coll, ei_id)
        ei.company_id = company_id
        ei.reindex_object()
        bi = getattr(coll, bi_id)
        bi.company_id = company_id
        bi.reindex_object()
        coll.allow_collections = 0
        coll.reindex_object()

    def update_company_collection(self, company_id, domain, country,
                                  name, old_collection_id=None):
        """Update information on an existing old-type collection
           (say, 'fgas30001') mainly setting it's `company_id`
           (the id internal to Fgas Portal for instance)
           If no `old_collection_id` is provided then a new collection will be
           created with id=company_id=provided `company_id`.
           If `old_collection_id` is provided, the the collection must exist
           in the expected path deducted from the
           domain/country/old_collection_id. It's company_id will be updated.
           If `old_collection_id` does not exist at the expected location
           nothing will happen."""

        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            self.REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
            resp = {'status': 'fail',
                    'message': ''}

            coll_path = self.FGASRegistryAPI.buildCollectionPath(
                domain, country, company_id, old_collection_id)

            if not coll_path:
                msg = (
                    '''Cannot form path to collection, with details domain: '''
                    ''' %s, country: %s, company_id: %s, old_collection_id: '''
                    ''' %s.''' % (domain, country, company_id,
                                  old_collection_id))
                logger.warning(msg)
                # return failure (404) to the service calling us
                self.REQUEST.RESPONSE.setStatus(404)
                resp['message'] = msg
                return json.dumps(resp)

            path_parts = coll_path.split('/')
            obligation_id = path_parts[0]
            country_id = path_parts[1]
            coll_id = path_parts[2]
            try:
                country_folder_path = '/'.join([obligation_id, country_id])
                country_folder = self.restrictedTraverse(country_folder_path)
            except KeyError:
                msg = (
                    '''Cannot update collection %s. Path to collection '''
                    '''does not exist''' % coll_path)
                logger.warning(msg)
                # return 404
                self.REQUEST.RESPONSE.setStatus(404)
                resp['message'] = msg
                return json.dumps(resp)

            coll_id = company_id
            if old_collection_id:
                coll_id = old_collection_id

            coll = getattr(country_folder, coll_id, None)
            if not coll:
                try:
                    country_uri = getattr(country_folder, 'country', '')
                    if domain == 'FGAS':
                        self.create_fgas_collections(
                            country_folder,
                            country_uri,
                            company_id,
                            name,
                            old_company_id=old_collection_id)
                    else:
                        country_folder.manage_addCollection(
                            dataflow_uris=[
                                self.FGASRegistryAPI.DOMAIN_TO_OBLIGATION[
                                    domain]],
                            country=country_uri,
                            id=company_id,
                            title=name,
                            allow_collections=0, allow_envelopes=1,
                            descr='', locality='', partofyear='', year='',
                            endyear='', old_company_id=old_collection_id)
                    coll = getattr(country_folder, coll_id)
                except Exception as e:
                    msg = "Cannot create collection %s. " % coll_path
                    logger.warning(msg + str(e))
                    # return failure (404) to the service calling us
                    self.REQUEST.RESPONSE.setStatus(404)
                    resp['message'] = msg
                    return json.dumps(resp)
            coll.company_id = company_id
            if old_collection_id:
                coll.old_company_id = old_collection_id
            coll.reindex_object()
            resp['status'] = 'success'
            resp['message'] = ('Collection %s updated/created succesfully'
                               % coll_path)
            return json.dumps(resp)
        else:
            pass

    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
        security.declareProtected('Audit Envelopes', 'globalworklist')
        security.declareProtected('Audit Envelopes', 'searchfeedbacks')
        security.declareProtected('Audit Envelopes', 'resultsfeedbacks')
        security.declareProtected('Audit Envelopes', 'recent')
        security.declareProtected('Audit Envelopes', 'recent_released')
        security.declareProtected('Audit Envelopes', 'searchxml')
        security.declareProtected('Audit Envelopes', 'resultsxml')
        security.declareProtected('Audit Envelopes', 'search_dataflow')
        security.declareProtected('Audit Envelopes', 'search_dataflow_url')
        security.declareProtected('Audit Envelopes', 'lookup_last_delivery')
        security.declareProtected('Audit Envelopes', 'getEnvelopesInfo')
        security.declareProtected('Audit Envelopes', 'getSearchResults')
        security.declareProtected('Audit Envelopes', 'getUniqueValuesFor')
    else:
        security.declareProtected('View', 'globalworklist')
        security.declareProtected('View', 'searchfeedbacks')
        security.declareProtected('View', 'resultsfeedbacks')
        security.declareProtected('View', 'recent')
        security.declareProtected('View', 'recent_released')
        security.declareProtected('View', 'searchxml')
        security.declareProtected('View', 'resultsxml')
        security.declareProtected('View', 'search_dataflow')
        security.declareProtected('View', 'search_dataflow_url')
        security.declareProtected('View', 'lookup_last_delivery')
        security.declareProtected('View', 'getEnvelopesInfo')
        security.declareProtected('View', 'getSearchResults')
        security.declareProtected('View', 'getUniqueValuesFor')

    globalworklist = PageTemplateFile('zpt/engineGlobalWorklist', globals())
    searchfeedbacks = PageTemplateFile('zpt/engineSearchFeedbacks', globals())
    resultsfeedbacks = PageTemplateFile(
        'zpt/engineResultsFeedbacks', globals())
    recent = PageTemplateFile('zpt/engineRecentUploads', globals())
    recent_released = PageTemplateFile('zpt/engineRecentReleased', globals())
    searchxml = PageTemplateFile('zpt/engineSearchXml', globals())
    resultsxml = PageTemplateFile('zpt/engineResultsXml', globals())

    security.declarePublic('languages_box')
    languages_box = PageTemplateFile('zpt/languages_box', globals())

    _searchdataflow = PageTemplateFile('zpt/searchdataflow', globals())

    search_dataflow = PageTemplateFile('zpt/search_dataflow', globals())

    def get_query_args(self):
        """ Make a Catalog query object from the form in the REQUEST
        """
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
            return

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

        return catalog_args

    security.declareProtected('View', 'searchdataflow')

    def searchdataflow(self, batch_size=None):
        """Search the ZCatalog for Report Envelopes,
        show results and keep displaying the form """
        # show the initial default populated
        if 'sort_on' not in self.REQUEST:
            return self._searchdataflow()

        catalog_args = self.get_query_args()
        if not catalog_args:
            return

        envelopes = searchResults(self.Catalog, catalog_args)
        envelopeObjects = []
        for eBrain in envelopes:
            o = eBrain.getObject()
            if getSecurityManager().checkPermission('View', o):
                envelopeObjects.append(o)

        return self._searchdataflow(results=envelopeObjects,
                                    **self.REQUEST.form)

    security.declareProtected('View', 'get_df_objects')

    def get_df_objects(self, catalog_args):
        """ Query the catalog with the provided catalog_args
        """
        envelopeObjects = []
        if catalog_args:
            envelopes = searchResults(self.Catalog, catalog_args)

            for eBrain in envelopes:
                obj = eBrain.getObject()
                if getSecurityManager().checkPermission('View', obj):
                    files = []
                    for fileObj in obj.objectValues('Report Document'):
                        files.append({
                            "filename": fileObj.id,
                            "title": str(fileObj.absolute_url_path()),
                            "url": (str(fileObj.absolute_url_path())
                                    + "/manage_document")
                        })

                    accepted = True
                    for fileObj in obj.objectValues('Report Feedback'):
                        if (fileObj.title in (
                            "Data delivery was not acceptable",
                                "Non-acceptance of F-gas report")):
                            accepted = False

                    obligations = []
                    for uri in obj.dataflow_uris:
                        obligations.append(self.dataflow_lookup(uri)['TITLE'])

                    countryName = ''
                    if obj.meta_type == 'Report Envelope':
                        countryName = obj.getCountryName()
                    else:
                        try:
                            countryName = obj.localities_dict()[
                                obj.country]['name']
                        except KeyError:
                            countryName = "Unknown"

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
                        'obligation': (obligations[0] if obligations
                                       else "Unknown"),
                        'accepted': accepted
                    })

        return envelopeObjects

    def search_dataflow_url(self):
        """Search the ZCatalog for Report Envelopes,
        show results and keep displaying the form """

        catalog_args = self.get_query_args()
        if self.REQUEST.get('countries'):
            isos = self.REQUEST.get('countries')
            countries = filter(lambda c: c.get(
                'iso') in isos, self.localities_rod())
            catalog_args['country'] = [country['uri'] for country in countries]
        if self.REQUEST.get('obligations'):
            obligations = self.REQUEST.get('obligations')
            df_dict = {o['PK_RA_ID']: o['uri'] for o in self.dataflow_rod()}

            if not isinstance(obligations, list):
                obligations = [obligations]

            df_uris = [df_dict[obl] for obl in obligations]
            catalog_args['dataflow_uris'] = df_uris

        return json.dumps(self.get_df_objects(catalog_args))

    def assign_roles(self, user, role, local_roles, doc):
        local_roles.append(role)
        doc.manage_setLocalRoles(user, local_roles)

    def remove_roles(self, user, role, local_roles, doc):
        doc.manage_delLocalRoles(userids=[user, ])
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
            brains = searchResults(catalog, query)
            if not brains:
                message = fail_pattern % (
                    crole,
                    ', '.join(users),
                    self.localities_dict().get(
                        country, {'name': 'Unknown'})['name']
                )
                messages.append({
                    'status': 'fail',
                    'message': message
                })
                break
            collections = []
            for brain in brains:
                doc = brain.getObject()
                for user in users:
                    local_roles = [
                        role for role in doc.get_local_roles_for_userid(user)
                        if role != 'Client'
                    ]
                    modifier(user, crole, local_roles, doc)
                collections.append('<li>%s</li>' % doc.absolute_url())
            message = success_pattern % (
                crole, ', '.join(users), ''.join(collections))
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
        return [x for x in objs
                if x.meta_type in ['Report Collection',
                                   'Report Envelope',
                                   'Repository Referral']]

    security.declareProtected('View', 'getSitemap')

    def getSitemap(self, tree_root=None, tree_pre='tree'):
        from ZTUtils import SimpleTreeMaker
        if tree_root is None:
            tree_root = self.getPhysicalRoot()
        tm = SimpleTreeMaker(tree_pre)
        tm.setChildAccess(filter=self.sitemap_filter)
        tm.setSkip('')
        try:
            tree, rows = tm.cookieTree(tree_root)
        except ValueError:
            # invalid parameter; clear request and try again
            tree_root.REQUEST.form.clear()
            tree, rows = tm.cookieTree(tree_root)
        rows.pop(0)
        return {'root': tree, 'rows': rows}

    security.declareProtected('View', 'sitemap')
    sitemap = PageTemplateFile('zpt/engine/sitemap', globals())

    security.declarePublic('getWebQURL')

    def getWebQURL(self):
        """ return '' if there's no WebQuestionnaire attached to this
            application
        """
        return self.webq_url

    def getNotCompletedWorkitems(self, sortby, how, REQUEST=None):
        """ Loops for all the workitems that are in the 'active','inactive',
            'fallout' status and returns their list
        """
        catalog = getattr(self, constants.DEFAULT_CATALOG)

        query = {
            'meta_type': 'Workitem',
            'status': ['active', 'inactive', 'fallout'],
            'sort_on': sortby
        }

        if how == 'desc':
            query['sort_order'] = 'reverse'

        workitems = searchResults(catalog, query)

        if REQUEST is None:
            return [ob.getObject() for ob in workitems]

        else:
            paginator = DiggPaginator(
                workitems, 20, body=5, padding=2, orphans=5)

            try:
                page = int(REQUEST.get('page', '1'))
            except ValueError:
                page = 1

            try:
                workitems = paginator.page(page)
            except (EmptyPage, InvalidPage):
                workitems = paginator.page(paginator.num_pages)

            workitems.object_list = [ob.getObject()
                                     for ob in workitems.object_list]
            return workitems

    def zipEnvelopes(self, envelopes=[], REQUEST=None, RESPONSE=None):
        """ Zip several envelopes together with the metadata """
        import zip_content

        envelopes = RepUtils.utConvertToList(envelopes)

        temp_dir = RepUtils.get_zip_cache()
        tmpfile = tempfile.mktemp(".temp", dir=str(temp_dir))

        if len(envelopes) == 0:
            return

        # get envelopes
        env_objs = [self.unrestrictedTraverse(env, None) for env in envelopes]

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

                # write metadata.txt
                metadata_file = RepUtils.TmpFile(
                    zip_content.get_metadata_content(env_ob))
                outzd.write(str(metadata_file),
                            "%s/%s" % (env_name, 'metadata.txt'))

                # write README.txt
                readme_file = RepUtils.TmpFile(
                    zip_content.get_readme_content(env_ob))
                outzd.write(str(readme_file),
                            "%s/%s" % (env_name, 'README.txt'))

                # write history.txt
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
            except Exception:
                pass
        return objects

    def get_apps_wks(self, apps):
        catalog = self.unrestrictedTraverse(constants.DEFAULT_CATALOG)
        return catalog(meta_type='Workitem',
                       status='active',
                       activity_id=apps)

    def get_running_envelopes(self):
        catalog = self.unrestrictedTraverse(constants.DEFAULT_CATALOG)
        return catalog(meta_type='Report Envelope',
                       wf_status='forward')

    def get_forward_envelopes(self):
        """Return a JSON array with envelopes that are in forward wf_status."""
        brains = self.get_running_envelopes()
        result = []
        for brain in brains:
            result.append(brain.getURL())

        return self.jsonify(result)

    def runAutomaticApplications(self, p_applications, REQUEST=None):
        """ Searches for the active workitems of activities that need
            triggering on regular basis and calls triggerApplication for them
            Example of activity that needs further triggering: AutomaticQA

            Note: Since this method is called using a HTTP get,
                  the p_applications parameter cannot be a list, but a string.
                  To include more than one applications, separate them by ||
        """
        apps = p_applications.split('||')
        result = []
        brains = self.get_apps_wks(apps)

        for brain in brains:
            try:
                wk = brain.getObject()
                result.append(brain.getURL())
                wk.triggerApplication(wk.id, REQUEST)
                if not REQUEST:
                    transaction.commit()
            except Exception as e:
                msg = 'Error while triggering application for: '\
                      '{} - ({})'.format(brain.getURL(), str(e))
                logger.error(msg)

        return result

    def getWkAppsActive(self, p_applications, REQUEST=None):
        """ Searches for the active workitems of activities that need
            triggering on regular basis.

            Note: Since this method is called using a HTTP get,
                  the p_applications parameter cannot be a list, but a string.
                  To include more than one applications, separate them by ||
        """
        apps = p_applications.split('||')
        result = []
        brains = self.get_apps_wks(apps)

        for brain in brains:
            result.append(brain.getURL())

        return self.jsonify(result)

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

    def lookup_last_delivery(self, dataflow_uris, country,
                             reporting_period=''):
        """ Find the newest delivery with the same location and dataflows,
            but is older than the reporting_period in the argument
            If the reporting_period is not provided, finds them all until today
        """
        if reporting_period:
            l_reporting_period = DateTime(reporting_period)
        else:
            l_reporting_period = DateTime()
        l_deliveries = self._xmlrpc_search_delivery(
            dataflow_uris=dataflow_uris, country=country)
        if l_deliveries:
            # order all envelopes by start data in reverse and
            # filter only the ones that have the start date previous than
            # l_reporting_period
            return RepUtils.utSortByMethod(l_deliveries, 'getStartDate',
                                           l_reporting_period, 1)
        return []

    security.declareProtected(view_management_screens, 'harvestXforms')

    def harvestXforms(self):
        """ Deprecated - use (with care) load_from_dd() on each
            DataflowMappingsRecord object for similar result

            calls getXforms from the WebQ, and updates the
            DataflowMappingRecord table for the haswebform attribute
            To be called on regular basis by a cron job
        """
        raise DeprecationWarning(
            '''DataflowMappingRecord objects have been deprecated,'''
            ''' use DataflowMappingsRecord objects instead''')

    ###########################################################################
    #
    # Interface for the DMM integration
    #
    ###########################################################################

    def getEnvelopesInfo(self, obligation):
        """ Returns a list with all information about envelopes for a certain
            obligation, including the XML files inside
        """
        reslist = []
        l_catalog = getattr(self, constants.DEFAULT_CATALOG)
        l_params = {'meta_type': 'Report Envelope',
                    'dataflow_uris': obligation, 'released': 1}

        for obj in self.__getObjects(searchResults(l_catalog, l_params)):
            res = {'url': obj.absolute_url(0),
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
                    filelist.append(
                        [file.id, file.content_type, file.xml_schema_location,
                         file.title, restricted])
            res['files'] = filelist
            reslist.append(res)
        return reslist

    ###########################################################################
    #
    # Interface for the UNS integration
    #
    ###########################################################################

    security.declareProtected('View', 'subscriptions_html')
    subscriptions_html = PageTemplateFile(
        'zpt/engine/subscriptions', globals())

    security.declareProtected('View', 'uns_settings')
    uns_settings = PageTemplateFile('zpt/engine/unsinterface', globals())

    _migration_table = PageTemplateFile(
        'zpt/engine/migration_table', globals())

    security.declareProtected('View management screens', 'migration_table')

    def migration_table(self):
        """List all migrations applied to this deployment and their details"""
        do_update = self.REQUEST.form.get('update')
        if do_update:
            upd_module = importlib.import_module(
                '.'.join(['Products.Reportek.updates', do_update]))
            app = self.unrestrictedTraverse('/')
            upd_module.update(app)

        migs = getattr(self, constants.MIGRATION_ID)
        migs = sorted(migs.values(), key=lambda o: o.current_ts, reverse=True)
        done_rows = []
        todo_rows = []

        for migrationOb in migs:
            migrationItem = {
                'name': migrationOb.name,
                'version': migrationOb.version,
                'first': migrationOb.toDate(migrationOb.first_ts),
                'current': migrationOb.toDate(migrationOb.current_ts)
            }
            done_rows.append(migrationItem)
        upd_path = os.path.dirname(Products.Reportek.updates.__file__)
        upd_files = [f.split('.py')[0] for f in os.listdir(upd_path)
                     if os.path.isfile('/'.join([upd_path, f])) and
                     f.startswith('u') and len(f.split('.py')) > 1]
        applied = [upd.get('name') for upd in done_rows]
        for f in set(upd_files):
            applicable = False
            if f not in applied:
                upd_module = importlib.import_module(
                    '.'.join(['Products.Reportek.updates', f]))
                if REPORTEK_DEPLOYMENT in upd_module.APPLIES_TO:
                    applicable = True
                todo_rows.append({
                    'name': f,
                    'applicable': applicable,
                    'version': upd_module.VERSION,
                })
        todo_rows = sorted(todo_rows, key=lambda o: o.get('version'),
                           reverse=True)
        return self._migration_table(todo_migrationRows=todo_rows,
                                     done_migrationRows=done_rows)

    security.declareProtected(
        'View management screens', 'manage_editUNSInterface')

    def manage_editUNSInterface(self, UNS_server, UNS_username, UNS_password,
                                UNS_password_confirmation, UNS_channel_id,
                                UNS_notification_types, REQUEST=None):
        """ Edit the UNS related properties """
        if UNS_password != UNS_password_confirmation:
            if REQUEST is not None:
                REQUEST.RESPONSE.redirect(
                    '''uns_settings?manage_tabs_message='''
                    '''Password and confirmation do not match!''')
            return 0
        self.UNS_server = UNS_server
        self.UNS_username = UNS_username
        self.UNS_password = UNS_password
        self.UNS_channel_id = UNS_channel_id
        self.UNS_notification_types = [
            x for x in UNS_notification_types if x != '']
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(
                'uns_settings?manage_tabs_message=Saved changes')
        return 1

    def uns_notifications_enabled(self):
        return bool(os.environ.get('UNS_NOTIFICATIONS', 'off') == 'on')

    def rmq_connector_enabled(self):
        return bool(os.environ.get('RABBITMQ_ENABLED', 'off') == 'on')

    security.declarePrivate('get_uns_xmlrpc_server')

    def get_uns_xmlrpc_server(self):
        if self.uns_notifications_enabled():
            url = self.UNS_server + '/rpcrouter'
            if self.UNS_username:
                frag = '%s:%s@' % (self.UNS_username, self.UNS_password)
                url = url.replace('http://', 'http://' + frag)
                url = url.replace('https://', 'https://' + frag)
            return xmlrpclib.Server(url)

    def get_ecas_userid(self, username):
        ecas_path = '/acl_users/' + ECAS_ID
        try:
            ecas = self.unrestrictedTraverse(ecas_path, None)
            if ecas:
                return ecas.getEcasUserId(username)
        except Exception:
            logger.info('Unable to get ecas info')

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
            if l_server is not None:
                if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                    if self.get_ecas_userid(user_id):
                        user_id = self.get_ecas_userid(user_id)
                l_ret = l_server.UNSService.canSubscribe(self.UNS_channel_id,
                                                         user_id)
                return l_ret
        except Exception as e:
            logger.warning("Unable to contact UNS to check if {0} can "
                           "subscribe: {1}".format(user_id, e))
            return 0

    security.declareProtected('View', 'subscribeToUNS')

    def subscribeToUNS(self, filter_country='', dataflow_uris=[],
                       filter_event_types=[], REQUEST=None):
        """ Creates new or updates existing subscription to the specified
            If there is a request, returns a message, otherwise, returns
            (1, '') for success
            (0, error_description) for failure
        """
        l_filters = []
        if dataflow_uris not in [[], ['']]:
            for df_uri in dataflow_uris:
                df_title = self.dataflow_lookup(df_uri)['TITLE']
                if filter_country:
                    l_filters.append(
                        {'''http://rod.eionet.europa.eu/schema.rdf'''
                         '''#obligation''': df_title,
                         '''http://rod.eionet.europa.eu/schema.rdf'''
                         '''#locality''': filter_country})
                else:
                    l_filters.append(
                        {'''http://rod.eionet.europa.eu/schema.rdf'''
                         '''#obligation''': df_title})
        elif filter_country:
            l_filters.append(
                {'''http://rod.eionet.europa.eu/schema.rdf'''
                 '''#locality''': filter_country})

        l_filters_final = []
        if l_filters != []:
            for l_filter_event_type in filter_event_types:
                for l_filter in l_filters:
                    l_tmp = copy(l_filter)
                    l_tmp['''http://rod.eionet.europa.eu/schema.rdf'''
                          '''#event_type'''] = l_filter_event_type
                    l_filters_final.append(l_tmp)
        else:
            for l_filter_event_type in filter_event_types:
                l_filters_final.append(
                    {'''http://rod.eionet.europa.eu/schema.rdf'''
                     '''#event_type''': l_filter_event_type})

        try:
            l_server = self.get_uns_xmlrpc_server()
            if l_server is not None:
                user_id = self.REQUEST['AUTHENTICATED_USER'].getUserName()
                if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                    if self.get_ecas_userid(user_id):
                        user_id = self.get_ecas_userid(user_id)
                l_server.UNSService.makeSubscription(
                    self.UNS_channel_id, user_id, l_filters_final)
                if REQUEST is not None:
                    REQUEST.RESPONSE.redirect(
                        '''subscriptions_html?info_title=Information'''
                        '''&info_msg=Subscription made successfully''')
                return (1, '')
        except Exception as err:
            if REQUEST is not None:
                REQUEST.RESPONSE.redirect(
                    '''subscriptions_html?info_title=Error&info_msg=Your '''
                    '''subscription could not be made because of the '''
                    '''following error: %s''' % str(err))
            return (0, str(err))

    security.declareProtected('View', 'sendNotificationToUNS')

    def sendNotificationToUNS(self, envelope, notification_type,
                              notification_label, actor='system',
                              description=''):
        """ Sends events data to the specified UNS's push channel """
        res = 0
        try:
            l_server = self.get_uns_xmlrpc_server()
            # create unique notification identifier
            # Envelope URL + time + notification_type
            if l_server is not None and not envelope.restricted:
                l_time = str(time())
                l_id = "%s/events#ts%s" % (envelope.absolute_url(), l_time)
                l_res = []
                l_res.append(
                    [l_id, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                     'http://rod.eionet.europa.eu/schema.rdf#Workflowevent'])
                l_res.append(
                    [l_id, 'http://purl.org/dc/elements/1.1/title',
                     notification_label])
                if description:
                    l_res.append(
                        [l_id, 'http://purl.org/dc/elements/1.1/description',
                         description])
                l_res.append(
                    [l_id, 'http://purl.org/dc/elements/1.1/identifier',
                     envelope.absolute_url()])
                l_res.append(
                    [l_id, 'http://purl.org/dc/elements/1.1/date',
                     strftime('%Y-%b-%d %H:%M:%S')])
                # l_res.append(
                # [l_id, 'http://rod.eionet.europa.eu/schema.rdf#label',
                #  notification_label])
                l_dataflows = [self.dataflow_lookup(
                    x)['TITLE'] for x in envelope.dataflow_uris]
                for l_dataflow in l_dataflows:
                    l_res.append(
                        [l_id,
                         'http://rod.eionet.europa.eu/schema.rdf#obligation',
                         str(l_dataflow)])
                l_res.append(
                    [l_id, 'http://rod.eionet.europa.eu/schema.rdf#locality',
                     str(envelope.getCountryName())])
                l_res.append(
                    [l_id, 'http://rod.eionet.europa.eu/schema.rdf#actor',
                     actor])
                l_res.append(
                    [l_id, 'http://rod.eionet.europa.eu/schema.rdf#event_type',
                     notification_type])
                l_server.UNSService.sendNotification(
                    self.UNS_channel_id, l_res)
                res = 1
        except Exception as e:
            logger.warning("Unable to send UNS notification for: {0}: {1}"
                           .format(envelope.absolute_url(), e))
            res = 0
        return res

    security.declarePrivate('uns_subscribe_actors')

    def uns_subscribe_actors(self, actors, filters):
        l_server = self.get_uns_xmlrpc_server()
        for act in actors:
            try:
                if l_server is not None:
                    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                        if self.get_ecas_userid(act):
                            act = self.get_ecas_userid(act)
                    l_server.UNSService.makeSubscription(self.UNS_channel_id,
                                                         act, filters)
                    return 1
            except Exception as e:
                logger.warning("Unable to subscribe actors: {0} to UNS: {1}"
                               .format(actors, e))
                return 0

    ###########################################################################
    #
    # Utils
    #
    ###########################################################################

    def getListAsDict(self, ob_list=[], key=''):
        """ Get a list of dictionaries and return a tuple of (key, value)
        """
        groups = list(set([x.get(key, '') for x in ob_list]))
        groups.sort()
        for group in groups:
            yield group, [x for x in ob_list if x.get(key, '') == group]

    security.declareProtected('View', 'messageDialog')

    def messageDialog(self, message='', action='', REQUEST=None):
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

    security.declareProtected(
        'View management screens', 'manage_raise_exception')

    def manage_raise_exception(self):
        """ Generate exception to check that it's handled properly """
        raise ValueError('hello world')

    def getSearchResults(self, **kwargs):
        [kwargs.pop(el) for el in kwargs.keys() if kwargs[el] in [None, '']]
        catalog = searchResults(self.Catalog, kwargs)
        return catalog

    def getUniqueValuesFor(self, value):
        return self.Catalog.uniqueValuesFor(value)

    security.declarePublic('getAvailableLanguages')

    def getAvailableLanguages(self):
        """Get avalilable languages as their .mo files are found in
           locales/<ln_code> folders map them to their localized name.
        """
        negociator = getUtility(INegotiator)
        return negociator.getAvailableLanguages()

    security.declarePublic('getSelectedLanguage')

    def getSelectedLanguage(self):
        """Get selected language for this requester. The lang is selected by
        HTTP headers, cookie or stored default"""
        negociator = getUtility(INegotiator)
        return negociator.getSelectedLanguage(self.REQUEST)

    # public access
    # security.declarePublic('setCookieLanguage')
    def setCookieLanguage(self):
        """Sets the language of the site by cookie.
        negotiator will read this pref from cookie on every request
        """
        new_lang = self.REQUEST.get('chlang')
        if new_lang:
            new_lang = normalize_lang(new_lang)
            self.REQUEST.RESPONSE.setCookie(
                'reportek_language', new_lang, path='/')
            self.REQUEST.RESPONSE.redirect(self.REQUEST['HTTP_REFERER'])

    if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
        # make it accessible from browser
        security.declarePublic('getUserCollections')

        def getUserCollections(self):
            if not getattr(self, 'REQUEST', None):
                return []
            collections = {}
            username = self.REQUEST['AUTHENTICATED_USER'].getUserName()
            ecas = (self.unrestrictedTraverse('/acl_users/'
                    + constants.ECAS_ID))
            ecas_user_id = ecas.getEcasUserId(username)
            # these are disjunct, so it is safe to add them all together
            # normally only one of the lists will have results, but they could
            # be all empty too
            middleware_collections = {
                'rw': [],
                'ro': []
            }

            def get_colls(paths):
                """Paths is a dictionary {'paths': [], 'prev_paths': []}"""
                acc_paths = list(
                    set(paths.get('paths') + paths.get('prev_paths')))
                colls = {
                    'rw': [],
                    'ro': []
                }
                for colPath in acc_paths:
                    path = str(colPath) if colPath.startswith(
                        '/') else '/{}'.format(str(colPath))
                    try:
                        if colPath in paths.get('paths'):
                            colls['rw'].append(self.unrestrictedTraverse(path))
                        else:
                            colls['ro'].append(self.unrestrictedTraverse(path))
                    except Exception:
                        logger.warning("Cannot traverse path: %s" % (path))

                return colls

            logger.debug(
                '''Attempt to interrogate middleware for authorizations for'''
                ''' user:id %s:%s''' % (username, ecas_user_id))
            if ecas_user_id:
                user_paths = self.authMiddleware.getUserCollectionPaths(
                    ecas_user_id,
                    recheck_interval=self.authMiddleware.recheck_interval)
                colls = get_colls(user_paths)
                middleware_collections['rw'] += [
                    col for col in colls.get('rw')
                    if col not in middleware_collections['rw']]
                middleware_collections['ro'] += [
                    col for col in colls.get('ro')
                    if col not in middleware_collections['ro']]
            catalog = getattr(self, constants.DEFAULT_CATALOG)

            middleware_collections['rw'] += [
                br.getObject() for br in searchResults(
                    catalog, dict(id=username))
                if not br.getObject() in middleware_collections['rw']]

            # check BDR registry
            user_paths = self.BDRRegistryAPI.getCollectionPaths(username)
            colls = get_colls(user_paths)
            middleware_collections['rw'] += [
                col for col in colls.get('rw')
                if col not in middleware_collections['rw']]
            middleware_collections['ro'] += [
                col for col in colls.get('ro')
                if col not in middleware_collections['ro']]

            collections['Reporter'] = middleware_collections
            local_roles = ['Auditor', 'ClientFG',
                           'ClientODS', 'ClientCARS', 'ClientHDV']
            local_r_col = searchResults(catalog,
                                        dict(meta_type='Report Collection',
                                             local_unique_roles=local_roles))

            auditor = [br.getObject() for br in local_r_col
                       if 'Auditor' in br.local_defined_roles.get(username, [])
                       and len(br.getPath().split('/')) == 3]

            def is_client(l_roles):
                c_roles = ['ClientFG', 'ClientODS', 'ClientCARS', 'ClientHDV']
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

    security.declareProtected('View', 'xls_export')

    def xls_export(self, envelopes=None, catalog_args=None):
        """ XLS Export for catalog results
        """
        env_objs = []

        if envelopes:
            envelopes = RepUtils.utConvertToList(envelopes)
            env_objs = [self.unrestrictedTraverse(
                env, None) for env in envelopes]
        else:
            if not catalog_args:
                catalog_args = self.get_query_args()

                if self.REQUEST.get('sort_on'):
                    catalog_args['sort_on'] = self.REQUEST['sort_on']
                if self.REQUEST.get('sort_order'):
                    catalog_args['sort_order'] = self.REQUEST['sort_order']
            if catalog_args:
                brains = searchResults(self.Catalog, catalog_args)
                if brains:
                    env_objs = [brain.getObject() for brain in brains]

        wb = xlwt.Workbook()
        sheet = wb.add_sheet('Results')
        header = dict(RepUtils.write_xls_header(sheet))
        idx = 1  # Start from row 1

        for obj in env_objs:
            data = obj.get_export_data()
            if data:
                RepUtils.write_xls_data(data, sheet, header, idx)
                idx += 1
            # break if more than defined self.XLS_max_rows
            if self.XLS_max_rows:
                if idx > self.XLS_max_rows:
                    break

        return self.download_xls(wb, 'searchresults.xls')

    security.declareProtected('View', 'download_xls')

    def download_xls(self, wb, filename):
        """ Return an .xls file
        """
        xls = StringIO()
        wb.save(xls)
        xls.seek(0)

        self.REQUEST.response.setHeader(
            'Content-type', 'application/vnd.ms-excel; charset=utf-8'
        )
        self.REQUEST.response.setHeader(
            'Content-Disposition', 'attachment; filename={0}'.format(filename)
        )

        return xls.read()

    security.declareProtected('View management screens', 'zip_cache_cleanup')

    def zip_cache_cleanup(self, days=7):
        """Deletes files older than days."""
        return RepUtils.cleanup_zip_cache(days=days)

    security.declareProtected('View', 'jsonify')

    def jsonify(self, value, ensure_ascii=False):
        """Return the value as JSON"""
        self.REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
        return json.dumps(value, indent=4, ensure_ascii=ensure_ascii)

    security.declareProtected('View management screens', 'get_left_menu_tmpl')

    def get_left_menu_tmpl(self, username=None):
        """Get the left menu template for username."""
        sm = getSecurityManager()
        nobody = SpecialUsers.nobody
        left_hand_tmpl = self.unrestrictedTraverse('/left_menu_buttons')
        root = self.unrestrictedTraverse('/')
        tmp_user = None
        try:
            try:
                if username:
                    # Get the user with roles populated
                    tmp_user = root.acl_users.getUserById(username)
                    # If the user can't be found, use a nobody account
                if not tmp_user:
                    tmp_user = nobody

                newSecurityManager(None, tmp_user)
                # Get the template rendered for the username
                return left_hand_tmpl(context=root)
            except Exception:
                # If special exception handlers are needed, run them here
                raise
        finally:
            # Restore the old security manager
            setSecurityManager(sm)

    @ram.cache(lambda *args: time() // (60 * 60 * 12))  # 12 hours
    def get_main_cols(self):
        root = self.getPhysicalRoot()
        collections = root.objectValues('Report Collection')
        collections.sort(key=lambda x: x.title_or_id().lower())

        return collections

    def find_col_with_different_id(self, parent, metadata):
        """Find collection that may have a different id in the parent coll"""
        relevant = [
            'country',
            'dataflow_uris',
            'locality',
            'parent'
        ]
        result = None
        # Verify that we have metadata and that we have dataflow_uris in it
        if metadata:
            for coll in parent.objectValues('Report Collection'):
                if coll.title == metadata.get('title'):
                    result = coll
                    break
                # Run check only if the collection id is auto-generated
                if (coll.id.startswith('col') and len(coll.id) == 9
                        and metadata.get('dataflow_uris')):
                    differs = []
                    for attr in relevant:
                        if attr == 'parent':
                            coll_attr = '/'.join(
                                coll.getParentNode().getPhysicalPath())
                        else:
                            coll_attr = getattr(coll, attr, None)
                        if coll_attr != metadata.get(attr, None):
                            differs.append(True)
                            break
                    if not differs:
                        result = coll
                        break

        return result

    security.declareProtected('View management screens', 'sync_collection')

    def sync_collection(self):
        """Sync local collection from remote collection"""
        collection = self.REQUEST.form.get('collection')
        auth = (
            os.environ.get('COLLECTION_SYNC_USER', ''),
            os.environ.get('COLLECTION_SYNC_PASS', '')
        )
        results = []
        remote_depl = '://'.join([
            collection.split('://')[0],
            collection.split('://')[-1].split('/')[0]
        ])
        collections = collection.split('://')[-1].split('/')[1:]
        collection = ''
        for coll in collections:
            if coll:
                metadata = None
                collection = '/'.join([collection, coll])
                result = {
                    'action': None,
                }
                try:
                    url = '/'.join([remote_depl, collection, 'metadata'])
                    headers = {"Accept": "application/json"}
                    depl = self.REQUEST.SERVER_URL.split(
                        '://')[-1].split('.')[0]
                    data = {
                        'deployment': depl
                    }
                    res = requests.post(url, auth=auth, headers=headers,
                                        data=data)
                    if res.ok:
                        metadata = RepUtils.encode_dict(res.json())
                    elif res.status_code == 404:
                        # If the metadata can't be found, it means it has been
                        #  deleted, but we're not deleting it from the clients
                        pass
                    else:
                        msg = ('[SYNC] Unable to retrieve remote collection '
                               'metadata: {}'.format(res.status_code))
                        logger.error(msg)
                        return self.jsonify({'error': msg})
                except Exception as e:
                    msg = (
                        '[SYNC] Unable to retrieve remote collection '
                        'metadata: {}'.format(str(e)))
                    logger.error(msg)
                    return self.jsonify({'error': msg})
                if metadata:
                    local_c = self.unrestrictedTraverse(collection, None)
                    if not local_c:
                        pcpath = '/'.join(collection.split('/')[:-1])
                        local_diff_id = None
                        if pcpath:
                            parent = self.unrestrictedTraverse(pcpath)
                            local_diff_id = self.find_col_with_different_id(
                                parent,
                                metadata)
                        else:
                            continue
                    col_args = deepcopy(metadata)
                    for arg in ['local_roles', 'modification_time',
                                'parent', 'restricted']:
                        del col_args[arg]
                    if not local_c:
                        if not local_diff_id:
                            allow_colls = getattr(parent, 'allow_collections',
                                                  None)
                            chg_allow_colls = False
                            if not allow_colls:
                                parent.allow_collections = 1
                                chg_allow_colls = True
                            parent.manage_addCollection(**col_args)
                            if chg_allow_colls:
                                parent.allow_collections = 0
                            local_c = self.unrestrictedTraverse(collection)
                            logger.info(
                                "[SYNC] Created collection: {}".format(
                                    local_c.absolute_url()))
                            result['action'] = 'created'
                        else:
                            # Check if can_move_released prevents renaming
                            can_move = getattr(parent,
                                               'can_move_released', False)
                            chg_can_move = False
                            if not can_move:
                                chg_can_move = True
                                parent.can_move_released = True
                            # Rename existing collection with different id
                            parent.manage_renameObject(
                                local_diff_id.id, metadata.get('id'))
                            local_c = self.unrestrictedTraverse(collection)
                            if chg_can_move:
                                del parent.can_move_released
                            logger.info(
                                "[SYNC] Renamed collection: {}".format(
                                    local_c.absolute_url()))
                            result['action'] = 'modified'
                        logger.info(
                            "[SYNC] Created collection: {}".format(
                                local_c.absolute_url()))

                        result['collection'] = local_c.absolute_url()
                        result['metadata'] = col_args
                    else:
                        changed = False
                        for key in col_args:
                            if key == 'allow_referrals':
                                if local_c.are_referrals_allowed() != col_args[
                                        key]:
                                    changed = True
                                    break
                            elif getattr(local_c, key) != col_args[key]:
                                changed = True
                                break
                        if changed:
                            del col_args['id']
                            result['action'] = 'modified'
                            result['collection'] = local_c.absolute_url()
                            result['metadata'] = col_args
                            local_c.manage_editCollection(**col_args)
                            logger.info(
                                "[SYNC] Updated collection: {} - {}".format(
                                    local_c.absolute_url(), col_args))
                    roles_info = {}
                    # Sync roles
                    for roleinfo in metadata.get('local_roles'):
                        entity, roles = roleinfo
                        cur_roles = local_c.get_local_roles_for_userid(entity)
                        if tuple(roles) != cur_roles:
                            # We're not removing roles from clients
                            # logger.info(
                            #     "[SYNC] Removing roles: {} for {}".format(
                            #         cur_roles, entity))
                            # local_c.manage_delLocalRoles([entity])
                            if roles:
                                roles_info[entity] = roles
                                local_c.manage_setLocalRoles(entity, roles)
                                logger.info(
                                    "[SYNC] Setting roles: {} for {}".format(
                                        roles, entity))
                    if roles_info:
                        result['action'] = 'modified'
                        result['collection'] = local_c.absolute_url()
                        result['roles'] = roles_info
                    local_c.reindex_object()
                    results.append(result)
        return self.jsonify(results)

    def init_cols_sync(self):
        query = {
            'meta_type': 'Report Collection'
        }
        brains = searchResults(self.Catalog, query)
        data = PersistentMapping()
        for brain in brains:
            data[brain.getPath()] = {
                'modified': brain.bobobase_modification_time.HTML4(),
                'ack': PersistentList()
            }

        return data


Globals.InitializeClass(ReportekEngine)
