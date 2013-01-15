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
# Dragos Chirila, Finsiel Romania


""" XMLInfoParser object
    Parses XML files and extract DTD identifier or XML Schema URL.

$Id$"""

__version__='$Revision$'[11:-2]

from cStringIO import StringIO
import lxml.etree


def detect_schema(src):
    try:
        doc = lxml.etree.parse(src)
    except lxml.etree.XMLSyntaxError:
        return ''

    root = doc.getroot()

    location = root.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}'
                               'noNamespaceSchemaLocation')
    if location is not None:
        return location

    location = root.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}'
                               'schemaLocation')
    if location is not None:
        location_list = location.split()
        if len(location_list) > 1:
            return ' '.join(location_list[1::2]) # pick every 2nd item in list
        else:
            return location_list[0]

    location = doc.docinfo.system_url
    if location is not None:
        return location

    return ''


def detect_single_schema(src):
    result = detect_schema(src)
    if not result:
        return ''
    return result.split()[-1]
