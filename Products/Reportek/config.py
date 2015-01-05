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
    'DEPLOYMENT_BDR',
    'DEPLOYMENT_CDR',
    'DEPLOYMENT_MDR',
    'permission_manage_properties_collections',
    'permission_manage_properties_envelopes',
    'LOCAL_CONVERTERS_PORT',
]

DEPLOYMENT_CDR = 'CDR'
DEPLOYMENT_BDR = 'BDR'
DEPLOYMENT_MDR = 'MDR'

REPORTEK_DEPLOYMENT = os.environ.get('REPORTEK_DEPLOYMENT', DEPLOYMENT_CDR)
LOCAL_CONVERTERS_PORT = os.environ.get('LOCAL_CONVERTERS_PORT', '5000')

if REPORTEK_DEPLOYMENT in (DEPLOYMENT_CDR, DEPLOYMENT_MDR):
    permission_manage_properties_collections = 'Change Collections'
    permission_manage_properties_envelopes = 'Change Envelopes'
elif REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
    permission_manage_properties_collections = 'Manage properties'
    permission_manage_properties_envelopes = 'Manage properties'

if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
    REDIS_DATABASE = int(os.environ.get('REDIS_DATABASE', '0'))
    __all__.append('REDIS_DATABASE')
