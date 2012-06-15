import os, sys
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')


class InitialisationTestCase(ZopeTestCase.ZopeTestCase):
    """ This simple test checks that when you start Zope, everything is created
        as expected
    """

    def testCreation(self):
        """ Check for the correct creation of the WorkflowEngine """
        self.assertTrue(hasattr(self.app, 'WorkflowEngine'))
        self.assertTrue(hasattr(self.app, 'Converters'))
        self.assertTrue(hasattr(self.app, 'DataflowMappings'))
        self.assertTrue(hasattr(self.app, 'QARepository'))
        self.assertTrue(hasattr(self.app, 'ReportekEngine'))
        self.assertTrue(hasattr(self.app, 'Catalog'))

    def testWorkflowEngine(self):
        of = getattr(self.app, 'WorkflowEngine')
        self.assertEquals(of.meta_type, 'Workflow Engine')
