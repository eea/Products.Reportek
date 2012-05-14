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

"""Constants/tables for keywords

Suggested usage: from tables import *
"""

# This structure is here to show you how to hardcode the list of obligations
# in case you don't want to use rod.eionet.europa.eu with XML-RPC. The list
# of obligations is grouped by SOURCE_TITLE. You must
# therefore do the same to your obligations. See how in dtml/collAdd.dtml.
#
# To use it, you create an External Method in Zope with Id: dataflow_table,
# Module Name: tables and Function Name: dataflow_table.

_dataflow_table = (
    {
    'PK_RA_ID': '130',
    'TITLE': 'EPER data reporting',
    'SOURCE_TITLE': 'EPER decision',
    },
    {
    'PK_RA_ID': '143',
    'TITLE': 'EPER national overview report',
    'SOURCE_TITLE': 'EPER decision',
    },
    {
    'PK_RA_ID': '136',
    'TITLE': 'EC Water Framework Directive Reporting Activity',
    'SOURCE_TITLE': 'Water framework directive'
    },
)

def dataflow_table():
    return _dataflow_table

_localities_table = (
{'iso': "",   'name': "Unspecified", 'fr':'Sans pays'},
)

def localities_table():
    return _localities_table
