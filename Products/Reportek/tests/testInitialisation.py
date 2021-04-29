# from Testing import ZopeTestCase
# ZopeTestCase.installProduct('Reportek')
from common import BaseTest, ConfigureReportek


# FIXME Why are these tests necessary?
class InitialisationTestCase(BaseTest, ConfigureReportek):
    """ This simple test checks that when you start Zope, everything is created
        as expected
    """

    def afterSetUp(self):
        super(InitialisationTestCase, self).afterSetUp()
        self.createStandardCatalog()
        self.createStandardDependencies()

    def testCreation(self):
        """ Check for the correct creation of the WorkflowEngine """
        self.assertTrue(hasattr(self.app, 'WorkflowEngine'))
        # self.assertTrue(hasattr(self.app, 'Converters'))
        # self.assertTrue(hasattr(self.app, 'DataflowMappings'))
        # self.assertTrue(hasattr(self.app, 'QARepository'))
        self.assertTrue(hasattr(self.app, 'ReportekEngine'))
        self.assertTrue(hasattr(self.app, 'Catalog'))

    def testWorkflowEngine(self):
        of = getattr(self.app, 'WorkflowEngine')
        self.assertEquals(of.meta_type, 'Workflow Engine')
