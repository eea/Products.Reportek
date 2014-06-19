# -*- coding: utf-8 -*-
import unittest
import lxml.etree
from StringIO import StringIO
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from DateTime import DateTime
from utils import (create_fake_root, create_upload_file, create_envelope,
                   add_document, add_feedback, add_hyperlink, simple_addEnvelope)
from mock import Mock, patch
from functools import partial
from zope.lifecycleevent import ObjectMovedEvent
import md5
import json

from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Products.Reportek import OpenFlowEngine
from Products.Reportek import constants
from Products.Reportek import Converters
from Products.Reportek import ContentRegistryPingger
from Products.Reportek.OpenFlowEngine import OpenFlowEngineImportError

from common import BaseTest, WorkflowTestCase, ConfigureReportek
from utils import mysleep

import os.path
TESTDIR = os.path.abspath(os.path.dirname(__file__))


class EnvelopeTestCase(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(EnvelopeTestCase, self).afterSetUp()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)

    def test_addEnvelope(self):
        """ To create an envelope the following is needed:
            1) self.REQUEST.AUTHENTICATED_USER.getUserName() must return something
            2) There must exist a default workflow
        """
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        simple_addEnvelope(col.manage_addProduct['Reportek'], '', '', '2003', '2004', '',
         'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
        self.envelope = None
        for env in col.objectValues('Report Envelope'):
            self.envelope = env
            break
        self.assertNotEqual(self.envelope, None)

    def helpCreateEnvelope(self,startYear, endYear, duration):
        """ To create an envelope the following is needed:
            1) self.REQUEST.AUTHENTICATED_USER.getUserName() must return something
            2) There must exist a default workflow
        """
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        col.manage_addProduct['Reportek'].manage_addEnvelope('', '', startYear, endYear, duration,
         'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
        self.envelope = None
        for env in col.objectValues('Report Envelope'):
            self.envelope = env
            self.envelope.messageDialog = Mock()
            break
        self.assertNotEqual(self.envelope, None)

    def test_endDateMultipleYears(self):
        self.helpCreateEnvelope('2003', '2004', 'Whole Year')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2003-01-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2004-12-31')

    def test_endDateFirstHalf(self):
        self.helpCreateEnvelope('2003', '', 'First Half')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2003-01-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2003-06-30')

    def test_endDateFirstQuarter(self):
        self.helpCreateEnvelope('2009', '', 'First Quarter')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2009-01-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2009-03-31')

    def test_endDateThirdQuarter(self):
        self.helpCreateEnvelope('2009', '', 'Third Quarter')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2009-07-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2009-09-30')

    def test_endDateMultipleYearsQuarter(self):
        self.helpCreateEnvelope('2004', '2009', 'First Quarter')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2004-01-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2009-12-31')
        self.envelope.release_envelope()
        rdf = self.envelope.rdf(self.app.REQUEST)
        assert rdf.find('startOfPeriod') > -1
        assert rdf.find('endOfPeriod') > -1

    def test_DateNoDates(self):
        self.helpCreateEnvelope('', '', 'First Quarter')
        s = self.envelope.getStartDate()
        self.assertEqual(s, None)
        r = self.envelope.getEndDate()
        self.assertEqual(r, None)
        self.envelope.release_envelope()
        rdf = self.envelope.rdf(self.app.REQUEST)
        self.assertEqual(-1,rdf.find('startOfPeriod'))

    def test_workitem(self):
        """ Test the first workitem """
        self.test_addEnvelope()
        # Check that exactly on workitem was created
        assert len(self.envelope.objectIds('Workitem')) == 1
        wi = self.envelope.objectValues('Workitem')[0]
        user = getSecurityManager().getUser().getUserName()
        # Activate envelope's workitem
        self.envelope.activateWorkitem(wi.id, actor=user)
        # Check that it did it correctly
        self.assertEquals(wi.actor, 'test_user_1_')
        self.assertEquals(self.envelope.id, wi.instance_id)
        self.assertEquals('Begin', wi.activity_id)
        self.envelope.completeWorkitem(wi.id, actor=user)
        self.assertEquals('complete', wi.status)

    def test_invalid_period(self):
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        from Products.Reportek import exceptions
        with self.assertRaises(exceptions.InvalidPartOfYear) as ex:
            col.manage_addProduct['Reportek'].manage_addEnvelope('', '', '2003', '2004', 'invalid',
             'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')

    def test_saveXML_on_released_envelope(self):
        from Products.Reportek import exceptions
        self.test_addEnvelope()
        self.envelope.released = True
        with self.assertRaises(exceptions.EnvelopeReleasedException) as ex:
            self.envelope.saveXML('file_id', Mock(), '')

    def test_openflow_exportToJson(self):
        self.createStandardCatalog()
        wfe = getattr(self.app, 'WorkflowEngine')
        pr = getattr(wfe, 'begin_end')
        tr = getattr(pr, 'begin_end')
        tr.condition = "python: len([ i for i in xrange(1, 11)])"
        pr.addActivity('activity1', application='script1')
        pr.addActivity('activity2', application='script2')
        self.app.manage_addFolder('Applications')
        folder = getattr(self.app, 'Applications')

        folder.manage_addProduct['PythonScripts'].manage_addPythonScript(id='an_application')
        script1 = getattr(folder, 'an_application')
        # test unicode
        script1.write(u"return 'blâ'")
        expected_type1 = script1.meta_type
        expected_checksum1 = md5.md5(script1.read().encode('utf-8')).hexdigest()

        folder.manage_addProduct['PythonScripts'].manage_addPythonScript(id='another_application')
        script2 = getattr(folder, 'another_application')
        # test string with non ascii chars
        script2.ZPythonScript_edit(params='',body="return 'blâ'")
        expected_type2 = script2.meta_type
        expected_checksum2 = md5.md5(script2.read()).hexdigest()

        wfe.addApplication('script1', script1.absolute_url(1))
        wfe.addApplication('script2', script2.absolute_url(1))
        # this application will not be exported as it is not referenced by any process activity
        wfe.addApplication('script3', '/this/is/not/referenced/by/any/activity')

        expected_role = 'Manager'
        wfe.editActivitiesPullableOnRole(expected_role, 'begin_end', ['Begin', 'Draft', 'Release'])

        r = wfe.exportToJson(proc='begin_end')
        o = json.loads(r)
        self.assertIn('applications', o)
        self.assertEqual(len(o['applications']), 2)
        self.assertIn({
            'checksum': expected_checksum1,
            'rid': 'script1',
            'type': expected_type1,
            'url': script1.absolute_url(1)
        }, o['applications'])
        self.assertIn({
            'checksum': expected_checksum2,
            'rid': 'script2',
            'type': expected_type2,
            'url': script2.absolute_url(1)
        }, o['applications'])

        self.assertIn('processes', o)
        proc = o['processes'][0]
        expected_proc = {
            u'activities': [{u'application': u'',
                             u'complete_automatically': 1,
                             u'description': u'',
                             u'finish_mode': 0,
                             u'join_mode': u'and',
                             u'kind': u'standard',
                             u'parameters': u'',
                             u'pullable_roles': [expected_role],
                             u'push_application': u'',
                             u'pushable_roles': [],
                             u'rid': u'Begin',
                             u'self_assignable': 1,
                             u'split_mode': u'and',
                             u'start_mode': 0,
                             u'subflow': u'',
                             u'title': u''},
                             {u'application': u'',
                             u'complete_automatically': 1,
                             u'description': u'',
                             u'finish_mode': 0,
                             u'join_mode': u'and',
                             u'kind': u'standard',
                             u'parameters': u'',
                             u'pullable_roles': [],
                             u'push_application': u'',
                             u'pushable_roles': [],
                             u'rid': u'End',
                             u'self_assignable': 1,
                             u'split_mode': u'and',
                             u'start_mode': 0,
                             u'subflow': u'',
                             u'title': u''},
                            {u'application': u'script1',
                             u'complete_automatically': 1,
                             u'description': u'',
                             u'finish_mode': 0,
                             u'join_mode': u'and',
                             u'kind': u'standard',
                             u'parameters': u'',
                             u'pullable_roles': [],
                             u'push_application': u'',
                             u'pushable_roles': [],
                             u'rid': u'activity1',
                             u'self_assignable': 1,
                             u'split_mode': u'and',
                             u'start_mode': 0,
                             u'subflow': u'',
                             u'title': u''},
                            {u'application': u'script2',
                             u'complete_automatically': 1,
                             u'description': u'',
                             u'finish_mode': 0,
                             u'join_mode': u'and',
                             u'kind': u'standard',
                             u'parameters': u'',
                             u'pullable_roles': [],
                             u'push_application': u'',
                             u'pushable_roles': [],
                             u'rid': u'activity2',
                             u'self_assignable': 1,
                             u'split_mode': u'and',
                             u'start_mode': 0,
                             u'subflow': u'',
                             u'title': u''}],
            u'begin': u'Begin',
            u'description': u'',
            u'end': u'End',
            u'priority': 0,
            u'rid': u'begin_end',
            u'title': u'',
            u'transitions': [{
                u'condition': tr.condition,
                u'description': u'',
                u'from': u'Begin',
                u'rid': u'begin_end',
                u'to': u'End'}]
        }
        self.assertEqual(proc, expected_proc)

    def _make_openflow_json(self, pr_id=u'begin_end_new', act_id=u'Begin',
            transition_id=u'begin_end',
            app_name_url=(u'script1', u'Applications/an_application'),
            roles=[u'Manager']):

        obj = {
            u'applications': [{u'checksum': u'48aaf9f159480ee25a3b56edab1c7f47',
                               u'rid': app_name_url[0],
                               u'type': u'Script (Python)',
                               u'url': app_name_url[1]},
                              {u'checksum': u'6d440bda5b6bc8f337e611ce7b6a172e',
                               u'rid': u'script2',
                               u'type': u'Script (Python)',
                               u'url': u'Applications/another_application'}],
            u'processes': [{u'activities': [{u'application': app_name_url[0],
                                             u'complete_automatically': 1,
                                             u'description': u'',
                                             u'finish_mode': 0,
                                             u'join_mode': u'and',
                                             u'kind': u'standard',
                                             u'parameters': u'',
                                             u'pullable_roles': roles,
                                             u'push_application': u'',
                                             u'pushable_roles': [],
                                             u'rid': act_id,
                                             u'self_assignable': 1,
                                             u'split_mode': u'and',
                                             u'start_mode': 0,
                                             u'subflow': u'',
                                             u'title': u''},
                                            {u'application': u'script2',
                                             u'complete_automatically': 1,
                                             u'description': u'',
                                             u'finish_mode': 0,
                                             u'join_mode': u'and',
                                             u'kind': u'standard',
                                             u'parameters': u'',
                                             u'pullable_roles': [],
                                             u'push_application': u'',
                                             u'pushable_roles': [],
                                             u'rid': u'End',
                                             u'self_assignable': 1,
                                             u'split_mode': u'and',
                                             u'start_mode': 0,
                                             u'subflow': u'',
                                             u'title': u''}],
                            u'begin': u'Begin',
                            u'description': u'Șșș',
                            u'end': u'End',
                            u'priority': 0,
                            u'rid': pr_id,
                            u'title': u'Ă title',
                            u'transitions': [{u'condition': u'python: len([ i for i in xrange(1, 11)])',
                                              u'description': u'',
                                              u'from': u'Begin',
                                              u'rid': transition_id,
                                              u'to': u'End'}]}]
        }
        return StringIO(json.dumps(obj))

    def test_openflow_importFromJson(self):
        self.createStandardCatalog()
        pr_id = u'begin_end_new'
        make_json = partial(self._make_openflow_json, pr_id=pr_id)
        jsonControlObj = json.load(make_json())
        jsonStream = make_json()

        wfe = getattr(self.app, 'WorkflowEngine')
        applications = wfe._importFromJson(jsonStream)
        proc = jsonControlObj['processes'][0]
        pr = getattr(wfe, pr_id)
        self.assertEqual(pr.title, proc['title'])
        self.assertEqual(pr.description, proc['description'])
        self.assertEqual(pr.priority, int(proc['priority']))
        self.assertEqual(pr.begin, proc['begin'])
        self.assertEqual(pr.end, proc['end'])

        act1 = proc['activities'][0]
        self.assertTrue(hasattr(pr, act1['rid']))
        a1 = getattr(pr, act1['rid'])
        act2 = proc['activities'][1]
        self.assertTrue(hasattr(pr, act2['rid']))
        a2 = getattr(pr, act2['rid'])

        self.assertEqual(a1.title, act1['title'])
        self.assertEqual(a2.title, act2['title'])
        self.assertEqual(a1.description, act1['description'])
        self.assertEqual(a2.description, act2['description'])
        self.assertEqual(a1.split_mode, act1['split_mode'])
        self.assertEqual(a2.split_mode, act2['split_mode'])
        self.assertEqual(a1.join_mode, act1['join_mode'])
        self.assertEqual(a2.join_mode, act2['join_mode'])
        self.assertEqual(a1.self_assignable, int(act1['self_assignable']))
        self.assertEqual(a2.self_assignable, int(act2['self_assignable']))
        self.assertEqual(a1.start_mode, int(act1['start_mode']))
        self.assertEqual(a2.start_mode, int(act2['start_mode']))
        self.assertEqual(a1.finish_mode, int(act1['finish_mode']))
        self.assertEqual(a2.finish_mode, int(act2['finish_mode']))
        self.assertEqual(a1.complete_automatically, int(act1['complete_automatically']))
        self.assertEqual(a2.complete_automatically, int(act2['complete_automatically']))
        self.assertEqual(a1.subflow, str(act1['subflow']))
        self.assertEqual(a2.subflow, str(act2['subflow']))
        self.assertEqual(a1.push_application, str(act1['push_application']))
        self.assertEqual(a2.push_application, str(act2['push_application']))
        self.assertEqual(a1.application, str(act1['application']))
        self.assertEqual(a2.application, str(act2['application']))
        self.assertEqual(a1.parameters, str(act1['parameters']))
        self.assertEqual(a2.parameters, str(act2['parameters']))
        self.assertEqual(a1.kind, str(act1['kind']))
        self.assertEqual(a2.kind, str(act2['kind']))

        pushRoles = wfe.getActivitiesPushableOnRole()
        self.assertEqual(pushRoles, {})
        pullRoles = wfe.getActivitiesPullableOnRole()
        self.assertEqual(pullRoles, {'Manager': {'begin_end_new': ['Begin']}})

        trans = proc['transitions'][0]
        tr = getattr(pr, trans['rid'])
        self.assertEqual(tr.description, trans['description'])
        self.assertEqual(tr.From, trans['from'])
        self.assertEqual(tr.To, trans['to'])
        self.assertEqual(tr.condition, trans['condition'])
        app1 = {u'checksum': u'48aaf9f159480ee25a3b56edab1c7f47',
                u'rid': u'script1',
                u'type': u'Script (Python)',
                u'url': u'Applications/an_application'}
        app2 = {u'checksum': u'6d440bda5b6bc8f337e611ce7b6a172e',
                u'rid': u'script2',
                u'type': u'Script (Python)',
                u'url': u'Applications/another_application'}
        self.assertIn(app1, applications)
        self.assertIn(app2, applications)

    def test_openflow_importFromJson_appWithDiffPaths(self):
        self.createStandardCatalog()

        wfe = getattr(self.app, 'WorkflowEngine')
        self.app.manage_addFolder('NewApplications')
        folder = getattr(self.app, 'NewApplications')
        folder.manage_addProduct['PythonScripts'].manage_addPythonScript(id='an_application')
        script1 = getattr(folder, 'an_application')
        script1.write(u"return 'blâ'")
        wfe.addApplication('script1', script1.absolute_url(1))
        folder.manage_addProduct['PythonScripts'].manage_addPythonScript(id='another_application')
        script1 = getattr(folder, 'another_application')
        script1.write(u"return 'something else'")
        wfe.addApplication('script2', script1.absolute_url(1))

        pr_id = u'begin_end_new'
        make_json = partial(self._make_openflow_json, pr_id=pr_id)
        jsonControlObj = json.load(make_json())
        jsonStream = make_json()

        applications = wfe._importFromJson(jsonStream)
        proc = jsonControlObj['processes'][0]
        pr = getattr(wfe, pr_id)

        act1 = proc['activities'][0]
        self.assertTrue(hasattr(pr, act1['rid']))

        self.assertEqual(act1['application'], 'script1')
        app1 = applications[0]
        self.assertIn('targetPath', app1)
        self.assertEqual(app1['rid'], act1['application'])
        self.assertNotEqual(app1['targetPath'], app1['url'])
        existing_type, existing_checksum = wfe._applicationDetails(app1['targetPath'])
        # the content checking is still performed though
        self.assertEqual(app1['checksum'], existing_checksum)

        act2 = proc['activities'][1]
        self.assertTrue(hasattr(pr, act2['rid']))

        self.assertEqual(act2['application'], 'script2')
        app2 = applications[1]
        self.assertIn('targetPath', app2)
        self.assertEqual(app2['rid'], act2['application'])
        self.assertNotEqual(app2['targetPath'], app2['url'])
        existing_type, existing_checksum = wfe._applicationDetails(app2['targetPath'])
        # the content checking is still performed though
        self.assertNotEqual(app2['checksum'], existing_checksum)


    def test_openflow_importFromJson_wrongId(self):
        self.createStandardCatalog()
        wfe = getattr(self.app, 'WorkflowEngine')

        pr_id = u'begin_end_new_ă'
        make_json = partial(self._make_openflow_json, pr_id)
        jsonStream = make_json()
        expected_exception_args = ('Invalid rid', pr_id)
        exception_args = None
        try:
            wfe._importFromJson(jsonStream)
        except OpenFlowEngineImportError as e:
            exception_args = e.args
            self.assertEqual(exception_args[:2], expected_exception_args)

        pr_id = u'begin_end_new'
        act_id = u'B€gin'
        make_json = partial(self._make_openflow_json, pr_id, act_id)
        jsonStream = make_json()
        expected_exception_args = ('Invalid rid', act_id)
        exception_args = None
        try:
            wfe._importFromJson(jsonStream)
        except OpenFlowEngineImportError as e:
            exception_args = e.args
        self.assertEqual(exception_args, expected_exception_args)

        pr_id = u'begin_end_new2'
        trans_id = u'b€gin_end'
        make_json = partial(self._make_openflow_json, pr_id, transition_id=trans_id)
        jsonStream = make_json()
        expected_exception_args = ('Invalid rid', trans_id)
        exception_args = None
        try:
            wfe._importFromJson(jsonStream)
        except OpenFlowEngineImportError as e:
            exception_args = e.args
        self.assertEqual(exception_args, expected_exception_args)

        pr_id = u'begin_end_new3'
        app_name = u'Draft'
        app_url = u'/Applications/Drâft'
        make_json = partial(self._make_openflow_json, pr_id, app_name_url=(app_name, app_url))
        jsonStream = make_json()
        expected_exception_args = ('Error adding application', app_name, app_url)
        exception_args = None
        try:
            wfe._importFromJson(jsonStream)
        except OpenFlowEngineImportError as e:
            exception_args = e.args
        self.assertEqual(exception_args, expected_exception_args)

    def test_openflow_importFromJson_generalException(self):
        self.createStandardCatalog()
        wfe = getattr(self.app, 'WorkflowEngine')

        jsonStream = StringIO(json.dumps({}))
        exception_args = None
        try:
            wfe._importFromJson(jsonStream)
        except Exception as e:
            exception_args = e.args
        self.assertIsNotNone(exception_args)

    def test_openflow_importFromJson_badRole(self):
        self.createStandardCatalog()
        wfe = getattr(self.app, 'WorkflowEngine')

        weird_roles = [u'Manager', u'destroyer']
        make_json = partial(self._make_openflow_json, roles=weird_roles)
        jsonStream = make_json()
        wfe._importFromJson(jsonStream)

        pullRoles = wfe.getActivitiesPullableOnRole()
        self.assertNotIn('destroyer', pullRoles)

def get_xml_metadata(envelope, inline='false'):
    from Products.Reportek.XMLMetadata import XMLMetadata
    xml_data = XMLMetadata(envelope).envelopeMetadata(inline)
    return lxml.etree.parse(StringIO(xml_data)).getroot()


class EnvelopeMetadataTest(unittest.TestCase):

    def setUp(self):
        self.root = create_fake_root()
        self.envelope = create_envelope(self.root)

    def test_metadata_of_empty_envelope(self):
        envelope_el = get_xml_metadata(self.envelope)
        self.assertEqual(envelope_el.attrib['released'], 'false')
        self.assertEqual(envelope_el.xpath('//file'), [])

    def test_metadata_of_envelope_with_document(self):
        add_document(self.envelope, create_upload_file("blah", 'blah.txt'))
        envelope_el = get_xml_metadata(self.envelope)
        xml_file_list = envelope_el.xpath('//file')
        self.assertEqual(len(xml_file_list), 1)
        [xml_file] = xml_file_list
        self.assertEqual(xml_file.attrib['name'], 'blah.txt')
        self.assertEqual(xml_file.attrib['type'], 'text/plain')

    def test_inline_xml_document(self):
        upload_file = create_upload_file('<foo title="bar"/>', 'baz.xml')
        add_document(self.envelope, upload_file)

        with patch.object(self.envelope, 'canViewContent'):
            envelope_el = get_xml_metadata(self.envelope, inline='true')

        xml_instance_list = envelope_el.xpath('//instance')
        self.assertEqual(len(xml_instance_list), 1)

        [xml_instance] = xml_instance_list
        self.assertEqual(xml_instance.attrib['name'], "baz.xml")
        self.assertEqual(xml_instance.attrib['type'], "text/xml")

        self.assertEqual(xml_instance[0].tag, "foo")
        self.assertEqual(xml_instance[0].attrib['title'], "bar")


class EnvelopeCustomDataflowsXmlTest(unittest.TestCase):

    def setUp(self):
        self.root = create_fake_root()
        self.envelope = create_envelope(self.root)

    def test_custom_dataflows_xml(self):
        upload_file = create_upload_file('<foo title="bar"/>', 'baz.xml')
        add_document(self.envelope, upload_file)
        dom = self.envelope.getFormContentAsXML('baz.xml')
        self.assertEqual(dom.firstChild.nodeName, 'foo')
        self.assertEqual(dom.firstChild.attributes['title'].value, 'bar')


class ActivityFindsApplicationTestCase(WorkflowTestCase):

    def setUp(self):
        super(ActivityFindsApplicationTestCase, self).setUp()
        self.app._setOb('Applications', Folder('Applications'))

    def test_getApplicationUrl(self):
        """
        Test if EnvelopeInstance.getApplicationUrl checks first
        <root>/<Applications Folder>/<process_id>/<activity_id> for an
        application
        NOTE: The id of the application should be the same as the id of the
        activity
        """
        self.create_cepaa_set(1)
        current_workitem = self.env1.objectValues('Workitem')[-1]
        current_application = self.env1.getApplicationUrl(current_workitem.id)
        self.assertEqual(current_application, 'Applications/proc1/act1')

    def test_getApplicationUrl_finds_in_Common_folder(self):
        """
        Test if EnvelopeInstance.getApplicationUrl checks next
        in <root>/<Applications Folder>/Common/<activity_id> for an application
        NOTE: The id of the application should be the same as the id of the
        activity
        """
        self.create_cepaa_set(1)
        self.app.Applications.proc1._delOb('act1')
        app = SimpleItem('act1').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications._setOb('Common', Folder('Common'))
        self.app.Applications.Common._setOb('act1', app)
        current_workitem = self.env1.objectValues('Workitem')[-1]
        current_application = self.env1.getApplicationUrl(current_workitem.id)
        self.assertEqual(current_application, 'Applications/Common/act1')

    def test_getApplicationUrl_proc_folder_has_priority(self):
        """
        Test if EnvelopeInstance.getApplicationUrl checks next
        in <root>/<Applications Folder>/Common/<activity_id> for an application
        NOTE: The id of the application should be the same as the id of the
        activity
        """
        self.create_cepaa_set(1)
        app = SimpleItem('act1').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications._setOb('Common', Folder('Common'))
        self.app.Applications.Common._setOb('act1', app)
        current_workitem = self.env1.objectValues('Workitem')[-1]
        current_application = self.env1.getApplicationUrl(current_workitem.id)
        self.assertEqual(current_application, 'Applications/proc1/act1')

    def test_getApplicationUrl_finds_application_attribute(self):
        """
        Test if EnvelopeInstance.getApplicationUrl checks next
        in <root>/<Applications Folder>/Common/<activity_id> for an application
        NOTE: This is for backward compatibility
        """
        self.create_cepaa_set(1)
        # no matching app in Applications or Applications/Common
        self.app.Applications.proc1._delOb('act1')
        current_workitem = self.env1.objectValues('Workitem')[-1]
        self.wf.proc1.get('act1').application = 'act1'
        current_application = self.env1.getApplicationUrl(current_workitem.id)
        # WARNING:
        # app path (from the attribute) doesn't have a leading '/' in this case
        # and if we call the application from the envelope context
        # it will start the traversing from the envelope and it
        # will find the application by acquisition.
        # e.g.:
        # ../col/env/Applications/CDDA/EnvelopeDecideStartActivity.py
        # and context.getMySelf() will work in this case
        self.assertEqual('SomeFolder/act1', current_application)

    def test_application_invalid_to_valid_rename(self):
        """
        Reportek has a folder to store all the applications for the activities.

        An application path has this pattern:
         ``/<apps_folder>/<proc_id>/<app_id>``

        Let's say we have an application with this path:
         ``/Applications/wise_soe/Draft``

        In order to be able to map activities to applications, when renaming an application, the new name must pass a validation mechanism.

        - First, the process id is identified by looking at the application path ``(wise_soe)``
        - A list with all the ids of activities for that process is pulled from WorkflowEngine
        - In order to be valid, the new name of the application must match one of the ids in the list
        """
        self.create_cepaa_set(1)
        app = SimpleItem('act1').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications.proc1._setOb('act1', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'bad_name',
                    self.app.Applications.proc1,
                    'act1'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        message = 'Id bad_name was not mapped by path to any activity. ' \
                  'Application act1 mapped by path to activity /WorkflowEngine/proc1/act1.'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])


    def test_application_invalid_to_invalid_rename(self):
        self.create_cepaa_set(1)
        app = SimpleItem('still_bad_name').__of__(self.app.Applications.proc1)
        app.id = 'still_bad_name'
        self.app.Applications.proc1._setOb('still_bad_name', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'bad_name',
                    self.app.Applications.proc1,
                    'still_bad_name'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        message = 'Id bad_name was not mapped by path to any activity. ' \
                  'Id still_bad_name does not match any activity name in process /WorkflowEngine/proc1. ' \
                  'Choose a valid name from this list: Begin, End, act1'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])

    def test_application_valid_to_valid_rename(self):
        self.create_cepaa_set(1)
        self.wf.proc1.addActivity('act2')
        app = SimpleItem('act2').__of__(self.app.Applications.proc1)
        app.id = 'act2'
        self.app.Applications.proc1._setOb('act2', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'act1',
                    self.app.Applications.proc1,
                    'act2'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        message = 'Activity /WorkflowEngine/proc1/act1 has no application mapped by path now. '\
                  'Application act2 mapped by path to activity /WorkflowEngine/proc1/act2.'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])

    def test_application_valid_to_invalid_rename(self):
        self.create_cepaa_set(1)
        app = SimpleItem('bad_name').__of__(self.app.Applications.proc1)
        app.id = 'bad_name'
        self.app.Applications.proc1._setOb('bad_name', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'act1',
                    self.app.Applications.proc1,
                    'bad_name'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        message = 'Activity /WorkflowEngine/proc1/act1 has no application mapped by path now. '\
                  'Id bad_name does not match any activity name in process /WorkflowEngine/proc1. ' \
                  'Choose a valid name from this list: Begin, End, act1'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])

    def test_application_valid_delete(self):
        self.create_cepaa_set(1)
        app = SimpleItem('Renamed_Draft').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications.proc1._setOb('act1', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'act1',
                    None, #empty newParent & empty newName means deletion
                    ''
                    )
        from Products.Reportek import exceptions
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        self.assertEqual('Application act1 deleted! '\
                   'Activity /WorkflowEngine/proc1/act1 has no '
                   'application mapped by path now.',
                   self.app.REQUEST['manage_tabs_message'])

    def test_application_invalid_delete(self):
        self.create_cepaa_set(1)
        app = SimpleItem('Renamed_Draft').__of__(self.app.Applications.proc1)
        app.id = 'bad_name'
        self.app.Applications.proc1._setOb('bad_name', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'bad_name',
                    None, #empty newParent & empty newName means deletion
                    ''
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        self.assertEqual('Application bad_name deleted! '\
                         'Id bad_name was not mapped by path to any activity.',
                         self.app.REQUEST['manage_tabs_message'])

    def test_application_valid_create(self):
        self.create_cepaa_set(1)
        app = SimpleItem('Renamed_Draft').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications.proc1._setOb('act1', app)
        event = ObjectMovedEvent(
                    app,
                    None,
                    '',
                    self.app.Applications.proc1,
                    'act1'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        self.assertEqual('Application act1 mapped by path '\
                         'to activity /WorkflowEngine/proc1/act1.',
                         self.app.REQUEST['manage_tabs_message'])

    def test_application_invalid_create(self):
        self.create_cepaa_set(1)
        app = SimpleItem('invalid_id').__of__(self.app.Applications.proc1)
        app.id = 'invalid_id'
        self.app.Applications.proc1._setOb('invalid_id', app)
        event = ObjectMovedEvent(
                    app,
                    None,
                    '',
                    self.app.Applications.proc1,
                    'invalid_id'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        message = 'Id invalid_id does not match any activity name in process /WorkflowEngine/proc1. ' \
                  'Choose a valid name from this list: Begin, End, act1'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])

    def test_application_valid_move_from_one_proc_to_another(self):
        self.create_cepaa_set(1)
        self.create_cepaa_set(2)
        # a valid movement is when proc1 and proc2 have a common activity id
        # so we add act1 to proc2 too
        self.wf.proc2.addActivity('act1')
        app = SimpleItem('act1').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications.proc1._setOb('act1', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'act1',
                    self.app.Applications.proc2,
                    'act1'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        self.assertEqual(
             'Application act1 moved! '\
             'Activity /WorkflowEngine/proc1/act1 has no application mapped by path now. '\
             'Application act1 mapped by path to activity /WorkflowEngine/proc2/act1.',
             self.app.REQUEST['manage_tabs_message'])

    def test_application_invalid_move_from_one_proc_to_another(self):
        self.create_cepaa_set(1)
        self.create_cepaa_set(2)
        # this happens when proc1 and proc2 do not have a common activity id
        app = SimpleItem('act1').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications.proc1._setOb('act1', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'act1',
                    self.app.Applications.proc2,
                    'act1'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        message = 'Application act1 moved! '\
                  'Activity /WorkflowEngine/proc1/act1 has no application mapped by path now. ' \
                  'Id act1 does not match any activity name in process /WorkflowEngine/proc2. ' \
                  'Choose a valid name from this list: Begin, End, act2'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])

    def test_application_valid_move_from_exterior_to_process_folder(self):
        self.create_cepaa_set(1)
        app = SimpleItem('act1').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications.proc1._setOb('act1', app)
        event = ObjectMovedEvent(
                    app,
                    self.app,
                    'act1',
                    self.app.Applications.proc1,
                    'act1'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        self.assertEqual('Application act1 mapped by path to activity /WorkflowEngine/proc1/act1.',
                         self.app.REQUEST['manage_tabs_message'])

    def test_application_invalid_move_from_exterior_to_process_folder(self):
        self.create_cepaa_set(1)
        app = SimpleItem('act2').__of__(self.app.Applications.proc1)
        app.id = 'act2'
        self.app.Applications.proc1._setOb('act2', app)
        event = ObjectMovedEvent(
                    app,
                    self.app,
                    'act2',
                    self.app.Applications.proc1,
                    'act2'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        message = 'Id act2 does not match any activity name in process /WorkflowEngine/proc1. ' \
                  'Choose a valid name from this list: Begin, End, act1'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])

    def test_application_valid_move_from_process_folder_to_exterior(self):
        self.create_cepaa_set(1)
        app = SimpleItem('act1').__of__(self.app)
        app.id = 'act1'
        self.app._setOb('act1', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'act1',
                    self.app,
                    'act1',
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        self.assertEqual('Application act1 moved! '\
                   'Activity /WorkflowEngine/proc1/act1 has no '
                   'application mapped by path now.',
                   self.app.REQUEST['manage_tabs_message'])

    def test_application_invalid_move_from_process_folder_to_exterior(self):
        self.create_cepaa_set(1)
        app = SimpleItem('act2').__of__(self.app)
        app.id = 'act2'
        self.app._setOb('act2', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'act2',
                    self.app,
                    'act2',
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        self.assertEqual(
            'Application act2 moved! '\
            'Id act2 was not mapped by path to any activity.',
            self.app.REQUEST['manage_tabs_message'])


class EnvelopeRdfTestCase(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(EnvelopeRdfTestCase, self).afterSetUp()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        simple_addEnvelope(col.manage_addProduct['Reportek'], '', '', '2003', '2004', '',
         'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
        self.envelope = None
        for env in col.objectValues('Report Envelope'):
            self.envelope = env
            break
        self.envelope.id = 'envu2nsuq'
        self.envelope.reportingdate = DateTime('2014/05/02 09:58:41 UTC')
        self.engine.content_registry_ping = Mock()
        # add subobjects of type document, feedback, hyperlink
        content = 'test content for our document'
        self.doc = add_document(self.envelope, create_upload_file(content, 'foo.txt'))
        #self.doc = add_document(self.envelope, create_upload_file(content, 'foo space foo.xml'))
        self.doc.upload_time = Mock(return_value=DateTime('2014/05/02 09:58:41 UTC'))

        feedbacktext = 'feedback text'
        setattr(
            self.root.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(return_value=Mock(text=feedbacktext)))
        getattr(self.root.getPhysicalRoot(),
                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)
        self.feed = add_feedback(self.envelope, feedbacktext, feedbackId='feedback1399024721')
        self.link = add_hyperlink(self.envelope, 'hyper/link')
        self.envelope._content_registry_ping = Mock()

    def test_subobjectsForContentRegistry(self):
        objsByType = self.envelope._getObjectsForContentRegistry()
        expectedObjsByType = {
            'Report Hyperlink': [self.link],
            'Report Feedback': [self.feed],
            'Report Document': [self.doc]
        }
        self.assertDictEqual(objsByType, expectedObjsByType)

    def test_rdf(self):
        self.envelope.release_envelope()
        self.envelope.reportingdate = DateTime('2014/05/02 09:58:41 UTC')
        rdf = self.envelope.rdf(self.app.REQUEST)
        f = open(os.path.join(TESTDIR, 'rdf.xml'), 'r')
        expected = f.read()
        f.close()
        self.assertEqual(str(rdf), expected)

    def test_space_in_name(self):
        self.doc.id = 'another document id with space.txt'
        self.envelope.release_envelope()
        self.envelope.reportingdate = DateTime('2014/05/02 09:58:41 UTC')
        rdf = self.envelope.rdf(self.app.REQUEST)
        f = open(os.path.join(TESTDIR, 'rdf_space.xml'), 'r')
        expected = f.read()
        f.close()
        self.assertEqual(str(rdf), expected)



class EnvelopeCRTestCase(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(EnvelopeCRTestCase, self).afterSetUp()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        simple_addEnvelope(col.manage_addProduct['Reportek'], '', '', '2003', '2004', '',
                           'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
        self.envelope = None
        for env in col.objectValues('Report Envelope'):
            self.envelope = env
            break

        self.engine.cr_api_url = 'http://none'
        self.pingger = self.engine.contentRegistryPingger
        self.assertTrue(bool(self.pingger))
        ContentRegistryPingger.ContentRegistryPingger.content_registry_ping_async = Mock()
        # add subobjects of type document, feedback, hyperlink
        content = 'test content for our document'
        self.doc = add_document(self.envelope, create_upload_file(content, 'foo.txt'))

        feedbacktext = 'feedback text'
        setattr(
            self.root.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters())
        safe_html = Mock(convert=Mock(return_value=Mock(text=feedbacktext)))
        getattr(self.root.getPhysicalRoot(),
                                constants.CONVERTERS_ID).__getitem__ = Mock(return_value=safe_html)
        self.feed = add_feedback(self.envelope, feedbacktext)
        self.link = add_hyperlink(self.envelope, 'hyper/link')

    def test_subobjectsForContentRegistry(self):
        objsByType = self.envelope._getObjectsForContentRegistry()
        expectedObjsByType = {
            'Report Hyperlink': [self.link],
            'Report Feedback': [self.feed],
            'Report Document': [self.doc]
        }
        self.assertDictEqual(objsByType, expectedObjsByType)

    def test_ping_create(self):
        expectedUris = set([
            self.envelope.absolute_url()+'/rdf',
            self.doc.absolute_url(),
            self.feed.absolute_url(),
            self.link.absolute_url(),
        ])
        self.envelope.content_registry_ping()
        mysleep(0.05)

        self.assertTrue(ContentRegistryPingger.ContentRegistryPingger.content_registry_ping_async.called)
        call_args = ContentRegistryPingger.ContentRegistryPingger.content_registry_ping_async.call_args
        args = call_args[0]
        kwargs = call_args[1]
        self.assertEqual(len(args), 1)
        uris = args[0]
        self.assertEqual(len(uris), 4)
        self.assertEqual(set(uris), expectedUris)
        self.assertEqual(len(kwargs), 1)
        ping_argument = kwargs.get('ping_argument')
        self.assertEqual(ping_argument, 'create')

    def test_ping_delete(self):
        expectedUris = set([
            self.envelope.absolute_url()+'/rdf',
            self.doc.absolute_url(),
            self.feed.absolute_url(),
            self.link.absolute_url(),
        ])
        self.envelope.content_registry_ping(delete=True)
        mysleep(0.05)

        self.assertTrue(ContentRegistryPingger.ContentRegistryPingger.content_registry_ping_async.called)
        call_args = ContentRegistryPingger.ContentRegistryPingger.content_registry_ping_async.call_args
        args = call_args[0]
        kwargs = call_args[1]
        self.assertEqual(len(args), 1)
        uris = args[0]
        self.assertEqual(len(uris), 4)
        self.assertEqual(set(uris), expectedUris)
        self.assertEqual(len(kwargs), 1)
        ping_argument = kwargs.get('ping_argument')
        self.assertEqual(ping_argument, 'delete')
