import os, sys
from Testing import ZopeTestCase
from configurereportek import ConfigureReportek

ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')

TESTDIR = os.path.abspath(os.path.dirname(__file__))


class OpenflowTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):
    """ This simple test checks the Openflow engine
    """

    def afterSetUp(self):
        self.createStandardDependencies()
        self.wf = self.app.WorkflowEngine

    def testCreation(self):
        """ Check for the correct creation of the WorkflowEngine """
        self.assertTrue(hasattr(self.app, 'WorkflowEngine'))

    def test_exportxml(self):
        """ Check that the application exports one workflow correctly """
        exported = """<?xml version="1.0" encoding="ISO-8859-1"?><workflow>
<process rid="process1" title="" description="" priority="0" begin="Begin" end="End">
<activity rid='Begin' title=''
                split_mode='and' join_mode='and' self_assignable='1'
                start_mode='0' finish_mode='0' complete_automatically='1'
                subflow='' push_application='' application=''
                parameters='' description='' kind='standard'
                pushable_roles='' pullable_roles=''/>
<activity rid='End' title=''
                split_mode='and' join_mode='and' self_assignable='1'
                start_mode='0' finish_mode='0' complete_automatically='1'
                subflow='' push_application='' application=''
                parameters='' description='' kind='standard'
                pushable_roles='' pullable_roles=''/>
</process>
</workflow>
"""
        self.wf.manage_addProcess('process1', BeginEnd=1)
        self.wf.setProcessMappings('process1', '1', '1')
        self.assertEquals(exported, self.wf.exportToXml('process1', self.app.REQUEST))

    def test_importxml(self):
        of = getattr(self.app, 'WorkflowEngine')
        f = open(os.path.join(TESTDIR, 'workflow_example.xml'),'r')
        of.importFromXml(f)
        self.assertTrue(hasattr(of,'noise_dataflows'))

    def testWorkflowEngine(self):
        of = getattr(self.app, 'WorkflowEngine')
        self.assertEquals(of.meta_type, 'Workflow Engine')

    def test_getDataflows(self):
        """ Test that the dataflows were added correctly """
        assert self.exampledataflows == self.wf.getDataflows()

    def test_getCountries(self):
        """ Test that the countries were added correctly """
        assert self.examplelocalities == self.wf.getCountries()

    def test_processmap(self):
        # A process called begin_end is already set up in createStandardDependencies()
        # and mapped to dataflows=* and countries=*
        self.assertEquals( (0, 'WorkflowEngine/begin_end') ,
           self.wf.findProcess(['http://rod.eionet.eu.int/obligations/8'],'http://rod.eionet.eu.int/spatial/2'))

        # Set a specific mapping for dataflow 8 and country 2
        self.wf.manage_addProcess('process1', BeginEnd=1)
        self.wf.setProcessMappings('process1', '', '', ['http://rod.eionet.eu.int/obligations/8'], ['http://rod.eionet.eu.int/spatial/2'])

        # Set a specific mapping for dataflow 9 and 11 and country 2
        self.wf.manage_addProcess('process2', BeginEnd=1)
        self.wf.setProcessMappings('process2', '', '',
           ['http://rod.eionet.eu.int/obligations/9','http://rod.eionet.eu.int/obligations/11'],
           ['http://rod.eionet.eu.int/spatial/2'])

        # This envelope has one obligation, Number 9 maps to process2
        self.assertEquals( (0, 'WorkflowEngine/process2') ,
           self.wf.findProcess(['http://rod.eionet.eu.int/obligations/9'],
           'http://rod.eionet.eu.int/spatial/2'))

        # This envelope has two obligations, Number 9 maps to process2, 15 maps to default begin_end
        # Should NOT return (0, 'WorkflowEngine/begin_end')
        self.assertEquals( (0, 'WorkflowEngine/process2') ,
           self.wf.findProcess(['http://rod.eionet.eu.int/obligations/9','http://rod.eionet.eu.int/obligations/15'],
           'http://rod.eionet.eu.int/spatial/2'))

        # This envelope has two obligations, each maps to the same process
        self.assertEquals( (0, 'WorkflowEngine/process2') ,
           self.wf.findProcess(['http://rod.eionet.eu.int/obligations/9','http://rod.eionet.eu.int/obligations/11'],
           'http://rod.eionet.eu.int/spatial/2'))

        # This envelope has two obligations, each maps to a different process
        # Should NOT return (0, 'WorkflowEngine/begin_end')
        self.assertEquals( (1, ('CannotPickProcess', 'More than one process associated with this envelope')) ,
           self.wf.findProcess(['http://rod.eionet.eu.int/obligations/8','http://rod.eionet.eu.int/obligations/9'],
           'http://rod.eionet.eu.int/spatial/2'))

    def test_special_country(self):
        """ Check that one country can have a special default workflow """
        # Set a specific mapping for dataflow 8 and country 2 and 3
        self.wf.manage_addProcess('process1', BeginEnd=1)
        # Assign it as default to country 2
        self.wf.setProcessMappings('process1', '1', '', [], ['http://rod.eionet.eu.int/spatial/2','http://rod.eionet.eu.int/spatial/3'])
        # Check that country 8 gets the original
        self.assertEquals( (0, 'WorkflowEngine/begin_end') ,
           self.wf.findProcess(['http://rod.eionet.eu.int/obligations/8'],'http://rod.eionet.eu.int/spatial/8'))
        self.assertEquals( (0, 'WorkflowEngine/process1') ,
           self.wf.findProcess(['http://rod.eionet.eu.int/obligations/8'],'http://rod.eionet.eu.int/spatial/2'))

    def test_doubleentry(self):
        # The begin_end is not removed from the process map
        self.wf.manage_addProcess('process1', BeginEnd=1)
        self.wf.setProcessMappings('process1', '1', '1')
        self.assertEquals( (1, ('CannotPickProcess', 'More than one process associated with this envelope')) ,
           self.wf.findProcess(['http://rod.eionet.eu.int/obligations/8'],'http://rod.eionet.eu.int/spatial/2'))
