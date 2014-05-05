import time
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
from zope.lifecycleevent import ObjectMovedEvent

from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Products.Reportek import OpenFlowEngine
from Products.Reportek import constants
from Products.Reportek import Converters

from common import BaseTest, WorkflowTestCase, ConfigureReportek

import os.path
TESTDIR = os.path.abspath(os.path.dirname(__file__))

# differentiate real and thread sleeping from sleeping inside the test
def _mysleep():
    from time import sleep as s
    sleep = s
    def inner(t):
        sleep(t)
    return inner
mysleep = _mysleep()

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
        from Products.Reportek import EnvelopeRemoteServicesManager
        self.test_addEnvelope()
        self.envelope.released = True
        with self.assertRaises(exceptions.EnvelopeReleasedException) as ex:
            self.envelope.saveXML('file_id', Mock(), '')


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
        self.envelope.reportingdate = DateTime('2014/05/02 12:58:41')
        self.engine.content_registry_ping = Mock()
        # add subobjects of type document, feedback, hyperlink
        content = 'test content for our document'
        self.doc = add_document(self.envelope, create_upload_file(content, 'foo.txt'))
        #self.doc = add_document(self.envelope, create_upload_file(content, 'foo space foo.xml'))
        self.doc.upload_time = Mock(return_value=DateTime('2014/05/02 12:58:41'))

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
        self.envelope.reportingdate = DateTime('2014/05/02 12:58:41')
        rdf = self.envelope.rdf(self.app.REQUEST)
        f = open(os.path.join(TESTDIR, 'rdf.xml'), 'r')
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
        self.engine.content_registry_ping = Mock()
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

    @patch('time.sleep')
    def test_ping_create(self, sleep_mock):
        not_there_message = '''<?xml version="1.0"?>
        <response>
            <message>URL not in catalogue of sources, no action taken.</message>
            <flerror>0</flerror>
        </response>'''
        self.engine.content_registry_ping.return_value = (200, not_there_message)
        self.envelope.release_envelope()
        mysleep(0.05)

        self.assertTrue(self.engine.content_registry_ping.called)
        call_args_list = self.engine.content_registry_ping.call_args_list
        self.assertIn(((self.envelope.absolute_url()+'/rdf',), {'additional_action':'create'}), call_args_list)
        self.assertIn(((self.doc.absolute_url(),), {'additional_action':'create'}), call_args_list)
        self.assertIn(((self.feed.absolute_url(),), {'additional_action':'create'}), call_args_list)
        self.assertIn(((self.link.absolute_url(),), {'additional_action':'create'}), call_args_list)


    def test_ping_delete(self):
        ok_message = '''<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>'''
        self.engine.content_registry_ping.return_value = (200, ok_message)
        self.envelope.released = 1
        with patch('time.sleep'):
            self.envelope.unrelease_envelope()
        mysleep(0.05)

        self.assertTrue(self.engine.content_registry_ping.called)
        call_args_list = self.engine.content_registry_ping.call_args_list
        self.assertIn(((self.envelope.absolute_url()+'/rdf',), {'additional_action':'delete'}), call_args_list)
        self.assertIn(((self.doc.absolute_url(),), {'additional_action':'delete'}), call_args_list)
        self.assertIn(((self.feed.absolute_url(),), {'additional_action':'delete'}), call_args_list)
        self.assertIn(((self.link.absolute_url(),), {'additional_action':'delete'}), call_args_list)
