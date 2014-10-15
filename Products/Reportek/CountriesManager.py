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

""" Module that handles the countries/localities dictionary: localities_table 

    'iso': string, 2 letter country code
    'uri': string
    'name': string
"""
from XMLRPCMethod import XMLRPCMethod
from RepUtils import inline_replace

class CountriesManager:
    """ Module that handles the countries/localities dictionary: localities_table """
    def __init__(self):
        self.xmlrpc_localities = XMLRPCMethod(
            title='Get countries from ROD',
            url='http://rod.eionet.europa.eu/rpcrouter',
            method_name='WebRODService.getCountries',
            timeout=5.0
        )

    def localities_rod(self):
        """ """
        return self.xmlrpc_localities.call_method()

    def localities_table(self):
        """ """
        try:
            return map(inline_replace, self.localities_rod())
        except Exception:
            return []

    def localities_dict(self, country=None):
        """ Converts the localities table into a dictionary """
        dummy = {'uri': '', 'name': 'Unknown', 'iso': 'XX'}
        l_ldict = {}
        for l_item in self.localities_table():
            l_ldict[l_item['uri']] = l_item
        if country:
            return l_ldict.get(country, dummy)
        return l_ldict

    def getCountryName(self, country_uri=None):
        """ Returns country name from the country uri
        """
        dummycounty = {'name':'Unknown'}
        if hasattr(self, 'country'):
            if self.country:
                return str(self.localities_dict().get(self.country, dummycounty)['name'])
            else:
                return ''
        else:
            try:
                return str([x['name'] for x in self.localities_table() if str(x['uri']) == country_uri][0])
            except:
                return ''

    def getCountryCode(self, country_uri=None):
        """ Returns country ISO code from the country uri
        """
        if hasattr(self, 'country'):
            if self.country:
                return str(self.localities_dict()[self.country]['iso'])
            return ''
        else:
            return str([x['iso'] for x in self.localities_table() if str(x['uri']) == country_uri][0])
