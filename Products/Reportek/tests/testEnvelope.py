import os, sys
import unittest
import lxml.etree
from StringIO import StringIO
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from configurereportek import ConfigureReportek
from utils import create_fake_root, create_temp_reposit, create_upload_file
from utils import create_envelope, add_document, simple_addEnvelope
from mock import Mock, patch
from zope.lifecycleevent import ObjectMovedEvent

from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Products.Reportek import OpenFlowEngine

from Products.Reportek.Collection import Collection
from Products.Reportek.Envelope import Envelope
from Products.Reportek.process import process
from Products.Reportek import exceptions
from common import create_mock_request, create_process, _BaseTest


def setUpModule(self):
    self._cleanup_temp_reposit = create_temp_reposit()

def tearDownModule(self):
    self._cleanup_temp_reposit()


class EnvelopeTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    def afterSetUp(self):
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


class ActivityFindsApplicationTestCase(_BaseTest):

    def setUp(self):
        super(ActivityFindsApplicationTestCase, self).setUp()
        self.app._setOb('Applications', Folder('Applications'))

    def create_cepaa_set(self, idx):
        col_id = "col%s" %idx
        env_id = "env%s" %idx
        proc_id = "proc%s" %idx
        act_id = "act%s" %idx
        app_id = "act%s" %idx
        country = 'http://spatial/%s' %idx
        dataflow_uris = 'http://obligation/%idx' %idx
        "create collection, envelope, process, activity, application"
        col = Collection(col_id, country=country, dataflow_uris=dataflow_uris)
        self.app._setOb(col_id, col)

        self.app.Templates.StartActivity = Mock(return_value='Test Application')
        self.app.Templates.StartActivity.title_or_id = Mock(return_value='Start Activity Template')
        create_process(self, proc_id)
        self.wf.addApplication(app_id, 'Applications/%s' %app_id)

        self.app.Applications._setOb(proc_id, Folder(proc_id))
        proc = getattr(self.app.Applications, proc_id)

        app = SimpleItem(app_id)
        app.id = app_id
        app.__call__ = Mock(return_value='Test Application')
        proc._setOb(app_id, app)
        getattr(proc, app_id).id = app_id
        getattr(self.wf, proc_id).addActivity(act_id,
                            split_mode='xor',
                            join_mode='xor',
                            start_mode=1)
        getattr(self.wf, proc_id).begin = act_id
        self.wf.setProcessMappings(proc_id, '1', '1')

        env = Envelope(process=getattr(self.wf, proc_id),
                       title='FirstEnvelope',
                       authUser='TestUser',
                       year=2012,
                       endyear=2013,
                       partofyear='January',
                       country='http://spatial/1',
                       locality='TestLocality',
                       descr='TestDescription')
        env.id = env_id
        getattr(self.app, col_id)._setOb(env_id, env)
        setattr(self, col_id, getattr(self.app, col_id))
        setattr(self, env_id, getattr(getattr(self.app, col_id), env_id))
        getattr(self, env_id).startInstance(self.app.REQUEST)

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
        self.assertEqual(current_application, '/Applications/proc1/act1')


    def test_application_valid_rename(self):
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
        app = SimpleItem('bad_name').__of__(self.app.Applications.proc1)
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
        message = 'Application act1 mapped by path to activity /WorkflowEngine/proc1/act1.'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])


    def test_application_invalid_rename(self):
        self.create_cepaa_set(1)
        app = SimpleItem('Renamed_Draft').__of__(self.app.Applications.proc1)
        app.id = 'act1'
        self.app.Applications.proc1._setOb('act1', app)
        event = ObjectMovedEvent(
                    app,
                    self.app.Applications.proc1,
                    'bad_name',
                    self.app.Applications.proc1,
                    'still_bad_name'
                    )
        # simulate a ObjectMovedEvent catch
        OpenFlowEngine.handle_application_move_events(event)
        message = 'Id act1 does not match any activity name in process /WorkflowEngine/proc1. ' \
                  'Choose a valid name from this list: Begin, End, act1'
        self.assertEqual(message, self.app.REQUEST['manage_tabs_message'])

    def test_application_delete_good_name(self):
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
        self.assertEqual('Application /Applications/proc1/act1 '
                   'deleted! Activity /WorkflowEngine/proc1/act1 has no '
                   'application mapped by path now.',
                   self.app.REQUEST['manage_tabs_message'])

    def test_application_delete_bad_name(self):
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
        self.assertEqual('Application /Applications/proc1/bad_name deleted! '\
                         'It was not mapped by path to any activity',
                         self.app.REQUEST['manage_tabs_message'])

    def test_application_valid_creation(self):
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

    def test_application_invalid_creation(self):
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
        self.assertEqual('Application act1 mapped by path to activity /WorkflowEngine/proc2/act1. '
                         'Activity /WorkflowEngine/proc1/act1 has no '
                         'application mapped by path now.',
                         self.app.REQUEST['manage_tabs_message'])

    def test_application_invalid_move_from_one_process_to_another(self):
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
        message = 'Id act1 does not match any activity name in process /WorkflowEngine/proc2. ' \
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
        self.assertEqual('Application act1 mapped by path to activity /WorkflowEngine/proc1/act1. ',
                         self.app.REQUEST['manage_tabs_message'])

    def test_application_move_from_process_folder_to_exterior(self):
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
        self.assertEqual('Application /Applications/proc1/act1 '
                   'moved! Activity /WorkflowEngine/proc1/act1 has no '
                   'application mapped by path now.',
                   self.app.REQUEST['manage_tabs_message'])
