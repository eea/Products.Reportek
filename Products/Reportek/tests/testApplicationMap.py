import os, sys
from Testing import ZopeTestCase
from configurereportek import ConfigureReportek

from common import _WorkflowTestCase
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Products.Reportek import constants

ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')


class ApplicationsTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):
    """ This simple test checks the Openflow engine
    """

    def afterSetUp(self):
        self.createStandardDependencies()
        self.wf = self.app.WorkflowEngine

    def testCreation(self):
        """ Check for the correct creation of the WorkflowEngine """
        self.assertTrue(hasattr(self.app, 'WorkflowEngine'))

    def test_application(self):
        """ Test that listApplications() returns the applications sorted on name """
        self.wf.addApplication(name="alpha_app", link="pyAuto")
        self.assertEquals( [{'name':'alpha_app','link':'pyAuto'}], self.wf.listApplications())
        self.wf.addApplication(name="delta_app", link="delta")
        self.wf.addApplication(name="beta_app", link="beta")
        self.assertEquals([{'link': 'pyAuto', 'name': 'alpha_app'},
            {'link': 'beta', 'name': 'beta_app'},
            {'link': 'delta', 'name': 'delta_app'}] , self.wf.listApplications())

class ActivityApplicationMapping(_WorkflowTestCase):
    """
    Test activity finds its application based on process that is part of
    """

    def setUp(self):
        super(ActivityApplicationMapping, self).setUp()
        self.app._setOb(
            constants.APPLICATIONS_FOLDER_ID,
            Folder(constants.APPLICATIONS_FOLDER_ID))
        self.apps_folder = getattr(self.app, constants.APPLICATIONS_FOLDER_ID)
        self.apps_folder._setOb(
            'Common',
            Folder('Common'))

    def test_activity_application_attribute(self):
        self.create_cepaa_set(1)
        # no matching app in Applications or Applications/Common
        self.app.Applications.proc1._delOb('act1')
        activity = self.wf.proc1.act1
        activity.application = 'act1'
        self.app._setOb('SomeFolder', Folder('SomeFolder'))
        ob = SimpleItem('act1')
        ob.id = 'act1'
        self.app.SomeFolder._setOb(ob.id, ob)
        result = activity.mapped_application()
        self.assertEqual('/SomeFolder/act1', result['path'])
        self.assertEqual('http://nohost/SomeFolder', result['parent_url'])
        self.assertEqual(False, result['mapped_by_path'])
        self.assertEqual(False, result['missing'])

    def test_activity_finds_app_in_proc_folder(self):
        self.create_cepaa_set(1)
        activity = self.wf.proc1.act1
        result = activity.mapped_application()
        self.assertEqual('/Applications/proc1/act1', result['path'])
        self.assertEqual('http://nohost/Applications/proc1', result['parent_url'])
        self.assertEqual(True, result['mapped_by_path'])
        self.assertEqual(False, result['missing'])

    def test_activity_finds_app_in_shared_folder(self):
        self.create_cepaa_set(1)
        activity = self.wf.proc1.act1
        # remove app act1 from proc1 folder
        self.app.Applications.proc1._delOb('act1')
        # add app act1 to Common folder
        ob = SimpleItem('act1')
        ob.id = 'act1'
        self.apps_folder.Common._setOb('act1', ob)
        result = activity.mapped_application()
        self.assertEqual('/Applications/Common/act1', result['path'])
        self.assertEqual('http://nohost/Applications/Common', result['parent_url'])
        self.assertEqual(True, result['mapped_by_path'])
        self.assertEqual(False, result['missing'])

    def test_activity_finds_no_app(self):
        self.create_cepaa_set(1)
        activity = self.wf.proc1.act1
        # remove app act1 from proc1 folder
        self.app.Applications.proc1._delOb('act1')
        result = activity.mapped_application()
        self.assertEqual(None, result['path'])
        self.assertEqual(None, result['parent_url'])
        self.assertEqual(False, result['mapped_by_path'])
        self.assertEqual(None, result['missing'])

    def test_activity_application_missing(self):
        self.create_cepaa_set(1)
        # no matching app in Applications or Applications/Common
        self.app.Applications.proc1._delOb('act1')
        activity = self.wf.proc1.act1
        activity.application = 'act1'
        self.app._setOb('SomeFolder', Folder('SomeFolder'))
        # app is not there
        #self.app.SomeFolder._setOb('act1', SimpleItem('act1'))
        result = activity.mapped_application()
        self.assertEqual('/SomeFolder/act1', result['path'])
        self.assertEqual(None, result['parent_url'])
        self.assertEqual(False, result['mapped_by_path'])
        self.assertEqual(True, result['missing'])
