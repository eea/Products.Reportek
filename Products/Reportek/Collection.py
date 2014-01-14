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


"""Collection object
Collections are the basic container objects and are analogous to directories.
$Id$"""

__version__='$Revision$'[11:-2]

import time, types, os, string
import Products
from Products.ZCatalog.CatalogAwareness import CatalogAware
import Globals
import AccessControl.Role, webdav.Collection
from AccessControl.Permissions import manage_users
from AccessControl import getSecurityManager, ClassSecurityInfo
from OFS.Folder import Folder
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from DateTime import DateTime

# product imports
import Envelope
import RepUtils
import constants
import Referral

from CountriesManager import CountriesManager
from Toolz import Toolz

manage_addCollectionForm=PageTemplateFile('zpt/collection/add', globals())

def manage_addCollection(self, title, descr,
            year, endyear, partofyear, country, locality, dataflow_uris,
            allow_collections=0, allow_envelopes=0, id='',
            REQUEST=None):
    """Add a new Collection object
    """
    if id == '': id = RepUtils.generate_id('col')
    ob = Collection(id, title, year, endyear, partofyear, country, locality, descr, dataflow_uris, allow_collections, allow_envelopes)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)

class Collection(CatalogAware, Folder, CountriesManager, Toolz):
    """
    Collections are basic container objects that provide a standard
    interface for object management. Collection objects also implement
    a management interface and can have arbitrary properties.
    """

    meta_type='Report Collection'

    security = ClassSecurityInfo()

    manage_options = Folder.manage_options[:3] + \
        ( 
            {'label':'Settings', 'action':'manage_prop', 'help':('Reportek','Collection_Properties.stx')},
            {'label':'List of reporters', 'action':'get_users_list'},
        ) + Folder.manage_options[3:]

    def __init__(self, id, title='', year='', endyear='', partofyear='', country='', locality='', 
            descr='', dataflow_uris=[], allow_collections=0, allow_envelopes=0):
        """ constructor """
        self.id = id
        self.title = title
        try: self.year = int(year)
        except: self.year = ''
        try: self.endyear = int(endyear)
        except: self.endyear = ''
        if self.year == '' and self.endyear != '':
            self.year = self.endyear
        self.partofyear = partofyear
        self.country = country
        self.locality = locality
        self.descr = descr
        self.released = 0
        self.dataflow_uris = dataflow_uris
        self.allow_collections = allow_collections
        self.allow_envelopes = allow_envelopes

    security.declareProtected('Change Collections', 'manage_cutObjects')
    security.declareProtected('Change Collections', 'manage_copyObjects')
    security.declareProtected('Change Collections', 'manage_pasteObjects')
    security.declareProtected('Change Collections', 'manage_renameForm')
    security.declareProtected('Change Collections', 'manage_renameObject')
    security.declareProtected('Change Collections', 'manage_renameObjects')

    def __setstate__(self,state):
        Collection.inheritedAttribute('__setstate__')(self, state)
        if type(self.year) is types.StringType and self.year != '':
            try:
                self.year = int(self.year)
            except:
                self.year = ''

        if not hasattr(self,'endyear'):
            self.endyear = ''

        if hasattr(self,'main_issues'):
            del self.main_issues
        if hasattr(self,'broad'):
            del self.broad
        if hasattr(self,'narrow'):
            del self.narrow
        if hasattr(self,'media'):
            del self.media
        if hasattr(self,'response'):
            del self.response
        if hasattr(self,'pressures'):
            del self.pressures
        if hasattr(self,'impacts'):
            del self.impacts
        if hasattr(self,'keywords'):
            del self.keywords
        # The new URI-based obligation codes. Can now be multiple
        # Old reportek could only use ROD.
        if not hasattr(self,'dataflow_uris'):
            if self.dataflow:
                self.dataflow_uris = [ "http://rod.eionet.eu.int/obligations/" + self.dataflow ]
            else:
                self.dataflow_uris = []

    def all_meta_types( self, interfaces=None ):
        """
            What can you put inside me? Checks if the legal products are
            actually installed in Zope
        """
        types = ['LDAPUserFolder','User Folder', 'Script (Python)', 'DTML Method', 'DTML Document', 'XMLRPC Method']
        y = []

        if self.allow_collections:
            y.append({'name': 'Report Collection', 'action': 'manage_addCollectionForm', 'permission': 'Add Collections'})
            types.append('Repository Referral')
        if self.allow_envelopes:
            y.append({'name': 'Report Envelope', 'action': 'manage_addEnvelopeForm', 'permission': 'Add Envelopes'})
            if not self.allow_collections:
                types.append('Repository Referral')

        for x in Products.meta_types:
            if x['name'] in types:
                y.append(x)
        return y

    security.declareProtected('View management screens', 'manage_main_inh')
    manage_main_inh = Folder.manage_main
    Folder.manage_main._setName('manage_main')

    security.declareProtected('View', 'manage_main')
    def manage_main(self,*args,**kw):
        """ Define manage main to be context aware """

        if getSecurityManager().checkPermission('View management screens',self):
            return apply(self.manage_main_inh,(self,)+ args,kw)
        else:
            return apply(self.index_html,(self,)+ args, kw)

    security.declareProtected('Add Collections', 'manage_addCollectionForm')
    manage_addCollectionForm = manage_addCollectionForm

    security.declareProtected('Add Collections', 'manage_addCollection')
    manage_addCollection = manage_addCollection

    security.declareProtected('Add Envelopes', 'manage_addEnvelopeForm')
    manage_addEnvelopeForm = Envelope.manage_addEnvelopeForm

    security.declareProtected('Add Envelopes', 'manage_addEnvelope')
    manage_addEnvelope = Envelope.manage_addEnvelope

    security.declareProtected('Add Collections', 'manage_addReferralForm')
    manage_addReferralForm = Referral.manage_addReferralForm

    security.declareProtected('Add Collections', 'manage_addReferral')
    manage_addReferral = Referral.manage_addReferral

    security.declareProtected('View', 'index_html')
    index_html = PageTemplateFile('zpt/collection/index', globals())

    security.declareProtected('Change Collections', 'manage_prop')
    manage_prop = PageTemplateFile('zpt/collection/prop', globals())

    _get_users_list = PageTemplateFile('zpt/collUsers', globals())

    security.declareProtected(manage_users, 'get_users_list')
    def get_users_list(self, REQUEST):
        """ List accounts with the reporter and client roles for current folder and subfolders """
        from ldap.dn import explode_dn 
        role_param = REQUEST.get('role', '')
        users = {}
        global_users = {}
        catalog = getattr(self, constants.DEFAULT_CATALOG)
        # retrieve the global accounts
        ldap_user_folder = self.acl_users['ldapmultiplugin']['acl_users']
        for user_dn, roles in ldap_user_folder.getLocalUsers():
            user = explode_dn(user_dn,notypes=1)[0]
            for role in roles:
                if role_param and role_param in ['Reporter', 'Client']:
                    if role == role_param:
                        global_users[user] =[role]
                else:
                    if role in ['Reporter', 'Client']:
                        if global_users.has_key(user):
                            global_users[user].append(role)
                        else:
                            global_users[user] = [role]
        # retrieve the local accounts
        folders = catalog(meta_type=['Report Collection'], path=self.absolute_url(1))
        for folder in folders:
            context = catalog.getobject(folder.data_record_id_)
            for user, roles in context.get_local_roles():
                for role in list(roles):
                    if role_param and role_param in ['Reporter', 'Client']:
                        if role == role_param:
                            if users.has_key(user):
                                users[user].append([context, [role]])
                            else:
                                users[user] = [[context, [role]]]
                    else:
                        if role in ['Reporter', 'Client']:
                            if users.has_key(user):
                                users[user].append([context, list(roles)])
                            else:
                                users[user] = [[context, list(roles)]]
        return self._get_users_list(REQUEST, users=users, global_users=global_users)

    security.declarePublic('years')
    def years(self):
        """ Return the range of years the object pertains to """
        if self.year == '':
            return ''
        if self.endyear == '':
            return [ self.year ]
        if int(self.year) > int(self.endyear):
            return range(int(self.endyear),int(self.year)+1)
        else:
            return range(int(self.year),int(self.endyear)+1)

    def getEngine(self):
        """ Returns the Reportek engine object """
        return getattr(self, constants.ENGINE_ID)

    def getDataflowMappingsContainer(self):
        """ """
        return getattr(self, constants.DATAFLOW_MAPPINGS)

    security.declarePublic('num_terminated_dataflows')
    def num_terminated_dataflows(self):
        """ Returns the number of terminated dataflows """
        amount = 0
        for df in self.dataflow_uris:
            dfobj = self.dataflow_lookup(df)
            if dfobj.get('terminated','0') == '1':
                amount += 1
        return amount

    security.declarePublic('dataflow_lookup')
    def dataflow_lookup(self, uri):
        """ Lookup a dataflow on URI and return a dictionary of info """
        try:
            return self.dataflow_dict()[uri]
        except:
            return {'uri': uri,
                'details_url': '',
                'TITLE': 'Unknown/Deleted obligation',
                'terminated':'1',
                'SOURCE_TITLE': 'Unknown obligations',
                'PK_RA_ID': '0'}

    def dataflow_dict(self):
        """ Converts the dataflow table into a dictionary """
        l_dfdict = {}
        for l_item in self.dataflow_table():
            l_dfdict[l_item['uri']] = l_item
        return l_dfdict

    security.declareProtected('Change Collections', 'manage_editCollection')
    def manage_editCollection(self, title, descr,
            year, endyear, partofyear, locality, country='',
            allow_collections=0,allow_envelopes=0,dataflow_uris=[],REQUEST=None):
        """ Manage the edited values """
        self.title = title
        try: self.year = int(year)
        except: self.year = ''
        try: self.endyear = int(endyear)
        except: self.endyear = ''
        self.partofyear = partofyear
        self.country = country
        self.locality = locality
        self.descr = descr
        self.allow_collections = allow_collections
        self.allow_envelopes = allow_envelopes
        self.dataflow_uris = dataflow_uris
        # update ZCatalog
        self.reindex_object()
        if REQUEST is not None:
            return self.messageDialog(
                            message="The properties of %s have been changed!" % self.id,
                            action='./manage_main')

    security.declareProtected('Change Collections', 'manage_editCategories')
    def manage_editCategories(self, REQUEST=None):
        """ Manage the edited values """
        # update ZCatalog
        self.reindex_object()
        if REQUEST is not None:
            return self.messageDialog(
                            message="The categories of %s have been changed!" % self.id,
                            action='./manage_main')

    security.declareProtected('Change Collections', 'manage_changeCollection')
    def manage_changeCollection(self, title=None,
            year=None,endyear=None,partofyear=None,country=None,locality=None,
            descr=None,
            allow_collections=None, allow_envelopes=None,
            dataflow_uris=None,REQUEST=None):
        """ Manage the edited values """
        if title is not None:
            self.title=title
        if year is not None:
            self.year=int(year)
        if endyear is not None:
            self.endyear=int(endyear)
        if partofyear is not None:
            self.partofyear=partofyear
        if country is not None:
            self.country=country
        if locality is not None:
            self.locality=locality
        if descr is not None:
            self.descr=descr
        if allow_collections is not None:
            self.allow_collections=allow_collections
        if allow_envelopes is not None:
            self.allow_envelopes=allow_envelopes
        if dataflow_uris is not None:
            self.dataflow_uris=dataflow_uris
        # update ZCatalog
        self.reindex_object()
        if REQUEST is not None:
            return self.messageDialog(
                            message="The properties of %s have been changed!" % self.id,
                            action='./manage_main')

    security.declareProtected('Use OpenFlow', 'worklist')
    worklist =  PageTemplateFile('zpt/collection/worklist', globals())

    security.declareProtected('View', 'collection_tabs')
    collection_tabs = PageTemplateFile('zpt/collection/tabs', globals())

    security.declarePublic('getWorkitemsForWorklist')
    def getWorkitemsForWorklist(self, p_ret=None):
        """ Returns active and inactive workitems from all contained envelopes """
        if p_ret == None:
            p_ret = []
        # loop the envelopes
        for l_env in self.objectValues('Report Envelope'):
            p_ret.extend(l_env.getListOfWorkitems(['active', 'inactive']))
        # loop the subcollections
        for l_coll in self.objectValues('Report Collection'):
            l_coll.getWorkitemsForWorklist(p_ret)
        return p_ret

    def changeQueryString(self, p_query_string, p_parameter, p_value):
        """ given the QUERY_STRING part of an URL, the function searches for the 
            parameter p_parameter and gives it the value p_value
        """
        l_ret = ''
        try:
            l_encountered = 0
            for l_item in p_query_string.split('&'):
                l_param, l_value = l_item.split('=')
                if l_param == p_parameter:
                    l_ret = p_query_string.replace(p_parameter + '=' + l_value, p_parameter + '=' + str(p_value))
                    l_encountered = 1
            if l_encountered == 0:
                l_ret = p_query_string + '&' + p_parameter + '=' + p_value
        except:
            l_ret = p_parameter + '=' + str(p_value)
        return l_ret

    def changeQueryString2(self, p_query_string, p_parameter=None, p_value=None):
        """ given the QUERY_STRING part of an URL, the function does the following:
            - if type(p_parameter) is str  searches for the parameter p_parameter and gives it the value p_value
            - if type(p_parameter) is dict searches for all the keys in ditionary and gives them the values from the dictionary
            - if the p_value is in None the key is removed (works the same with dictionary)
        """
        l_query_array = self.changeQueryString2Dict(p_query_string, p_parameter, p_value)
        return '&'.join(str(x) + '=' + str(l_query_array[x]) for x in l_query_array.keys())


    def changeQueryString2Dict(self, p_query_string, p_parameter=None, p_value=None):
        """ returns the array for changeQueryString2 """
        #store the {key,value} pair in a dictionary
        l_query_array={}
        l_items = p_query_string.split('&')
        for i in l_items:
            l_temp = i.split('=')
            l_key   = l_temp[0]
            l_value = '='.join(l_temp[1:])
            l_query_array[l_key] = l_value

        if (type(p_parameter)==type({})):
            #if p_parameter is a dictionary pass through every element
            l_input_array = p_parameter
            for i in l_input_array.keys():
                if l_input_array[i] == None:
                    try:
                        del(l_query_array[i])
                    except:
                        pass
                else:
                    l_query_array[i] = l_input_array[i]
        else:
            
            if p_value == None:
                try:
                    del(l_query_array[p_parameter])
                except:
                    pass
            else:
                l_query_array[p_parameter] = p_value
        return l_query_array



    security.declareProtected('View', 'messageDialog')
    def messageDialog(self, message='', action='./manage_main', REQUEST=None):
        """ displays a message dialog """
        return self.message_dialog(message=message, action=action)

    message_dialog = PageTemplateFile('zpt/message_dialog', globals())

Globals.InitializeClass(Collection)
