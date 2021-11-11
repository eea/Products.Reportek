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

import lxml.etree
__version__ = '$Revision$'[11:-2]


class SchemaError(ValueError):
    pass


def locations_str(locations):
    if isinstance(locations, basestring):
        return locations
    loc_list = [loc for loc in locations]
    return ' '.join(loc_list)


def absolute_location(location):
    return location.startswith('http://') or location.startswith('https://')


def detect_schema(src):
    """ Detect the schema location of this xml file.
    The schema may be missing completely in which case we return empty string
    However the xml must be well formmed and the schema location must be in
    absolute form;
    otherwise throw an SchemaError exception in order to reject the file.
    """
    try:
        iterparser = lxml.etree.iterparse(src, huge_tree=True)
        iterparser = iter(iterparser)
        event, element = next(iterparser)
        doc = element.getroottree()
        root = doc.getroot()
        # Copy the attributes into a dictionary
        root_attr = dict(root.attrib)

        # Loop over the elements in order to make sure it's well-formed
        for event, element in iterparser:
            element.clear()
    except lxml.etree.XMLSyntaxError as e:
        raise SchemaError('XML Syntax Error', *e.args)

    location = root_attr.get('{http://www.w3.org/2001/XMLSchema-instance}'
                             'noNamespaceSchemaLocation')
    if location:
        if absolute_location(location):
            return location
        else:
            raise SchemaError('Schema location is not a valid URL', location)

    location = root_attr.get('{http://www.w3.org/2001/XMLSchema-instance}'
                             'schemaLocation')
    if location is not None:
        location_list = location.split()
        # schemaLocation must come in pairs (schema, location)
        if location_list and len(location_list) % 2:
            raise SchemaError('schemaLocation must have pairs of values',
                              locations_str(location_list))
        # pick every 2nd item in list (the location)
        location_list = location_list[1::2]
        if location_list:
            location_list_valid = filter(absolute_location, location_list)
            if len(location_list) != len(location_list_valid):
                raise SchemaError('Schema location is not a valid URL',
                                  locations_str(set(location_list) - set(
                                    location_list_valid)))
        return ' '.join(location_list)

    location = doc.docinfo.system_url
    if location:
        if absolute_location(location):
            return location
        else:
            raise SchemaError('Schema location is not a valid URL', location)

    return ''


def detect_single_schema(src):
    result = detect_schema(src)
    if not result:
        return ''
    return result.split()[-1]
