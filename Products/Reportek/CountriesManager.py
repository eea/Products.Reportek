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
from ZODB.POSException import ConflictError

from .DataflowsManager import ROD_TIMEOUT, RODUnavailable
from .RepUtils import inline_replace
from .XMLRPCMethod import XMLRPCMethod


class NoCountries(list):
    """The countries when ROD gave none, to know that they must not be kept."""


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
            self.cm_rest_url, timeout=self.cm_timeout or ROD_TIMEOUT, verify=True
        )
        if res.status_code != 200:
            raise RODUnavailable(self.cm_rest_url)
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

    def localities_rod(self):
        """The countries of ROD, none when ROD answers with an error status.

        That answer is not cached for 12 hours: the next call asks ROD again.
        """
        try:
            return self._localities_rod()
        except RODUnavailable:
            return NoCountries()

    @ram.cache(lambda *args: time() // (60 * 60 * 12))
    def _localities_rod(self):
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

    def localities_dict(self, country=None):
        """Converts the localities table into a dictionary"""
        try:
            countries = self._localities_dict()
        except ConflictError:
            raise
        except Exception:
            # ROD gave no countries: nothing is kept for 12 hours
            countries = {}
        return self._lookup_locality(countries, country)

    @ram.cache(lambda *args: time() // (60 * 60 * 12))
    def _localities_dict(self):
        countries = self.localities_rod()
        if isinstance(countries, NoCountries):
            raise RODUnavailable("no countries from ROD")
        return {item["uri"]: item for item in [inline_replace(x) for x in countries]}

    @staticmethod
    def _lookup_locality(l_ldict, country):
        dummy = {"uri": "", "name": "Unknown", "iso": "XX"}
        if country:
            return l_ldict.get(country, dummy)
        return l_ldict
