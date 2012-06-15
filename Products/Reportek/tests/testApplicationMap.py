import os, sys
from Testing import ZopeTestCase
from configurereportek import ConfigureReportek

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
