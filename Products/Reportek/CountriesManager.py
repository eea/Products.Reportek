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

"""Module that handles the countries/localities dictionary: localities_table

'iso': string, 2 letter country code
'uri': string
'name': string
"""

from time import time

import requests
from plone.memoize import ram
from RepUtils import inline_replace
from XMLRPCMethod import XMLRPCMethod


class CountriesManager:
    """Module that handles the countries/localities dictionary"""

    def __init__(self):
        self.xmlrpc_localities = XMLRPCMethod(
            title="Get countries from ROD",
            url="http://rod.eionet.europa.eu/rpcrouter",
            method_name="WebRODService.getCountries",
            timeout=5.0,
        )

    @property
    def cm_title(self):
        xmlrpc_localities = getattr(self, "xmlrpc_localities", None)
        if xmlrpc_localities:
            return getattr(xmlrpc_localities, "title", None)

    @property
    def cm_url(self):
        xmlrpc_localities = getattr(self, "xmlrpc_localities", None)
        if xmlrpc_localities:
            return getattr(xmlrpc_localities, "url", None)

    @property
    def cm_method(self):
        xmlrpc_localities = getattr(self, "xmlrpc_localities", None)
        if xmlrpc_localities:
            return getattr(xmlrpc_localities, "method_name", None)

    @property
    def cm_timeout(self):
        xmlrpc_localities = getattr(self, "xmlrpc_localities", None)
        if xmlrpc_localities:
            return getattr(xmlrpc_localities, "timeout", None)

    def get_countries_rest(self):
        res = requests.get(
            self.cm_rest_url, timeout=self.cm_timeout, verify=False
        )
        if res.status_code == 200:
            prefix = "http://{}/spatial".format(
                self.cm_rest_url.split("://")[-1].split("/")[0]
            )
            countries = [
                {
                    "iso": c.get("twoLetter"),
                    "name": c.get("name"),
                    "uri": "{}/{}".format(prefix, c.get("spatialId")),
                }
                for c in res.json()
            ]
            return countries

    @property
    def cm_type(self):
        return getattr(self, "_cm_type", None)

    @property
    def cm_rest_url(self):
        return getattr(self, "_cm_rest_url", None)

    @property
    def cm_rest_timeout(self):
        return getattr(self, "_cm_rest_timeout", None)

    @ram.cache(lambda *args: time() // (60 * 60 * 12))
    def localities_rod(self):
        """ """
        if self.cm_type == "cm_rest":
            countries = self.get_countries_rest()
        else:
            countries = self.xmlrpc_localities.call_method()

        return countries

    def localities_table(self):
        """ """
        try:
            return [inline_replace(x) for x in self.localities_rod()]
        except Exception:
            return []

    @ram.cache(lambda *args: time() // (60 * 60 * 12))
    def localities_dict(self, country=None):
        """Converts the localities table into a dictionary"""
        dummy = {"uri": "", "name": "Unknown", "iso": "XX"}
        l_ldict = {}
        for l_item in self.localities_table():
            l_ldict[l_item["uri"]] = l_item
        if country:
            return l_ldict.get(country, dummy)
        return l_ldict
