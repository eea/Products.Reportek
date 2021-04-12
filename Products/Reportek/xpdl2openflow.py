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

from StringIO import StringIO
from xml.sax.handler import ContentHandler
from xml.sax import *
from xpdldefinitions import *

xpdlns_1_0 = "http://www.wfmc.org/2002/XPDL1.0"


class saxstack_struct:
    def __init__(self, obj=None):
        self.obj = obj
        self.content = ''


class generic_tag:
    def __init__(self):
        pass


class xpdl_handler(ContentHandler):

    def __init__(self):
        self.root = None
        self.stack = []

    def startElement(self, name, attrs):
        """ """
        # get package
        if name == 'Package':
            obj = package()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        # get package header
        elif name == 'PackageHeader':
            obj = packageheader()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'XPDLVersion':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Vendor':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Created':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Version':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Author':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Codepage':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'CountryKey':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'PublicationStatus':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'ConformanceClass':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'PriorityUnit':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Responsible':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'ExternalPackage':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Documentation':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Icon':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'CostUnit':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        # get participants
        elif name == 'Participant':
            obj = participant(attrs.get('Id', u'').encode('utf-8'), attrs.get(
                'Name', u'').encode('utf-8'), attrs.get('Description', u'').encode('utf-8'))
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'ParticipantType':
            self.stack[-1].obj.participant_type = attrs.get(
                'Type', u'').encode('utf-8')
        elif name == 'ExtendedAttribute':  # merg la toate
            self.stack[-1].obj.extendedattributes[attrs.get('Name', u'').encode(
                'utf-8')] = attrs.get('Value', u'').encode('utf-8')
        # get application
        elif name == 'Application':
            obj = application(attrs.get('Id', u'').encode('utf-8'), attrs.get(
                'Name', u'').encode('utf-8'), attrs.get('Description', u'').encode('utf-8'))
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        # get processes
        elif name == 'WorkflowProcess':
            obj = workflowprocess(attrs.get('Id', u'').encode('utf-8'), attrs.get(
                'Name', u'').encode('utf-8'), attrs.get('Description', u'').encode('utf-8'))
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'ProcessHeader':
            obj = processheader()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Description':  # bun si in cazul lui activity
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Priority':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        # get activities
        elif name == 'Activity':
            obj = activity(attrs.get('Id', u'').encode('utf-8'), attrs.get('Name',
                                                                           u'').encode('utf-8'), attrs.get('Description', u'').encode('utf-8'))
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        # get implementation (No, Tool, SubFlow, Loop)
        elif name == 'Implementation':
            pass
        elif name == 'No':
            pass
        elif name == 'Tool':
            obj = tool(attrs.get('Id', u'').encode('utf-8'),
                       attrs.get('Type', u'').encode('utf-8'))
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'ActualParameter':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'SubFlow':
            obj = subflow(attrs.get('Id', u'').encode('utf-8'),
                          attrs.get('Execution', u'').encode('utf-8'))
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Loop':
            obj = loop(attrs.get('Kind', u'').encode('utf-8'))
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Performer':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        # start and finish modes
        elif name == 'Manual':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Automatic':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'StartMode':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'FinishMode':
            obj = generic_tag()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'TransitionRestriction':
            obj = transitionrestriction()
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Join':
            obj = generic_tag()
            obj.type = attrs.get('Type', u'').encode('utf-8')
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Split':
            obj = splittransition()
            obj.type = attrs.get('Type', u'').encode('utf-8')
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'TransitionRef':
            obj = transitionref()
            obj.id = attrs.get('Id', u'').encode('utf-8')
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Transition':
            obj = transition(attrs.get('Id', u'').encode('utf-8'), attrs.get('Name', u'').encode('utf-8'),
                             attrs.get('From', u'').encode('utf-8'), attrs.get('To', u'').encode('utf-8'))
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)
        elif name == 'Condition':
            obj = generic_tag()
            obj.type = attrs.get('Type', u'').encode('utf-8')
            stackObj = saxstack_struct(obj)
            self.stack.append(stackObj)

    def endElement(self, name):
        """ """
        if name == 'Package':
            self.root = self.stack[-1].obj
            self.stack.pop()
        elif name == 'PackageHeader':
            self.stack[-2].obj.packageheader = self.stack[-1].obj
            self.stack.pop()
        elif name == 'XPDLVersion':
            self.stack[-2].obj.xpdlversion = self.stack[-1].content
            self.stack.pop()
        elif name == 'Vendor':
            self.stack[-2].obj.vendor = self.stack[-1].content
            self.stack.pop()
        elif name == 'Created':
            self.stack[-2].obj.created = self.stack[-1].content
            self.stack.pop()
        elif name == 'Version':
            self.stack[-2].obj.version = self.stack[-1].content
            self.stack.pop()
        elif name == 'Author':
            self.stack[-2].obj.author = self.stack[-1].content
            self.stack.pop()
        elif name == 'Codepage':
            self.stack[-2].obj.codepage = self.stack[-1].content
            self.stack.pop()
        elif name == 'CountryKey':
            self.stack[-2].obj.countrykey = self.stack[-1].content
            self.stack.pop()
        elif name == 'PublicationStatus':
            self.stack[-2].obj.publicationstatus = self.stack[-1].content
            self.stack.pop()
        elif name == 'ConformanceClass':
            self.stack[-2].obj.conformanceclass = self.stack[-1].content
            self.stack.pop()
        elif name == 'PriorityUnit':
            self.stack[-2].obj.priorityunit = self.stack[-1].content
            self.stack.pop()
        elif name == 'Responsible':
            self.stack[-2].obj.responsible = self.stack[-1].content
            self.stack.pop()
        elif name == 'ExternalPackage':
            self.stack[-2].obj.externalpackage = self.stack[-1].content
            self.stack.pop()
        elif name == 'Documentation':
            self.stack[-2].obj.documentation = self.stack[-1].content
            self.stack.pop()
        elif name == 'Icon':
            self.stack[-2].obj.icon = self.stack[-1].content
            self.stack.pop()
        elif name == 'CostUnit':
            self.stack[-2].obj.costunit = self.stack[-1].content
            self.stack.pop()
        elif name == 'Participant':
            self.stack[-2].obj.participants.append(self.stack[-1].obj)
            self.stack.pop()
        elif name == 'ParticipantType':
            pass
        elif name == 'ExtendedAttribute':
            pass
        elif name == 'Application':
            self.stack[-2].obj.applications.append(self.stack[-1].obj)
            self.stack.pop()
        elif name == 'WorkflowProcess':
            self.stack[-2].obj.process_definitions.append(self.stack[-1].obj)
            self.stack.pop()
        elif name == 'ProcessHeader':
            self.stack[-2].obj.process_header = self.stack[-1].obj
            self.stack.pop()
        elif name == 'Description':
            self.stack[-2].obj.description = self.stack[-1].content
            self.stack.pop()
        elif name == 'Priority':
            self.stack[-2].obj.priority = self.stack[-1].content
            self.stack.pop()
        elif name == 'Activity':
            self.stack[-2].obj.activities.append(self.stack[-1].obj)
            self.stack.pop()
        elif name == 'Implementation':
            pass
        elif name == 'No':
            pass
        elif name == 'Tool':
            self.stack[-2].obj.tool = self.stack[-1].obj
            self.stack.pop()
        elif name == 'ActualParameter':
            self.stack[-2].obj.actual_parameters.append(self.stack[-1].content)
            self.stack.pop()
        elif name == 'SubFlow':
            self.stack[-2].obj.subflow = self.stack[-1].obj
            self.stack.pop()
        elif name == 'Loop':
            self.stack[-2].obj.loop = self.stack[-1].obj
            self.stack.pop()
        elif name == 'Performer':
            self.stack[-2].obj.performer = self.stack[-1].content
            self.stack.pop()
        elif name == 'StartMode':
            self.stack[-2].obj.startmode = self.stack[-1].obj
            self.stack.pop()
        elif name == 'FinishMode':
            self.stack[-2].obj.finishmode = self.stack[-1].obj
            self.stack.pop()
        elif name == 'Manual':
            self.stack[-2].obj.mode = 0
            self.stack.pop()
        elif name == 'Automatic':
            self.stack[-2].obj.mode = 1
            self.stack.pop()
        elif name == 'TransitionRestriction':
            self.stack[-2].obj.transition_restrictions = self.stack[-1].obj
            self.stack.pop()
        elif name == 'Join':
            self.stack[-2].obj.join = self.stack[-1].obj
            self.stack.pop()
        elif name == 'Split':
            self.stack[-2].obj.split = self.stack[-1].obj
            self.stack.pop()
        elif name == 'TransitionRef':
            self.stack[-2].obj.transition_refs.append(self.stack[-1].obj)
            self.stack.pop()
        elif name == 'Transition':
            self.stack[-2].obj.transitions.append(self.stack[-1].obj)
            self.stack.pop()
        elif name == 'Condition':
            self.stack[-2].obj.condition = self.stack[-1].content
            self.stack.pop()

    def characters(self, content):
        if len(self.stack) > 0:
            self.stack[-1].content += content.strip(' \t')


class xpdlparser:
    """ """

    def parseWorkflow(self, xml_string):
        """ """
        hndl = xpdl_handler()
        parser = make_parser()
        parser.setContentHandler(hndl)
        inpsrc = InputSource()
        inpsrc.setByteStream(StringIO(xml_string))
        try:
            parser.parse(inpsrc)
            return hndl
        except:
            return None
