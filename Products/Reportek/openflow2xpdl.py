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

# -----------------------------------------------------------------------------
# Name:        openflow2xpdl.py
# Purpose:     Create XPDL files using OpenFlow info
#              XPDL format was standarized by WfMC: www.wfmc.org
#
# Author:      Mikel Larreategi Arana
#
# Created:
# RCS-ID:      $Id$
# Copyright:   (c) 2003
# Licence:     GPL
# -----------------------------------------------------------------------------

import time
from xml.dom import minidom


class OpenFlow2Xpdl:

    def __init__(self, folder, xmldoc, of):
        """ Metodo eraikitzailea - constructor """
        self.folder = folder
        self.xmldoc = xmldoc
        self.of = of

    def gehituErabiltzaileak(self):
        """ Erabiltzaileak eta rolak gehitzeko metodoa - Add users/roles """

        # erabiltzaile guztiak gordeko dituen elementua sortu
        # create the element to contain participants
        erabiltzailea = self.xmldoc.createElement('Participants')

        # rol bakoitzeko
        # for each role
        for k in self.of.valid_roles():
            rol = self.xmldoc.createElement('Participant')
            rol.setAttribute('Id', k)
            rol.setAttribute('Name', k)
            mota = self.xmldoc.createElement('ParticipantType')
            mota.setAttribute('Type', 'ROLE')
            rol.appendChild(mota)
            erabiltzailea.appendChild(rol)

        # Erabiltzaileen izenak gordetzen dituen egituratik izen horiek lortu,
        # egituraren izena beti izango da 'acl_users'
        # Get usernames from UserFolder. UserFolder's name is always acl_users
#        for i in self.of.acl_users.getUserNames():
#            user = self.xmldoc.createElement('Participant')
#            user.setAttribute('Id', i)
#            user.setAttribute('Name', i)
#            mota = self.xmldoc.createElement('ParticipantType')
#            mota.setAttribute('Type', 'HUMAN')
#            user.appendChild(mota)
#            erabiltzailea.appendChild(user)

        return erabiltzailea

    def _add_process_header(self, node, object):
        """ Add process header """
        header = node.appendChild(self.xmldoc.createElement('ProcessHeader'))
        # add description
        descr = self.xmldoc.createElement('Description')
        descr.appendChild(self.xmldoc.createTextNode(object.description))
        header.appendChild(descr)
        # add priority
        priority = self.xmldoc.createElement('Priority')
        priority.appendChild(self.xmldoc.createTextNode(str(object.priority)))
        header.appendChild(priority)

    def gehituProzesuak(self):
        """ Prozesuen atala gehitzeko funtzioa - Add processes """

        # sortu nodoa
        # create the element
        prozesuak = self.xmldoc.createElement('WorkflowProcesses')
        # dagoen prozesu bakoitzeko
        # for each Process in OpenFlow
        for i in self.of.objectValues('Process'):
            # elementu bat sortu
            # create an element
            prozesua = self.xmldoc.createElement('WorkflowProcess')
            # prozesuaren atributuak bete
            # add attributes
            prozesua.setAttribute('Id', i.getId())
            prozesua.setAttribute('Name', i.title)
            # add the process header element which contains the basic Workflow Process properties
            self._add_process_header(prozesua, i)
            # ekintzak gehitu
            # add the process additional attributes
            self._add_process_extended_attrs(prozesua, i)
            # add activities
            prozesua.appendChild(self.gehituEkintzak(i))
            # trantsizioak gehitu
            # add transitions
            prozesua.appendChild(self.gehituTrantsizioak(i))

            prozesuak.appendChild(prozesua)

        return prozesuak

#    def gehituAplikazioak(self):
#        """ Prozesu konkretu bati lotutako aplikazioak gehituko ditu. Pasatzen diren
#        parametroak produktuarekin probak egin ostean detektatu direnak izan dira, hau da,
#        aplikazioei pasatzen zaizkien defektuzko parametroak dira - Add applications"""
#
#        aplikazioak = self.xmldoc.createElement('Applications')
#
#        # for each process and activity, if it contains an Application
#        # add it to the XML document. This adds all applications at the
#        # beggining of the document
#        for prozesua in self.of.objectValues('Process'):
#            for i in prozesua.objectValues('Activity'):
#                # Aplikazio bat erlazionatuta baldin badauka
#                if i.application:
#
#                    aplikazioa = self.xmldoc.createElement('Application')
#                    aplikazioa.setAttribute('Id', i.application)
#
#                    # Goian esan bezala ez da inon agertzen zein diren aplikazioei
#                    # pasatutako parametroak, ondorioz aplikazioa automatikoei
#                    # pasatzen zaizkien defektuzko 3 parametroak ipini ditut
#
#                    # I can't get application parameters neither using the API
#                    # nor using the attributes.
#                    # I decided to pass the 3 default parameters OpenFlow passes to
#                    # Automatic applications.
#
#                    forpars = self.xmldoc.createElement('FormalParameters')
#                    pars = ['workflowID', 'instanceID', 'workitemID']
#                    for j in pars:
#                        forpar = self.xmldoc.createElement('FormalParameter')
#                        forpar.setAttribute('Id', j)
#                        forpar.setAttribute('Index', str(pars.index(j)))
#                        forpar.setAttribute('Mode', 'IN')
#                        dt = self.xmldoc.createElement('DataType')
#                        bt = self.xmldoc.createElement('BasicType')
#                        bt.setAttribute('Type', 'STRING')
#                        dt.appendChild(bt)
#                        forpar.appendChild(dt)
#                        forpars.appendChild(forpar)
#
#                    aplikazioa.appendChild(forpars)
#                    aplikazioak.appendChild(aplikazioa)
#
#        return aplikazioak

    def gehituAplikazioak(self):
        """ Add applications """
        applications = self.xmldoc.createElement('Applications')
        for i in self.of.listApplications():
            app = self.xmldoc.createElement('Application')
            app.setAttribute('Id', i['name'])
            app.setAttribute('Name', i['link'])
            applications.appendChild(app)
        return applications

    def _add_process_extended_attrs(self, node, process):
        """ Add process specific attributes """
        attrs = self.xmldoc.createElement('ExtendedAttributes')
        # add 'begin' property
        attr = self.xmldoc.createElement('ExtendedAttribute')
        attr.setAttribute('Name', 'begin')
        attr.setAttribute('Value', str(process.begin))
        attrs.appendChild(attr)

        # add 'end' property
        attr = self.xmldoc.createElement('ExtendedAttribute')
        attr.setAttribute('Name', 'end')
        attr.setAttribute('Value', str(process.end))
        attrs.appendChild(attr)

        node.appendChild(attrs)

    def _add_activity_description(self, node, activity):
        """ Add the Activity description """
        descr = self.xmldoc.createElement('Description')
        descr.appendChild(self.xmldoc.createTextNode(activity.description))
        node.appendChild(descr)

    def _add_activity_extended_attrs(self, node, process, activity):
        """ Add the Activity specific attributes """
        attrs = self.xmldoc.createElement('ExtendedAttributes')
        # add 'complete_automatically' property
        attr = self.xmldoc.createElement('ExtendedAttribute')
        attr.setAttribute('Name', 'complete_automatically')
        attr.setAttribute('Value', str(activity.complete_automatically))
        attrs.appendChild(attr)

        # add 'self_assignable' property
        attr = self.xmldoc.createElement('ExtendedAttribute')
        attr.setAttribute('Name', 'self_assignable')
        attr.setAttribute('Value', str(activity.self_assignable))
        attrs.appendChild(attr)

        # add 'pushable_roles' property
        pushable_roles = self.of.getPushRoles(process.id, activity.id)
        attr = self.xmldoc.createElement('ExtendedAttribute')
        attr.setAttribute('Name', 'pushable_roles')
        attr.setAttribute('Value', ','.join(pushable_roles))
        attrs.appendChild(attr)

        # add 'push_application' property
        attr = self.xmldoc.createElement('ExtendedAttribute')
        attr.setAttribute('Name', 'push_application')
        attr.setAttribute('Value', str(activity.push_application))
        attrs.appendChild(attr)

        # add 'kind' property
        attr = self.xmldoc.createElement('ExtendedAttribute')
        attr.setAttribute('Name', 'kind')
        attr.setAttribute('Value', str(activity.kind))
        attrs.appendChild(attr)

        node.appendChild(attrs)

    def gehituEkintzak(self, prozesua):
        """ Prozesu konkretu baten ekintzak gehituko ditu
            Add activities of a given process"""

        ekintzak = self.xmldoc.createElement('Activities')

        pull_roles = self.of.getActivitiesPullableOnRole()

        # dagoen ekintza bakoitzeko
        # for each activity
        for i in prozesua.objectValues('Activity'):
            # ekintza sortu
            # create the element
            ekintza = self.xmldoc.createElement('Activity')
            # atributuak gehitu
            # add attributes
            ekintza.setAttribute('Id', i.getId())
            ekintza.setAttribute('Name', i.getId())

            # add description
            self._add_activity_description(ekintza, i)

            # add extended attributes
            self._add_activity_extended_attrs(ekintza, prozesua, i)

            # mota
            # type of implementation: Subflow, Standard, Route
            impl = self.xmldoc.createElement('Implementation')
            if i.isSubflow():
                sub = self.xmldoc.createElement('SubFlow')
                sub.setAttribute('Id', i.subflow)
                # In the case of *synchronous execution*, the execution of the Activity
                # is suspenden after a process instance of the referenced Process Definition
                # is initiated. After execution termination of this process instance the
                # Activity is resumed. This is what happens in OpenFlow, because the activity
                # isn't finished before the completion of the subflow
                sub.setAttribute('Execution', 'SYNCHR')

                # Parameters passed here, are not decided till execution
                # instanceID and workitemID are passed in execution time
                # so I can't guess their values now
                actpars = self.xmldoc.createElement('ActualParameters')
                pars = [self.of.id, 'instanceID', 'workitemID']
                for j in pars:
                    actpar = self.xmldoc.createElement('ActualParameter')
                    actpar.appendChild(self.xmldoc.createTextNode(j))
                    actpars.appendChild(actpar)

                sub.appendChild(actpars)

                impl.appendChild(sub)
                ekintza.appendChild(impl)

            elif i.isStandard():
                # if exists an application for this activity add it
                if i.application:
                    sub = self.xmldoc.createElement('Tool')
                    sub.setAttribute('Id', i.application)
                    sub.setAttribute('Type', 'APPLICATION')
                    # Parameters passed here, are not decided till execution
                    # instanceID and workitemID are passed in execution time
                    # so I can't guess their values now
                    actpars = self.xmldoc.createElement('ActualParameters')
                    pars = [self.of.id, 'instanceID', 'workitemID']
                    for j in pars:
                        actpar = self.xmldoc.createElement('ActualParameter')
                        actpar.appendChild(self.xmldoc.createTextNode(j))
                        actpars.appendChild(actpar)

                    sub.appendChild(actpars)
                else:
                    sub = self.xmldoc.createElement('No')

                impl.appendChild(sub)
                ekintza.appendChild(impl)

            else:  # i.isDummy(): routing activity
                route = self.xmldoc.createElement('Route')
                ekintza.appendChild(route)

            # nork burutzen du
            # add the performer's role
            text = ''
            for perfor, w in pull_roles.items():
                for proc, activies in w.items():
                    for act in activies:
                        if proc == prozesua.getId() and i.getId() == act:
                            if text == '':
                                text = perfor
                            else:
                                text = text + ', ' + perfor

            if text <> '':
                perf = self.xmldoc.createElement('Performer')
                perftxt = self.xmldoc.createTextNode(text)
                perf.appendChild(perftxt)
                ekintza.appendChild(perf)

            start = self.xmldoc.createElement('StartMode')
            finish = self.xmldoc.createElement('FinishMode')

            # Hasiera eta bukaera: eskuz edo automatikoki
            # auto or manual start
            if i.isAutoStart():
                stMode = self.xmldoc.createElement('Automatic')
            else:
                stMode = self.xmldoc.createElement('Manual')
            # auto or manual finish
            if i.isAutoFinish():
                fiMode = self.xmldoc.createElement('Automatic')
            else:
                fiMode = self.xmldoc.createElement('Manual')

            start.appendChild(stMode)
            finish.appendChild(fiMode)
            ekintza.appendChild(start)
            ekintza.appendChild(finish)

            # irteera eta sarrera babesak gehitu
            # add split and join restrictions: AND or XOR
            restrictions = self.xmldoc.createElement('TransitionRestrictions')
            restriction = self.xmldoc.createElement('TransitionRestriction')

            split = self.xmldoc.createElement('Split')
            split.setAttribute('Type', i.split_mode.upper())

            # ekintza honetatik irteten diren trantsizioen identifikadoreak
            # add which transitions start after this activity
            transrefs = self.xmldoc.createElement('TransitionRefs')
            for k in prozesua.objectValues('Transition'):
                if k.From == i.getId():
                    trasref = self.xmldoc.createElement('TransitionRef')
                    trasref.setAttribute('Id', k.getId())
                    transrefs.appendChild(trasref)

            split.appendChild(transrefs)

            join = self.xmldoc.createElement('Join')
            join.setAttribute('Type', i.join_mode.upper())

            restriction.appendChild(join)
            restriction.appendChild(split)
            restrictions.appendChild(restriction)

            ekintza.appendChild(restrictions)
            ekintzak.appendChild(ekintza)

        return ekintzak

    def gehituTrantsizioak(self, prozesua):
        """ Prozesu konkretu baten dauden ekintzen arteko trantsizioak gehituko ditu
            Add transitions between activities of a given process  """
        trantsizioak = self.xmldoc.createElement('Transitions')
        # dagoen trantsizio bakoitzeko
        # for each transition
        for i in prozesua.objectValues('Transition'):
            trantsizioa = self.xmldoc.createElement('Transition')
            trantsizioa.setAttribute('Id', i.getId())
            trantsizioa.setAttribute('Name', i.description)
            trantsizioa.setAttribute('From', i.From)
            trantsizioa.setAttribute('To', i.To)
            # trantsizioa egiteko bete behar den baldintza
            # add the condition
            if i.condition <> '':
                condition = self.xmldoc.createElement('Condition')
                condition.setAttribute('Type', 'CONDITION')

                condText = self.xmldoc.createTextNode(i.condition)
                condition.appendChild(condText)
                trantsizioa.appendChild(condition)
            trantsizioak.appendChild(trantsizioa)

        return trantsizioak

    def gehituHeadera(self):
        """PackageHeader gehitzen dio
        Add the PackageHeader"""
        header = self.xmldoc.createElement('PackageHeader')

        ver = self.xmldoc.createElement('XPDLVersion')
        txt1 = self.xmldoc.createTextNode('1.0')
        ver.appendChild(txt1)

        vendor = self.xmldoc.createElement('Vendor')
        txt2 = self.xmldoc.createTextNode('openflow2xpdl')
        vendor.appendChild(txt2)

        created = self.xmldoc.createElement('Created')
        txt3 = self.xmldoc.createTextNode(time.asctime())
        created.appendChild(txt3)

        header.appendChild(ver)
        header.appendChild(vendor)
        header.appendChild(created)

        return header

    def gehituConformance(self):
        """ Add Conformance Class declaration 
            ConformanceClass adierazpena gehitu"""

        conformance = self.xmldoc.createElement('ConformanceClass')
        conformance.setAttribute('GraphConformance', 'NON_BLOCKED')
        return conformance

    def gehituScript(self):
        """ Add script info """
        script = self.xmldoc.createElement('Script')
        script.setAttribute('Type', 'Python')
        return script

    def create(self):
        """ XPDL fitxategia sortzeko metodoa. """

        # xml dokumentu berria sortu
        # create new XML document
        self.xmldoc = minidom.Document()
        # erro elementua sortu eta dokumentura gehitu
        # create and add the root element
        root = self.xmldoc.createElement('Package')

        root.setAttribute('Id', self.folder.id)
        root.setAttribute('xmlns', 'http://www.wfmc.org/2002/XPDL1.0')
        root.setAttribute('xmlns:xpdl', 'http://www.wfmc.org/2002/XPDL1.0')
        root.setAttribute(
            'xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        root.setAttribute(
            'xsi:schemaLocation', 'http://www.wfmc.org/2002/XPDL1.0 http://wfmc.org/standards/docs/TC-1025_schema_10_xpdl.xsd')

        # headera gehitu
        # add header
        root.appendChild(self.gehituHeadera())
        # add ConformanceClass
        root.appendChild(self.gehituConformance())
        # add script type declaration
        root.appendChild(self.gehituScript())
        # erabiltzaileak atala gehitu
        # add users/roles
        root.appendChild(self.gehituErabiltzaileak())
        # aplikazioen atala gehitu
        # add applications
        root.appendChild(self.gehituAplikazioak())
        # prozesuen atala gehitu
        # add processes: activities, transitions,
        root.appendChild(self.gehituProzesuak())

        self.xmldoc.appendChild(root)

        # Zope objektu berria sortu izena parametroan pasatutako izenarekin
        # create new file and put the name in parameter

        # Objektua editatu eta bere eduki berria txertatu
        # edit the document and add the text
        testua = self.xmldoc.toprettyxml(encoding='UTF-8')
        return testua
