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



# ZCatalog
DEFAULT_CATALOG = 'Catalog'

# ids of Root objects
# The name of the engine is hardcoded in DTML files
ENGINE_ID = 'ReportekEngine'
WORKFLOW_ENGINE_ID = 'WorkflowEngine'
CONVERTERS_ID = 'Converters'
QAREPOSITORY_ID = 'QARepository'
DATAFLOW_MAPPINGS = 'DataflowMappings'
APPLICATIONS_FOLDER_ID = 'Applications'
PING_ENVELOPES_KEY = 'PingEnvelopesStore'

# remote servers
WEBQ_XML_REPOSITORY = 'http://cdr.eionet.europa.eu/xmlexports/groundwater/'

CONTENT_TYPES = {'application/zip':'.zip',
                 'image/png':'.png',
                 'application/vnd.google-earth.kml+xml':'.kml'}

#Mime-types ignored by sentry logger
IGNORED_MIME_TYPES = [
    'application/octet-stream',
    'text/plain',
]
