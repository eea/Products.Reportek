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


""" XMLInfoParser object

Parses XML files and extract DTD identifier or XML Schema URL.

"""


# Python imports
from xml.sax.handler import ContentHandler
from xml.sax import *
from cStringIO import StringIO
from copy import copy


class WorkflowHandler(ContentHandler):
    def __init__(self):
        self.processes = []
        self.applications = []
        self.__process = {}
        self.__activities = []
        self.__transitions = []

    def startElement(self, name, attrs):
        #build a dictionary with all attributes
        attrs_dict = {}
        for attr in attrs.keys():
            attrs_dict[attr] = attrs[attr]
        #parse tags
        if name == 'process':
            self.__process = {}
            self.__activities = []
            self.__transitions = []
            self.__process.update(attrs_dict)
        elif name == 'application':
            self.__application = {}
            self.applications.append(attrs_dict)
        elif name == 'activity':
            self.__activities.append(attrs_dict)
        elif name == 'transition':
            self.__transitions.append(attrs_dict)

    def endElement(self, name):
        if name == 'process':
            self.__process['activities'] = self.__activities
            self.__process['transitions'] = self.__transitions
            self.processes.append(self.__process)

class sxpdlparser:
    """ """

    def __init__(self):
        """ """
        pass

    def ParseWorkflow(self, p_xml_string):
        """ """
        l_handler = WorkflowHandler()
        l_parser = make_parser()
        l_parser.setContentHandler(l_handler)
        l_inpsrc = InputSource()
        l_inpsrc.setByteStream(StringIO(p_xml_string))
        try:
            l_parser.parse(l_inpsrc)
            return l_handler
        except:
            return None
