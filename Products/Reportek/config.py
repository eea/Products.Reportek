# -*- coding: UTF-8 -*-
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
# Author(s):
# Daniel Mihai Bărăgan, Eau de Web

import os

__all__ = [
    'REPORTEK_DEPLOYMENT',
    'DEPLOYMENT_BDR',
    'DEPLOYMENT_CDR',
    'permission_manage_properties_collections',
    'permission_manage_properties_envelopes',
]

DEPLOYMENT_CDR = 'CDR'
DEPLOYMENT_BDR = 'BDR'

REPORTEK_DEPLOYMENT_KEY = 'REPORTEK_DEPLOYMENT'
REPORTEK_DEPLOYMENT = os.environ.get(REPORTEK_DEPLOYMENT_KEY, DEPLOYMENT_CDR)

if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
    permission_manage_properties_collections = 'Change Collections'
    permission_manage_properties_envelopes = 'Change Envelopes'
elif REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
    permission_manage_properties_collections = 'Manage properties'
    permission_manage_properties_envelopes = 'Manage properties'
