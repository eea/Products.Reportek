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

import json
import logging
import operator
from datetime import datetime

import constants
import Envelope
import Globals
import Referral
import RepUtils
import requests
from AccessControl import ClassSecurityInfo, getSecurityManager
from AccessControl.Permissions import change_permissions, manage_users
from AccessControl.requestmethod import requestmethod
from Acquisition import aq_base
from DateTime import DateTime
from OFS.Folder import Folder
from Toolz import Toolz
from zope.event import notify
from zope.interface import implements
from zope.lifecycleevent import ObjectModifiedEvent

import Products
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek import DEPLOYMENT_BDR, REPORTEK_DEPLOYMENT
from Products.Reportek.CatalogAware import CatalogAware
from Products.Reportek.config import permission_manage_properties_collections
from Products.Reportek.constants import DEFAULT_CATALOG
from Products.Reportek.interfaces import ICollection
from Products.Reportek.rabbitmq import queue_msg
from Products.Reportek.RepUtils import DFlowCatalogAware, getToolByName

logger = logging.getLogger(__name__)
__version__ = "$Revision$"[11:-2]

manage_addCollectionForm = PageTemplateFile("zpt/collection/add", globals())


def manage_addCollection(
    self,
    title,
    descr,
    year,
    endyear,
    partofyear,
    country,
    locality,
    dataflow_uris,
    allow_collections=0,
    allow_envelopes=0,
    allow_referrals=0,
    id="",
    REQUEST=None,
    old_company_id=None,
):
    """Add a new Collection object"""
    if isinstance(self, Collection) and not self.allow_collections:
        raise ValueError(
            "The collection does not allow child collections to be created."
        )
    if id == "":
        id = RepUtils.generate_id("col")
    ob = Collection(
        id,
        title,
        year,
        endyear,
        partofyear,
        country,
        locality,
        descr,
        dataflow_uris,
        allow_collections,
        allow_envelopes,
    )
    if old_company_id:
        ob.old_company_id = old_company_id

    if isinstance(self, Collection):
        if allow_referrals != self.are_referrals_allowed():
            ob.prop_allowed_referrals = allow_referrals
        # If parent collection is restricted, set the child restricted
        if self.restricted:
            ob.restricted = True

    self._setObject(id, ob)

    if REQUEST is not None:
        # Return to containers's view
        return REQUEST.RESPONSE.redirect(self.absolute_url())


class BaseCollection(object):
    """BaseCollection class."""

    implements(ICollection)


class Collection(
    CatalogAware, Folder, Toolz, DFlowCatalogAware, BaseCollection
):
    """
    Collections are basic container objects that provide a standard
    interface for object management. Collection objects also implement
    a management interface and can have arbitrary properties.
    """

    meta_type = "Report Collection"
    security = ClassSecurityInfo()

    manage_options = (
        Folder.manage_options[:3]
        + (
            {
                "label": "Settings",
                "action": "manage_prop",
                "help": ("Reportek", "Collection_Properties.stx"),
            },
            {"label": "List of reporters", "action": "get_users_list"},
            {"label": "Company details", "action": "company_details"},
        )
        + Folder.manage_options[3:]
    )

    def __init__(
        self,
        id,
        title="",
        year="",
        endyear="",
        partofyear="",
        country="",
        locality="",
        descr="",
        dataflow_uris=[],
        allow_collections=0,
        allow_envelopes=0,
    ):
        """constructor"""
        self.id = id
        self.title = title
        try:
            self.year = int(year)
        except Exception:
            self.year = ""
        try:
            self.endyear = int(endyear)
        except Exception:
            self.endyear = ""
        if self.year == "" and self.endyear != "":
            self.year = self.endyear
        self.partofyear = partofyear
        self.country = country
        self.locality = locality
        self.descr = descr
        self.released = 0
        self.dataflow_uris = dataflow_uris
        self.allow_collections = allow_collections
        self.allow_envelopes = allow_envelopes

    security.declareProtected("Change Collections", "manage_cutObjects")
    security.declareProtected("Change Collections", "manage_copyObjects")
    security.declareProtected("Change Collections", "manage_pasteObjects")
    security.declareProtected("Change Collections", "manage_renameForm")
    security.declareProtected("Change Collections", "manage_renameObject")
    security.declareProtected("Change Collections", "manage_renameObjects")

    def all_meta_types(self, interfaces=None):
        """
        What can you put inside me? Checks if the legal products are
        actually installed in Zope
        """
        types = [
            "LDAPUserFolder",
            "User Folder",
            "Script (Python)",
            "DTML Method",
            "DTML Document",
            "XMLRPC Method",
        ]
        y = []

        if self.allow_collections:
            y.append(
                {
                    "name": "Report Collection",
                    "action": "manage_addCollectionForm",
                    "permission": "Add Collections",
                }
            )
            types.append("Repository Referral")
        if self.allow_envelopes:
            y.append(
                {
                    "name": "Report Envelope",
                    "action": "manage_addEnvelopeForm",
                    "permission": "Add Envelopes",
                }
            )
            if not self.allow_collections:
                types.append("Repository Referral")

        for x in Products.meta_types:
            if x["name"] in types:
                y.append(x)
        return y

    security.declareProtected("View management screens", "manage_main_inh")
    manage_main_inh = Folder.manage_main
    Folder.manage_main._setName("manage_main")

    security.declareProtected("View", "manage_main")

    def manage_main(self, *args, **kw):
        """Define manage main to be context aware"""
        if getSecurityManager().checkPermission(
            "View management screens", self
        ):
            return apply(self.manage_main_inh, (self,) + args, kw)
        else:
            return apply(self.index_html, (self,) + args, kw)

    security.declareProtected("Add Collections", "manage_addCollectionForm")
    manage_addCollectionForm = manage_addCollectionForm

    security.declareProtected("Add Collections", "manage_addCollection")
    manage_addCollection = manage_addCollection

    security.declareProtected("Add Envelopes", "manage_addEnvelopeForm")
    manage_addEnvelopeForm = Envelope.manage_addEnvelopeForm

    security.declareProtected("Add Envelopes", "manage_addEnvelope")
    manage_addEnvelope = Envelope.manage_addEnvelope

    security.declareProtected("Add Envelopes", "manage_addReferralForm")
    manage_addReferralForm = Referral.manage_addReferralForm

    security.declareProtected("Add Envelopes", "manage_addReferral")
    manage_addReferral = Referral.manage_addReferral

    macros = PageTemplateFile("zpt/collection/macros", globals()).macros

    security.declareProtected("View", "index_html")
    index_html = PageTemplateFile("zpt/collection/index", globals())

    security.declareProtected("Change Collections", "manage_prop")
    manage_prop = PageTemplateFile("zpt/collection/prop", globals())

    _get_users_list = PageTemplateFile("zpt/collection/users", globals())

    security.declareProtected("View", "company_details")
    company_details = PageTemplateFile(
        "zpt/collection/company_details", globals()
    )

    security.declareProtected("View", "other_reports")
    other_reports = PageTemplateFile("zpt/collection/other_reports", globals())

    def local_defined_roles(self):
        return self.__ac_local_roles__

    def local_defined_users(self):
        if isinstance(self.__ac_local_roles__, dict):
            return self.__ac_local_roles__.keys()

    def local_unique_roles(self):
        return set(
            role
            for roles in self.__ac_local_roles__.values()
            for role in roles
        )

    security.declareProtected(manage_users, "get_users_list")

    def get_users_list(self, REQUEST):
        """List accounts with the reporter and client roles for current
        folder and subfolders
        """
        from ldap.dn import explode_dn

        role_param = REQUEST.get("role", "")
        members = {}
        global_members = {}
        catalog = getattr(self, constants.DEFAULT_CATALOG)
        ldap_groups = self.getLDAPGroups()
        # retrieve the global accounts
        ldap_user_folder = self.acl_users["ldapmultiplugin"]["acl_users"]
        for user_dn, roles in ldap_user_folder.getLocalUsers():
            member = explode_dn(user_dn, notypes=1)[0]
            for role in roles:
                if role_param and role_param in ["Reporter", "Client"]:
                    if role == role_param:
                        global_members[member] = {
                            "type": "user",
                            "roles": [role],
                        }
                else:
                    if role in ["Reporter", "Client"]:
                        if member in global_members:
                            global_members[member]["roles"].append(role)
                        else:
                            global_members[member] = {
                                "type": "user",
                                "roles": [role],
                            }
        # retrieve the local accounts
        folders = catalog.searchResults(
            **dict(meta_type=["Report Collection"], path=self.absolute_url(1))
        )
        for folder in folders:
            context = catalog.getobject(folder.data_record_id_)
            for member, roles in context.get_local_roles():
                for role in list(roles):
                    if role_param and role_param in ["Reporter", "Client"]:
                        if role == role_param:
                            if member in members:
                                members[member]["roles"].append(
                                    [context, [role]]
                                )
                            else:
                                u_type = "user"
                                if member in ldap_groups:
                                    u_type = "group"
                                members[member] = {
                                    "type": u_type,
                                    "roles": [[context, [role]]],
                                }
                    else:
                        if role in ["Reporter", "Client"]:
                            if member in members:
                                members[member]["roles"].append(
                                    [context, list(roles)]
                                )
                            else:
                                u_type = "user"
                                if member in ldap_groups:
                                    u_type = "group"
                                members[member] = {
                                    "type": u_type,
                                    "roles": [[context, list(roles)]],
                                }

        return self._get_users_list(
            REQUEST,
            members=members,
            global_members=global_members,
            groups=bool(ldap_groups),
        )

    security.declarePublic("years")

    def years(self):
        """Return the range of years the object pertains to"""
        if self.year == "":
            return ""
        if self.endyear == "":
            return [self.year]
        if int(self.year) > int(self.endyear):
            return range(int(self.endyear), int(self.year) + 1)
        else:
            return range(int(self.year), int(self.endyear) + 1)

    def getEngine(self):
        """Returns the Reportek engine object"""
        return getattr(self, constants.ENGINE_ID)

    def getDataflowMappingsContainer(self):
        """ """
        return getattr(self, constants.DATAFLOW_MAPPINGS, None)

    def getCountryName(self, country_uri=None):
        """Returns country name from the country uri"""
        dummycounty = {"name": "Unknown", "iso": "xx"}
        engine = self.getEngine()
        if country_uri:
            try:
                return str(
                    [
                        x["name"]
                        for x in engine.localities_table()
                        if str(x["uri"]) == country_uri
                    ][0]
                )
            except Exception:
                return dummycounty["name"]
        return str(
            engine.localities_dict()
            .get(self.country, dummycounty)["name"]
            .encode("utf-8")
        )

    def getCountryCode(self, country_uri=None):
        """Returns country ISO code from the country uri"""
        dummycounty = {"name": "Unknown", "iso": "xx"}
        engine = self.getEngine()
        if country_uri:
            try:
                return str(
                    [
                        x["iso"]
                        for x in engine.localities_table()
                        if str(x["uri"]) == country_uri
                    ][0]
                )
            except Exception:
                return dummycounty["iso"]
        return str(
            engine.localities_dict().get(self.country, dummycounty)["iso"]
        )

    security.declareProtected("View", "get_dataflow_uris")

    def get_dataflow_uris(self):
        """Return a list of dataflow URIs for the collection.

        Returns:
            list: A list of dataflow URIs. For FGAS or ODS collections with
                terminated dataflows, returns only the active
                dataflow URI if present in collection's dataflows.
                Otherwise returns all collection's dataflow URIs.
        """
        try:
            # Get dataflow URIs with a default empty list
            dataflow_uris = getattr(self, "dataflow_uris", [])

            # If no terminated dataflows, return all dataflow URIs
            if not self.num_terminated_dataflows():
                return dataflow_uris

            # Special handling for FGAS/ODS collections
            if self.is_fgas() or self.is_ods():
                domain = "FGAS" if self.is_fgas() else "ODS"
                try:
                    engine = self.getEngine()
                    active_dataflow = engine.get_active_df(domain)

                    # Return active dataflow if it's in collection's dataflows
                    if active_dataflow in dataflow_uris:
                        return [active_dataflow]
                except AttributeError as e:
                    logger.error(
                        "Failed to get active FGAS dataflow: {}".format(str(e))
                    )

            return dataflow_uris

        except Exception as e:
            logger.error("Error retrieving dataflow URIs: {}".format(str(e)))
            return []

    security.declarePublic("num_terminated_dataflows")

    def num_terminated_dataflows(self):
        """Returns the number of terminated dataflows"""
        amount = 0
        engine = self.getEngine()
        for df in self.dataflow_uris:
            dfobj = engine.dataflow_lookup(df)
            if dfobj.get("terminated", "0") == "1":
                amount += 1
        return amount

    security.declareProtected(
        permission_manage_properties_collections, "manage_editCollection"
    )

    def manage_editCollection(
        self,
        title,
        descr,
        year,
        endyear,
        partofyear,
        locality,
        country="",
        allow_collections=0,
        allow_envelopes=0,
        allow_referrals=0,
        dataflow_uris=[],
        REQUEST=None,
    ):
        """Manage the edited values"""
        self.title = title
        try:
            self.year = int(year)
        except Exception:
            self.year = ""
        try:
            self.endyear = int(endyear)
        except Exception:
            self.endyear = ""
        self.partofyear = partofyear
        self.country = country
        self.locality = locality
        self.descr = descr
        self.allow_collections = allow_collections
        self.allow_envelopes = allow_envelopes
        if allow_referrals != self.are_referrals_allowed():
            self.prop_allowed_referrals = allow_referrals

        self.dataflow_uris = dataflow_uris
        # update ZCatalog
        self.reindexObject()
        notify(ObjectModifiedEvent(self))
        if REQUEST is not None:
            return self.messageDialog(
                message="The properties of %s have been changed!" % self.id,
                action="",
            )

    security.declareProtected("Change Collections", "manage_editCategories")

    def manage_editCategories(self, REQUEST=None):
        """Manage the edited values"""
        # update ZCatalog
        self.reindexObject()
        if REQUEST is not None:
            return self.messageDialog(
                message="The categories of %s have been changed!" % self.id,
                action="",
            )

    security.declareProtected(
        permission_manage_properties_collections, "manage_changeCollection"
    )

    def manage_changeCollection(
        self,
        title=None,
        year=None,
        endyear=None,
        partofyear=None,
        country=None,
        locality=None,
        descr=None,
        allow_collections=None,
        allow_envelopes=None,
        dataflow_uris=None,
        REQUEST=None,
    ):
        """Manage the edited values"""
        if title is not None:
            self.title = title
        if year is not None:
            self.year = int(year)
        if endyear is not None:
            self.endyear = int(endyear)
        if partofyear is not None:
            self.partofyear = partofyear
        if country is not None:
            self.country = country
        if locality is not None:
            self.locality = locality
        if descr is not None:
            self.descr = descr
        if allow_collections is not None:
            self.allow_collections = allow_collections
        if allow_envelopes is not None:
            self.allow_envelopes = allow_envelopes
        if dataflow_uris is not None:
            self.dataflow_uris = dataflow_uris
        # update ZCatalog
        self.reindexObject()
        notify(ObjectModifiedEvent(self))
        if REQUEST is not None:
            return self.messageDialog(
                message="The properties of %s have been changed!" % self.id,
                action="",
            )

    security.declareProtected("Use OpenFlow", "worklist")
    worklist = PageTemplateFile("zpt/collection/worklist", globals())

    security.declareProtected("View", "collection_tabs")
    collection_tabs = PageTemplateFile("zpt/collection/tabs", globals())

    security.declarePublic("getWorkitemsForWorklist")

    def getWorkitemsForWorklist(self, p_ret=None):
        """Returns active and inactive workitems from all child envelopes"""
        if p_ret is None:
            p_ret = []
        # loop the envelopes
        for l_env in self.objectValues("Report Envelope"):
            p_ret.extend(l_env.getListOfWorkitems(["active", "inactive"]))
        # loop the subcollections
        for l_coll in self.objectValues("Report Collection"):
            l_coll.getWorkitemsForWorklist(p_ret)
        return p_ret

    def changeQueryString(self, p_query_string, p_parameter, p_value):
        """given the QUERY_STRING part of an URL, the function searches for
        the parameter p_parameter and gives it the value p_value
        """
        l_ret = ""
        try:
            l_encountered = 0
            for l_item in p_query_string.split("&"):
                l_param, l_value = l_item.split("=")
                if l_param == p_parameter:
                    l_ret = p_query_string.replace(
                        p_parameter + "=" + l_value,
                        p_parameter + "=" + str(p_value),
                    )
                    l_encountered = 1
            if l_encountered == 0:
                l_ret = p_query_string + "&" + p_parameter + "=" + p_value
        except Exception:
            l_ret = p_parameter + "=" + str(p_value)
        return l_ret

    def changeQueryString2(
        self, p_query_string, p_parameter=None, p_value=None
    ):
        """given the QUERY_STRING part of an URL, the function does the
        following:
        - if type(p_parameter) is str  searches for the parameter
          p_parameter and gives it the value p_value
        - if type(p_parameter) is dict searches for all the keys
          in ditionary and gives them the values from the dictionary
        - if the p_value is in None the key is removed (works the same
          with dictionary)
        """
        l_query_array = self.changeQueryString2Dict(
            p_query_string, p_parameter, p_value
        )
        return "&".join(
            str(x) + "=" + str(l_query_array[x]) for x in l_query_array.keys()
        )

    def changeQueryString2Dict(
        self, p_query_string, p_parameter=None, p_value=None
    ):
        """returns the array for changeQueryString2"""
        # store the {key,value} pair in a dictionary
        l_query_array = {}
        l_items = p_query_string.split("&")
        for i in l_items:
            l_temp = i.split("=")
            l_key = l_temp[0]
            l_value = "=".join(l_temp[1:])
            l_query_array[l_key] = l_value

        if isinstance(p_parameter, dict):
            # if p_parameter is a dictionary pass through every element
            l_input_array = p_parameter
            for i in l_input_array.keys():
                if l_input_array[i] is None:
                    try:
                        del l_query_array[i]
                    except Exception:
                        pass
                else:
                    l_query_array[i] = l_input_array[i]
        else:
            if p_value is None:
                try:
                    del l_query_array[p_parameter]
                except Exception:
                    pass
            else:
                l_query_array[p_parameter] = p_value
        return l_query_array

    def localities_rod(self):
        engine = self.getEngine()
        if engine:
            return engine.localities_rod()

    def dataflow_rod(self):
        engine = self.getEngine()
        if engine:
            return engine.dataflow_rod()

    @property
    def company_id(self):
        company_id = getattr(self, "_company_id", None)
        if not company_id:
            company_id = getattr(self, "old_company_id", None)
        return company_id

    @company_id.setter
    def company_id(self, value):
        self._company_id = value

    def get_zope_company_meta(self):
        """Return the company meta attached to the collection"""

        def cname(obj):
            try:
                parent = obj.getParentNode()
            except Exception:
                return (None, None)
            if hasattr(obj, "_company_id") and not hasattr(
                parent, "_company_id"
            ):
                return (obj.title, obj.getId())
            else:
                return cname(parent)

        return cname(self)

    security.declareProtected("View", "messageDialog")

    def messageDialog(self, message="", action="", params=None, REQUEST=None):
        """displays a message dialog"""
        return self.message_dialog(
            message=message, action=action, params=params
        )

    message_dialog = PageTemplateFile("zpt/message_dialog", globals())

    security.declareProtected(change_permissions, "manage_addLocalRoles")

    @requestmethod("POST")
    def manage_addLocalRoles(self, userid, roles, REQUEST=None):
        super(Collection, self).manage_addLocalRoles(userid, roles)
        if REQUEST is not None:
            if hasattr(self, "reindexObject"):
                self.reindexObject()
            stat = "Your changes have been saved."
            return self.manage_listLocalRoles(self, REQUEST, stat=stat)

    security.declareProtected(change_permissions, "manage_setLocalRoles")

    @requestmethod("POST")
    def manage_setLocalRoles(self, userid, roles, REQUEST=None):
        super(Collection, self).manage_setLocalRoles(userid, roles)
        if REQUEST is not None:
            if hasattr(self, "reindexObject"):
                self.reindexObject()
            if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                if hasattr(aq_base(self), "reindexObjectSecurity"):
                    self.reindexObjectSecurity()
            stat = "Your changes have been saved."
            return self.manage_listLocalRoles(self, REQUEST, stat=stat)

    security.declareProtected(change_permissions, "manage_delLocalRoles")

    def manage_delLocalRoles(self, userids, REQUEST=None):
        """Remove all local roles for a user."""
        super(Collection, self).manage_delLocalRoles(userids)
        if REQUEST is not None:
            if hasattr(self, "reindexObject"):
                self.reindexObject()
            if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                if hasattr(aq_base(self), "reindexObjectSecurity"):
                    self.reindexObjectSecurity()
            stat = "Your changes have been saved."
            return self.manage_listLocalRoles(self, REQUEST, stat=stat)

    security.declareProtected("Add Envelopes", "get_company_data")

    def get_company_data(self):
        """Retrieve company data by interrogating the appropriate registry
        based on the collection's obligations
        """
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            engine = self.getEngine()
            registry = engine.get_registry(self)
            if self.company_id and registry:
                registry_name = getattr(registry, "registry_name", None)
                if registry_name == "FGAS Registry":
                    domain = "FGAS"
                    for obl in self.dataflow_uris:
                        if obl in engine.er_ods_obligations:
                            domain = "ODS"
                            break
                    data = registry.get_company_details(
                        self.company_id, domain=domain
                    )
                else:
                    # For BDR-Registry, get the domain from the top-level path
                    domain = (
                        self.getPhysicalPath()[1]
                        if len(self.getPhysicalPath()) > 1
                        else None
                    )
                    data = registry.get_company_details(
                        self.company_id, domain=domain
                    )
                if data:
                    data["registry"] = registry_name

                return data

    security.declareProtected("View", "company_status")

    def company_status(self):
        """Retrieve the status of the collection's associated company"""
        status = "DISABLED"
        data = self.get_company_data()
        if data:
            if not data.get("status"):
                if data.get("active"):
                    status = "VALID"
            else:
                return data.get("status", "N/A")

        return status

    security.declareProtected("View", "aggregated_licences")

    def aggregated_licences(self, all_years=False):
        """Return the ODS licences for the company"""
        res = {"licences": [], "result": "Ok", "message": ""}
        self.REQUEST.RESPONSE.setHeader("Content-Type", "application/json")
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            engine = self.getEngine()
            registry = engine.get_registry(self)

            if self.company_id and registry:
                registry_name = getattr(registry, "registry_name", None)
                if registry_name == "FGAS Registry":
                    domain = "FGAS"
                    for obl in self.dataflow_uris:
                        if obl in engine.er_ods_obligations:
                            domain = "ODS"
                            break

                    data = json.loads(self.REQUEST.get("BODY") or "{}")
                    if not isinstance(data, dict):
                        res["result"] = "Fail"
                        res["message"] = "Malformed body"
                    year = self.REQUEST.get("year")
                    if not year:
                        if all_years:
                            year = ""
                        elif "year" in data:
                            year = str(data.get("year"))
                            del data["year"]
                        else:
                            # Default to the previous year
                            year = str(DateTime().year() - 1)
                    response = registry.get_company_licences(
                        self.company_id,
                        domain=domain,
                        year=year,
                        data=json.dumps(data),
                    )
                    if response is not None:
                        if response.status_code != requests.codes.ok:
                            res["result"] = "Fail"
                            res["message"] = response.reason
                        else:
                            res.update(response.json())
                            res["result"] = "Ok"
                            res["message"] = ""
                    else:
                        res["result"] = "Fail"
                        res["message"] = None
        # FLOAT_REPR is deprecated in python 3.6
        json.encoder.FLOAT_REPR = (
            lambda o: ("%.7f" % o).rstrip("0") if o != int(o) else str(o)
        )

        return json.dumps(res, indent=4)

    security.declareProtected("View", "aggregated_licences_listing")

    def aggregated_licences_listing(self):
        """Licence list for use in the company detail view"""
        data = []
        raw_data = self.aggregated_licences(all_years=True)
        if raw_data:
            raw_data = json.loads(raw_data)
            data = raw_data["licences"]
        return json.dumps(data, indent=4)

    security.declareProtected("View", "process_agent_uses")

    def process_agent_uses(self):
        """Return the ODS process agent uses for the company"""
        res = {"result": "Ok", "message": ""}
        self.REQUEST.RESPONSE.setHeader("Content-Type", "application/json")
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            engine = self.getEngine()
            registry = engine.get_registry(self)

            if self.company_id and registry:
                registry_name = getattr(registry, "registry_name", None)
                if registry_name == "FGAS Registry":
                    domain = "FGAS"
                    for obl in self.dataflow_uris:
                        if obl in engine.er_ods_obligations:
                            domain = "ODS"
                            break

                    data = json.loads(self.REQUEST.get("BODY") or "{}")
                    if not isinstance(data, dict):
                        res["result"] = "Fail"
                        res["message"] = "Malformed body"
                    response = registry.get_company_paus(
                        self.company_id, domain=domain
                    )
                    if response is not None:
                        if response.status_code != requests.codes.ok:
                            res["result"] = "Fail"
                            res["message"] = response.reason
                        else:
                            res.update(response.json())
                            res["result"] = "Ok"
                            res["message"] = ""
                    else:
                        res["result"] = "Fail"
                        res["message"] = None

        return json.dumps(res, indent=4)

    security.declareProtected("View", "process_agent_uses_listing")

    def process_agent_uses_listing(self):
        """PAU listing used in company detail view"""
        data = []
        raw_data = self.process_agent_uses()
        if raw_data:
            raw_data = json.loads(raw_data)
            paus_per_year = raw_data.get(self.company_id)
            for year, paus in paus_per_year.items():
                for pau in paus:
                    pau["year"] = year
                    data.append(pau)
        return json.dumps(data, indent=4)

    security.declareProtected("View", "stocks")

    def stocks(self):
        """Return the ODS stocks for the company"""
        res = {"result": "Ok", "message": ""}
        self.REQUEST.RESPONSE.setHeader("Content-Type", "application/json")
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            engine = self.getEngine()
            registry = engine.get_registry(self)

            if self.company_id and registry:
                registry_name = getattr(registry, "registry_name", None)
                if registry_name == "FGAS Registry":
                    response = registry.get_company_stocks(self.company_id)
                    if response is not None:
                        if response.status_code != requests.codes.ok:
                            res["result"] = "Fail"
                            res["message"] = response.reason
                        else:
                            res.update(response.json())
                            res["result"] = "Ok"
                            res["message"] = ""
                    else:
                        res["result"] = "Fail"
                        res["message"] = None

        return json.dumps(res, indent=4)

    security.declareProtected("View", "stock_listing")

    def stock_listing(self):
        """Stock listing used in company detail view"""
        data = []
        raw_data = self.stocks()
        if raw_data:
            raw_data = json.loads(raw_data)
            stocks_per_year = raw_data.get(self.company_id)
            for year, stocks in stocks_per_year.items():
                for stock in stocks:
                    stock["year"] = year
                    data.append(stock)
        return json.dumps(data, indent=4)

    security.declareProtected("View", "company_ids_match")

    def company_ids_match(self):
        """Return the ODS stocks for the company"""
        res = {
            "match": 0,
        }
        self.REQUEST.RESPONSE.setHeader("Content-Type", "application/json")
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            new_id = self.REQUEST.get("new_id", "")
            old_id = self.REQUEST.get("old_id", "")
            new_company_id = getattr(self, "_company_id", "")
            old_company_id = getattr(self, "old_company_id", "")
            if new_id and new_company_id and old_id and old_company_id:
                if new_id == new_company_id and old_id == old_company_id:
                    res["match"] = 1

        return json.dumps(res, indent=4)

    def get_company_details_short(self):
        res = {}
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            engine = self.getEngine()
            registry = engine.get_registry(self)

            if self.company_id and registry:
                registry_name = getattr(registry, "registry_name", None)
                if registry_name == "FGAS Registry":
                    domain = "FGAS"
                    for obl in self.dataflow_uris:
                        if obl in engine.er_ods_obligations:
                            domain = "ODS"
                            break

                    res = registry.get_company_details_short(
                        self.company_id, domain=domain
                    )
        return res

    security.declareProtected("View", "company_details_short")

    def company_details_short(self):
        """Return the short company details"""
        self.REQUEST.RESPONSE.setHeader("Content-Type", "application/json")
        res = self.get_company_details_short()
        return json.dumps(res, indent=4)

    security.declareProtected("View", "company_types")

    def company_types(self):
        """Retrieve the types of the collection's associated company"""
        c_types = []
        data = self.get_company_data()
        if data:
            for c_type in data.get("types", "").split(","):
                if c_type:
                    c_types.append(c_type)

        return c_types

    security.declareProtected("View", "portal_registration_date")

    def portal_registration_date(self):
        """Retrieve the portal_registration_date of the collection's
        associated company
        """
        data = self.get_company_data()

        if data:
            reg_date = data.get("date_registered")
            strftime = "%Y-%m-%d %H:%M:%S"
            if not reg_date:
                reg_date = data.get("date_created")
                strftime = "%d/%m/%Y"

            try:
                pr_date = DateTime(datetime.strptime(reg_date, strftime))
            except ValueError:
                pr_date = None

            return pr_date

    def is_valid(self):
        """Return False if BDR deployment and associated company status is
        disabled, otherwise True
        """
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            company_status = self.company_status()

            if company_status:
                if company_status != "VALID":
                    return False

        return True

    def has_company_checks_failed(self):
        """Return True if BDR deployment and company checks failed"""
        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            raw_data = self.get_company_data()
            if raw_data:
                checks_passed = raw_data.get("check_passed", False)
                registry = raw_data.get("registry")
                if not checks_passed and registry == "FGAS Registry":
                    return True
        return False

    def allowed_envelopes(self):
        """Return False if the collection's associated company is disabled"""
        if self.has_company_checks_failed():
            return False

        return self.allow_envelopes

    def are_referrals_allowed(self):
        """Check through aquisition if referrals are allowed"""
        return getattr(self, "prop_allowed_referrals", 1)

    security.declareProtected("View management screens", "metadata")

    def metadata(self):
        """Collection metadata in JSON"""

        depl = self.REQUEST.form.get("deployment", None)
        if depl:
            engine = self.unrestrictedTraverse("ReportekEngine", None)
            engine.set_depl_col_synced(
                depl,
                "/".join(self.getPhysicalPath()),
                self.bobobase_modification_time().HTML4(),
            )

        result = {
            "id": self.id,
            "title": self.title,
            "descr": self.descr,
            "year": self.year,
            "endyear": self.endyear,
            "partofyear": self.partofyear,
            "country": self.country,
            "locality": self.locality,
            "dataflow_uris": [df for df in self.dataflow_uris],
            "allow_collections": self.allow_collections,
            "allow_envelopes": self.allow_envelopes,
            "allow_referrals": self.are_referrals_allowed(),
            "restricted": self.restricted,
            "parent": "/".join(self.getParentNode().getPhysicalPath()),
            "modification_time": self.bobobase_modification_time().HTML4(),
            "local_roles": self.get_local_roles(),
        }
        accept = self.REQUEST.environ.get("HTTP_ACCEPT")
        if accept == "application/json":
            self.REQUEST.RESPONSE.setHeader("Content-Type", "application/json")
            return json.dumps(result, indent=4)

        return result

    def notify_sync(self):
        engine = self.getEngine()
        if getattr(engine, "col_sync_rmq", False):
            queue_msg(self.absolute_url(), queue="collections_sync")

    security.declareProtected("Add Envelopes", "get_company_details")

    def get_company_details(self):
        """Company details tab view"""
        data = {}
        raw_data = self.get_company_data()
        if raw_data:
            alt_address = raw_data.get("address", {})
            alt_street_name = alt_address.get("street", "")
            alt_street_no = alt_address.get("number", "")
            alt_street = ""
            if alt_street_name:
                alt_street += alt_street_name
            if alt_street_no:
                alt_street = alt_street + " " + alt_street_no

            street = raw_data.get("addr_street", alt_street)
            city = raw_data.get(
                "addr_place1", raw_data.get("address", {}).get("city")
            )
            country = raw_data.get("country", raw_data.get("country_code"))
            data = {
                "name": raw_data.get("name"),
                "status": self.company_status(),
                "address": {"city": city, "street": street},
                "country": country.upper(),
                "vat": raw_data.get("vat_number", raw_data.get("vat")),
                "portal_registration_date": self.portal_registration_date(),
                "registry": {"FGAS Registry": "European Registry"}.get(
                    raw_data.get("registry"), raw_data.get("registry")
                ),
                "businessprofile": raw_data.get("businessprofile", []),
                "domain": raw_data.get("domain", ""),
            }

        return data

    def get_company_collections(self):
        """Get the company collections, to be used by other_reports for
        Managers
        """

        def get_colls(paths):
            """Paths is a dictionary {'paths': [], 'prev_paths': []}"""
            acc_paths = list(set(paths.get("paths") + paths.get("prev_paths")))
            colls = {"rw": [], "ro": []}
            for colPath in acc_paths:
                path = (
                    str(colPath)
                    if colPath.startswith("/")
                    else "/{}".format(str(colPath))
                )
                try:
                    if colPath in paths.get("paths"):
                        colls["rw"].append(self.unrestrictedTraverse(path))
                    else:
                        colls["ro"].append(self.unrestrictedTraverse(path))
                except Exception:
                    pass

            return colls

        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            engine = self.getEngine()
            registry = engine.get_registry(self)
            if self.company_id and registry:
                registry_name = getattr(registry, "registry_name", None)
                if registry_name == "FGAS Registry":
                    domain = "FGAS"
                    for obl in self.dataflow_uris:
                        if obl in engine.er_ods_obligations:
                            domain = "ODS"
                            break
                    c_data = registry.getCompanyDetailsById(
                        self.company_id, domain=domain
                    )
                    if c_data:
                        path = c_data.get("path", None)
                        paths = [path] if path else []
                        data = get_colls(
                            {
                                "paths": paths,
                                "prev_paths": c_data.get("previous_paths"),
                            }
                        )
                        return data

    def get_released_envelopes(self):
        path = "/".join(self.getPhysicalPath())
        query = {
            "meta_type": "Report Envelope",
            "released": 1,
            "sort_on": "reportingdate",
            "sort_order": "reverse",
            "path": {"query": path, "depth": 1},
        }
        catalog = getToolByName(self, DEFAULT_CATALOG, None)
        envs = catalog.searchResults(**query)

        return envs

    def get_latest_env_reportingdate(self):
        envs = self.get_children("Report Envelope", "reportingdate")
        if envs:
            return envs[0].reportingdate

    def get_children(self, m_types, sort_on, desc=1):
        objs = self.objectValues(m_types)
        objs.sort(key=operator.attrgetter(sort_on))
        if desc:
            objs.reverse()
        return objs

    def get_catalog_children(self, m_types, sort_on, sort_order="reverse"):
        path = "/".join(self.getPhysicalPath())
        query = {
            "meta_type": m_types,
            "sort_on": sort_on,
            "sort_order": sort_order,
            "path": {"query": path, "depth": 1},
        }
        catalog = getToolByName(self, DEFAULT_CATALOG, None)
        return catalog.searchResults(**query)

    security.declareProtected("View", "get_domain")

    def get_domain(self, df_type=None):
        """Return the domain type (FGAS or ODS)."""
        engine = self.getEngine()
        if engine:
            return engine.get_df_domain(self.dataflow_uris, df_type)

        return False

    security.declareProtected("View", "is_fgas")

    def is_fgas(self):
        """Return True if the collection is a FGAS collection."""

        return self.get_domain(df_type="undertakings") == "FGAS"

    security.declareProtected("View", "is_fgas_verification")

    def is_fgas_verification(self):
        """Return True if the collection is a FGAS verification collection."""

        return self.get_domain(df_type="verification") == "FGAS"

    security.declareProtected("View", "is_ods")

    def is_ods(self):
        """Return True if the collection is an ODS collection."""
        return self.get_domain(df_type="undertakings") == "ODS"

    security.declareProtected("View", "get_audit_collection")

    def get_audit_collection(self):
        """Return the audit subcollection."""
        if not self.is_fgas():
            return None
        try:
            return self.restrictedTraverse("col_fgas_ver")
        except AttributeError:
            return None

    security.declareProtected("View", "get_auditable_data_reports")

    def get_auditable_data_reports(self):
        """Return the auditable data reports."""
        if not self.is_fgas_verification():
            return []
        import plone.protect.interfaces
        from zope.interface import alsoProvides

        if hasattr(plone.protect.interfaces, "IDisableCSRFProtection"):
            alsoProvides(
                self.REQUEST, plone.protect.interfaces.IDisableCSRFProtection
            )
        # This is a bit weird here, since we expect this to be called
        # from envelopes from audit collection, which is a
        # subcollection of the FGAS collection.
        res = []
        rep_coll = self.getParentNode()
        envs = rep_coll.objectValues("Report Envelope")
        envs = [env for env in envs if env.is_auditable()]
        MKEYS = [
            "tr_09C",
            "tr_09F",
            "tr_13Bb",
            "tr_13D",
            "tr_5C_exempted_CO2e",
        ]
        for env in envs:
            docs = [
                r
                for r in env.objectValues("Report Document")
                if r.content_type == "text/xml"
            ]

            if not docs:
                continue

            # asume that there's only one element here
            doc = docs[0]
            metadata = doc.metadata

            mdata = {
                "id": env.id,
                "url": env.absolute_url(),
                "title": env.title,
                "year": env.year,
                "reportingdate": env.reportingdate.HTML4(),
            }
            for key in MKEYS:
                try:
                    if key in metadata:
                        amount = metadata.get(key, {}).get("Amount")
                        mdata[key] = (
                            int(amount) if amount is not None else None
                        )
                    else:
                        mdata[key] = None
                except (ValueError, KeyError, TypeError):
                    mdata[key] = None
            res.append(mdata)
        return res

    security.declareProtected("View", "is_newest_released")

    def is_newest_released(self, env_id):
        """Return True if it's the newest released envelope in context."""
        envs = self.get_released_envelopes()
        if envs and envs[0].id == env_id:
            return True
        return False

    @property
    def Description(self):
        if isinstance(self.descr, unicode):  # noqa: F821
            return self.descr.encode("utf-8")

        return self.descr

    def add_envelope(self, **kwargs):
        # Add envelope with the Manager role. To be called by Applications.
        RepUtils.execute_under_special_role(
            self, "Manager", self.manage_addEnvelope, **kwargs
        )

    security.declareProtected("View management screens", "set_restricted")

    def set_restricted(self, permission, roles, acquire=0, REQUEST=None):
        """
        Restrict access to the named objects.
        Figure out what roles exist, but don't give access to
        anonymous and authenticated
        """
        self.manage_permission(
            permission_to_manage=permission, roles=roles, acquire=acquire
        )
        self.restricted = True
        self.reindexObject()

    @property
    def restricted(self):
        return getattr(self, "_restricted", False)

    @restricted.setter
    def restricted(self, value):
        self._restricted = bool(value)


Globals.InitializeClass(Collection)
