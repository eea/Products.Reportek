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

from xml.sax.handler import ContentHandler, feature_namespaces
from xml.sax.saxlib import LexicalHandler
from xml.sax import handler, make_parser, InputSource
from cStringIO import StringIO
import lxml.etree

class InfoStructureHandler(ContentHandler, LexicalHandler):
    """ """

    __XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
    __SCHEMALOCATION_TAG = 'schemaLocation'
    __NONAMESPACESCHEMALOCATION_TAG = 'noNamespaceSchemaLocation'

    def __init__(self):
        """ """
        self.__isroot = 1
        self.xdi_info = 0
        self.xdi_name = None
        self.xdi_public_id = None
        self.xdi_system_id = None
        self.xsi_info = 0
        self.xsi_xmlns = {}
        self.xsi_schema_location = None

    def startDTD(self, name, public_id, system_id):
        """ get DTD information """
        self.xdi_info = 1
        self.xdi_name = name
        if public_id:
            self.xdi_public_id = public_id
            self.xdi_system_id = system_id
        elif system_id:
            self.xdi_system_id = system_id

    def startElementNS(self, name, qname, attributes):
        """ """
        if self.__isroot: # Only continue if we're in the root element
            self.__isroot = 0
            # Check no-namespace schema attribute
            value = attributes.get((self.__XSI_NS, self.__NONAMESPACESCHEMALOCATION_TAG))
            if value is not None:
                raise NotImplementedError
                self.xsi_info = 1
                self.xsi_schema_location = value.strip()
                return
            # Check schema attribute
            value = attributes.get((self.__XSI_NS, self.__SCHEMALOCATION_TAG))
            if value is not None:
                self.xsi_info = 1
                u = value.strip().split()
                if len(u) == 1:
                    raise NotImplementedError
                    self.xsi_schema_location = value.strip()
                else:
                    raise NotImplementedError
                    s = []
                    for x in xrange(1,len(u),2):
                        s.append(u[x])
                    self.xsi_schema_location = ' '.join(s)
                return

class XMLInfoParser:
    """ """

    def __init__(self):
        """ """
        pass

    def ParseXmlFile(self, p_xml_string):
        """ """
        l_info_handler = InfoStructureHandler()
        l_parser = make_parser()
        l_parser.setContentHandler(l_info_handler)
        l_parser.setProperty(handler.property_lexical_handler, l_info_handler)
        l_inpsrc = InputSource()
        l_inpsrc.setByteStream(StringIO(p_xml_string))
        try:
            l_parser.setFeature(feature_namespaces, 1)
            l_parser.parse(l_inpsrc)
            return l_info_handler
        except:
            return None


class ElementHandler(ContentHandler):
    """ """
    def __init__(self, element):
        self.inElement = 0
        self.theElement = element
        self.results = []

    def startElement(self, name, attributes):
        if name == self.theElement:
            self.inElement = 1

    def characters(self, data):
        if self.inElement:
            self.results.append(data)

    def endElement(self, name):
        if name == self.theElement:
            self.inElement = 0

class SearchElementParser:
    """ Retrieves the list of values for a given element
    """

    def __init__(self):
        """ """
        pass

    def parse_and_search(self, p_xml_string, p_element):
        """ """
        l_handler = ElementHandler(p_element)
        l_parser = make_parser()
        l_parser.setContentHandler(l_handler)
        l_inpsrc = InputSource()
        l_inpsrc.setByteStream(StringIO(p_xml_string))
        try:
            l_parser.parse(l_inpsrc)
            return l_handler.results
        except:
            return ''


def detect_schema(content):
    try:
        doc = lxml.etree.parse(StringIO(content))
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


def detect_single_schema(content):
    return detect_schema(content).split()[-1]
