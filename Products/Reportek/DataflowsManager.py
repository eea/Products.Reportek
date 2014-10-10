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

""" Module that handles the dataflows(obligations) information: dataflow_table

    The dataflow_table is an object in Zope root folder which returns
    a list of fictionaries containing, for each obligation:

        'terminated': Unicode string
        'SOURCE_TITLE': Unicode string
        'TITLE': Unicode string
        'source_uri': Unicode string
        'uri': Unicode string
        'details_url': Unicode string

"""

from XMLRPCMethod import XMLRPCMethod


class ServiceTemporarilyUnavailableException(Exception):
    pass


class DataflowsManager:
    """ Module that handles the dataflows(obligations) information: dataflow_table """

    def __init__(self):
        self.xmlrpc_method = XMLRPCMethod(
            title='Get activities from ROD',
            url='http://rod.eionet.europa.eu/rpcrouter',
            method_name='WebRODService.getActivities',
            timeout=10.0
        )

    def dataflow_rod(self):
        """ """
        return self.xmlrpc_method.call_method()

    def dataflow_table(self):
        """ """
        def inline_replace(x):
            x['uri'] = x['uri'].replace('eionet.eu.int', 'eionet.europa.eu')
            return x

        try:
            return map(inline_replace, self.dataflow_rod())
        except Exception:
            msg = "Reporting Obligations Database is temporarily unavailable," \
                  " please try again later"
            raise ServiceTemporarilyUnavailableException, msg

    def dataflow_dict(self):
        """ Converts the dataflow table into a dictionary """
        l_dfdict = {}
        for l_item in self.dataflow_table():
            l_dfdict[l_item['uri']] = l_item
        return l_dfdict

    def getDataflowDict(self, dataflow_uri):
        """ returns all properties of a dataflow as dictionary given the uri """
        try:
            return [x for x in self.dataflow_table()
                    if str(x['uri']) == dataflow_uri][0]
        except:
            return {'SOURCE_TITLE': 'Deleted', 'TITLE': 'Unknown obligation'}

    # Getters for the dataflow

    def isDataflowTerminated(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)['terminated']

    def getDataflowSourceTitle(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)['SOURCE_TITLE']

    def getDataflowTitle(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)['TITLE']

    def getDataflowSourceURI(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)['source_uri']

    def getDataflowDetailsURL(self, dataflow_uri):
        """ """
        return self.getDataflowDict(dataflow_uri)['details_url']
