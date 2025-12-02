import os

from Testing import ZopeTestCase

from Products.Reportek.exceptions import CannotPickProcess
from Products.Reportek.RepUtils import inline_replace

from .common import BaseTest, ConfigureReportek

ZopeTestCase.installProduct("Reportek")
ZopeTestCase.installProduct("PythonScripts")

TESTDIR = os.path.abspath(os.path.dirname(__file__))


class OpenflowTestCase(BaseTest, ConfigureReportek):
    """This simple test checks the Openflow engine"""

    def afterSetUp(self):
        super(OpenflowTestCase, self).afterSetUp()
        self.createStandardCatalog()
        self.createStandardDependencies()

    def testCreation(self):
        """Check for the correct creation of the WorkflowEngine"""
        self.assertTrue(hasattr(self.app, "WorkflowEngine"))

    def testWorkflowEngine(self):
        of = getattr(self.app, "WorkflowEngine")
        self.assertEqual(of.meta_type, "Workflow Engine")

    def test_getDataflows(self):
        """Test that the dataflows were added correctly"""
        assert (
            list(map(inline_replace, self.exampledataflows))
            == self.wf.getDataflows()
        )

    def test_getCountries(self):
        """Test that the countries were added correctly"""
        assert (
            list(map(inline_replace, self.examplelocalities))
            == self.wf.getCountries()
        )

    def test_processmap(self):
        # A process called begin_end is already set up in
        # createStandardDependencies() and mapped to dataflows=*
        # and countries=*
        self.assertEqual(
            (0, "WorkflowEngine/begin_end"),
            self.wf.findProcess(
                ["http://rod.eionet.eu.int/obligations/8"],
                "http://rod.eionet.eu.int/spatial/2",
            ),
        )

        # Set a specific mapping for dataflow 8 and country 2
        self.wf.manage_addProcess("process1", BeginEnd=1)
        self.wf.setProcessMappings(
            "process1",
            "",
            "",
            ["http://rod.eionet.eu.int/obligations/8"],
            ["http://rod.eionet.eu.int/spatial/2"],
        )

        # Set a specific mapping for dataflow 9 and 11 and country 2
        self.wf.manage_addProcess("process2", BeginEnd=1)
        self.wf.setProcessMappings(
            "process2",
            "",
            "",
            [
                "http://rod.eionet.eu.int/obligations/9",
                "http://rod.eionet.eu.int/obligations/11",
            ],
            ["http://rod.eionet.eu.int/spatial/2"],
        )

        # This envelope has one obligation, Number 9 maps to process2
        self.assertEqual(
            (0, "WorkflowEngine/process2"),
            self.wf.findProcess(
                ["http://rod.eionet.eu.int/obligations/9"],
                "http://rod.eionet.eu.int/spatial/2",
            ),
        )

        # This envelope has two obligations, Number 9 maps to process2,
        # 15 maps to default begin_end
        # Should NOT return (0, 'WorkflowEngine/begin_end')
        self.assertEqual(
            (0, "WorkflowEngine/process2"),
            self.wf.findProcess(
                [
                    "http://rod.eionet.eu.int/obligations/9",
                    "http://rod.eionet.eu.int/obligations/15",
                ],
                "http://rod.eionet.eu.int/spatial/2",
            ),
        )

        # This envelope has two obligations, each maps to the same process
        self.assertEqual(
            (0, "WorkflowEngine/process2"),
            self.wf.findProcess(
                [
                    "http://rod.eionet.eu.int/obligations/9",
                    "http://rod.eionet.eu.int/obligations/11",
                ],
                "http://rod.eionet.eu.int/spatial/2",
            ),
        )

        # This envelope has two obligations, each maps to a different process
        # Should NOT return (0, 'WorkflowEngine/begin_end')
        self.assertEqual(
            (
                1,
                (
                    CannotPickProcess,
                    "More than one process associated with this envelope",
                ),
            ),
            self.wf.findProcess(
                [
                    "http://rod.eionet.eu.int/obligations/8",
                    "http://rod.eionet.eu.int/obligations/9",
                ],
                "http://rod.eionet.eu.int/spatial/2",
            ),
        )

    def test_special_country(self):
        """Check that one country can have a special default workflow"""
        # Set a specific mapping for dataflow 8 and country 2 and 3
        self.wf.manage_addProcess("process1", BeginEnd=1)
        # Assign it as default to country 2
        self.wf.setProcessMappings(
            "process1",
            "1",
            "",
            [],
            [
                "http://rod.eionet.eu.int/spatial/2",
                "http://rod.eionet.eu.int/spatial/3",
            ],
        )
        # Check that country 8 gets the original
        self.assertEqual(
            (0, "WorkflowEngine/begin_end"),
            self.wf.findProcess(
                ["http://rod.eionet.eu.int/obligations/8"],
                "http://rod.eionet.eu.int/spatial/8",
            ),
        )
        self.assertEqual(
            (0, "WorkflowEngine/process1"),
            self.wf.findProcess(
                ["http://rod.eionet.eu.int/obligations/8"],
                "http://rod.eionet.eu.int/spatial/2",
            ),
        )

    def test_doubleentry(self):
        # The begin_end is not removed from the process map
        self.wf.manage_addProcess("process1", BeginEnd=1)
        self.wf.setProcessMappings("process1", "1", "1")
        self.assertEqual(
            (
                1,
                (
                    CannotPickProcess,
                    "More than one process associated with this envelope",
                ),
            ),
            self.wf.findProcess(
                ["http://rod.eionet.eu.int/obligations/8"],
                "http://rod.eionet.eu.int/spatial/2",
            ),
        )
