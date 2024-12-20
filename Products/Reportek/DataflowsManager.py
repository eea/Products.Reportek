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

"""Module that handles the dataflows(obligations) information: dataflow_table

The dataflow_table is an object in Zope root folder which returns
a list of fictionaries containing, for each obligation:

    'terminated': Unicode string
    'SOURCE_TITLE': Unicode string
    'TITLE': Unicode string
    'source_uri': Unicode string
    'uri': Unicode string
    'details_url': Unicode string

"""

from time import time

import requests
from plone.memoize import ram
from RepUtils import inline_replace
from XMLRPCMethod import XMLRPCMethod

from Products.Reportek.constants import CUSTOM_DFLOWS


class ServiceTemporarilyUnavailableException(Exception):
    pass


class DataflowsManager:
    """Module that handles the dataflows(obligations) information:
    dataflow_table
    """

    def __init__(self):
        self.xmlrpc_dataflow = XMLRPCMethod(
            title="Get activities from ROD",
            url="http://rod.eionet.europa.eu/rpcrouter",
            method_name="WebRODService.getActivities",
            timeout=10.0,
        )

    @property
    def dfm_title(self):
        xmlrpc_dataflow = getattr(self, "xmlrpc_dataflow", None)
        if xmlrpc_dataflow:
            return getattr(xmlrpc_dataflow, "title", None)

    @property
    def dfm_url(self):
        xmlrpc_dataflow = getattr(self, "xmlrpc_dataflow", None)
        if xmlrpc_dataflow:
            return getattr(xmlrpc_dataflow, "url", None)

    @property
    def dfm_method(self):
        xmlrpc_dataflow = getattr(self, "xmlrpc_dataflow", None)
        if xmlrpc_dataflow:
            return getattr(xmlrpc_dataflow, "method_name", None)

    @property
    def dfm_timeout(self):
        xmlrpc_dataflow = getattr(self, "xmlrpc_dataflow", None)
        if xmlrpc_dataflow:
            return getattr(xmlrpc_dataflow, "timeout", None)

    @property
    def dfm_type(self):
        return getattr(self, "_dfm_type", None)

    @property
    def dfm_rest_url(self):
        return getattr(self, "_dfm_rest_url", None)

    @property
    def dfm_obl_url_prefix(self):
        return getattr(self, "_dfm_obl_url_prefix", None)

    @property
    def dfm_rest_timeout(self):
        return getattr(self, "_dfm_rest_timeout", None)

    def get_custom_dataflows(self):
        result = []
        custom_dfs = self.unrestrictedTraverse(CUSTOM_DFLOWS, None)
        if custom_dfs:
            result = custom_dfs()
        return result

    @ram.cache(lambda *args: time() // (60 * 60 * 12))
    def dataflow_rod(self):
        """ """
        if self.dfm_type == "dfm_rest":
            dflows = self.get_dataflows_rest()
        else:
            dflows = self.xmlrpc_dataflow.call_method()
        return dflows + self.get_custom_dataflows()

    def get_dataflows_rest(self):
        res = requests.get(
            self.dfm_rest_url, timeout=self.dfm_timeout, verify=False
        )
        dflows = []
        if res.status_code == 200:
            prefix = "{}/obligations".format(self.dfm_obl_url_prefix)
            dflows = [
                {
                    "LAST_UPDATE": c.get("lastUpdate").encode("utf-8"),
                    "PK_RA_ID": str(c.get("obligationId")),
                    "PK_SOURCE_ID": str(c.get("sourceId")),
                    "SOURCE_TITLE": c.get("sourceAlias"),
                    "TITLE": c.get("oblTitle"),
                    "details_url": "{}/{}".format(
                        prefix, c.get("obligationId")
                    ),
                    "terminated": (
                        "1"
                        if c.get("terminate").encode("utf-8") == "Y"
                        else "0"
                    ),
                    "uri": "{}/{}".format(prefix, c.get("obligationId")),
                }
                for c in res.json()
            ]

        return dflows

    def dataflow_table(self):
        """ """
        try:
            return map(inline_replace, self.dataflow_rod())
        except Exception:
            msg = (
                """Reporting Obligations Database is temporarily"""
                """unavailable, please try again later"""
            )
            raise ServiceTemporarilyUnavailableException(msg)

    def dataflow_dict(self):
        """Converts the dataflow table into a dictionary"""
        l_dfdict = {}
        for l_item in self.dataflow_table():
            l_dfdict[l_item["uri"]] = l_item
        return l_dfdict

    def dataflow_lookup(self, uri):
        """Lookup a dataflow on URI and return a dictionary of info"""
        try:
            return self.dataflow_dict()[uri]
        except KeyError:
            return {
                "uri": uri,
                "details_url": "",
                "TITLE": "Unknown/Deleted obligation",
                "terminated": "1",
                "SOURCE_TITLE": "Unknown obligations",
                "PK_RA_ID": "0",
            }

    def getDataflowDict(self, dataflow_uri):
        """returns all properties of a dataflow as dictionary given the uri"""
        try:
            return [
                x
                for x in self.dataflow_table()
                if str(x["uri"]) == dataflow_uri
            ][0]
        except Exception:
            return {"SOURCE_TITLE": "Deleted", "TITLE": "Unknown obligation"}

    # Getters for the dataflow

    def isDataflowTerminated(self, dataflow_uri):
        """ """
        return bool(int(self.getDataflowDict(dataflow_uri)["terminated"]))

    def getDataflowSourceTitle(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)["SOURCE_TITLE"]

    def getDataflowTitle(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)["TITLE"]

    def getDataflowSourceURI(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)["source_uri"]

    def getDataflowDetailsURL(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)["details_url"]
