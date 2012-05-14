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

class common:
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description

class package:
    def __init__(self):
        self.package_header = None
        self.applications = []
        self.participants = []
        self.process_definitions = []

class packageheader:
    def __init__(self):
        self.xpdlversion = 0.0
        self.vendor = ''
        self.created = '' # datetime
        self.version = ''
        self.author = ''
        self.codepage = ''
        self.countrykey = ''
        self.publicationstatus = ''
        self.conformanceclass = ''
        self.priorityunit = ''
        self.responsible = ''
        self.externalpackage = ''
        self.documentation = ''
        self.icon = ''
        self.costunit = ''

class participant(common):
    def __init__(self, id, name, description):
        common.__dict__['__init__'](self, id, name, description)
        self.extendedattributes = {}
        self.participant_type = ''

class application(common):
    def __init__(self, id, name, description):
        common.__dict__['__init__'](self, id, name, description)
        self.extendedattributes = {}
        self.formal_parameters = []

class formalparameter:
    def __init__(self):
        self.data_types = []

class datafield:
    def __init__(self):
        self.data_types = []

class datatype:
    def __init__(self):
        self.basic_types = []

class basictype:
    pass

class processheader:
    pass

class redefinableheader:
    pass

class workflowprocess(common):
    def __init__(self, id, name, description):
        common.__dict__['__init__'](self, id, name, description)
        self.extendedattributes = {}
        self.process_header = None
        self.redefinable_header = None
        self.formal_parameters = []
        self.data_fields = []
        self.activities = []
        self.transitions = []
        self.applications = []
        self.participants = []
        self.extended_attributes = ()

class transition:
    def __init__(self, id, name, from_, to):
        self.id = id
        self.name = name
        self.from_ = from_
        self.to = to
        self.extended_attributes = []
        self.condition = ''

class extendedattribute:
    pass

class tool:
    def __init__(self, id, type):
        self.id = id
        self.type = type
        self.actual_parameters = []

class subflow:
    def __init__(self, id, execution):
        self.id = id
        self.execution = execution
        self.actual_parameters = []

class loop:
    def __init__(self, kind):
        self.kind = kind


class activity(common):
    def __init__(self, id, name, description):
        common.__dict__['__init__'](self, id, name, description)
        self.extendedattributes = {}
        self.extended_attributes = []
        self.transition_restrictions = []
        self.automationmode = ''
        self.split = ''
        self.join = ''
        self.priority = ''
        self.limit = ''
        self.startmode = ''
        self.finishmode = ''
        self.deadline = ''
        self.condition = ''
        self.from_ = ''
        self.to = ''
        self.performer = ''
        self.tool = None
        self.subflow = ''
        self.activityset = ''
        self.actualparameter = ''
        self.documentation = ''
        self.icon = ''
        self.cost = ''
        self.duration = ''
        self.waitingtime = ''
        self.workingtime = ''

class transitionrestriction:
    def __init__(self):
        self.join = {}
        self.split = None

class splittransition:
    def __init__(self):
        self.transition_refs = []

class transitionref:
    pass