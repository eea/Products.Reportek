from Products.Reportek.exceptions import CannotPickProcess, NoProcessAvailable
from common import BaseTest, WorkflowTestCase, ConfigureReportek


class EnvelopeRenderingTestCase(BaseTest, ConfigureReportek):

    def setUp(self):
        super(EnvelopeRenderingTestCase, self).setUp()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.envelope = self.createStandardEnvelope()

    def test_overview_without_rights(self):
        from utils import publish_view
        self.assertIn('This envelope is not yet available for public view.\n',
                       publish_view(self.envelope).body)

    def test_overview_with_rights(self):
        from utils import chase_response, load_json
        from mock import Mock
        from AccessControl.User import User
        self.envelope.canViewContent = Mock(return_value=1)
        self.wf.canPullActivity = Mock(return_value=True)
        localities_table = load_json('localities_table.json')
        self.envelope.localities_table = Mock(return_value=localities_table)
        self.envelope.overview = Mock(return_value='Envelope Test Template')

        w_item_0 = getattr(self.envelope,'0')
        w_item_0.status = 'active'
        w_item_0.actor = 'gigel'
        user = User('gigel', 'gigel', ['manager'], '')
        self.assertEqual('Envelope Test Template', chase_response(self.envelope, user=user).body.strip())


class FindProcessTestCase(BaseTest, ConfigureReportek):

    messages = {
      CannotPickProcess: 'More than one process associated with this envelope',
      NoProcessAvailable: 'No process associated with this envelope'
    }

    def afterSetUp(self):
        super(FindProcessTestCase, self).afterSetUp()
        # don't createStandardDependencies; we need a clean slate here
        self.col = self.createStandardCollection()
        from mock import Mock
        self.app.REQUEST.AUTHENTICATED_USER = Mock()
        self.app.REQUEST.AUTHENTICATED_USER.getUserName.return_value = 'gigel'

    def assertCreateEnvelopeRaises(self, exception,
                                   dataflow=None, country=None):
        if not dataflow:
            dataflow = 'http://rod.eionet.eu.int/obligations/8'
        if not country:
            country = 'http://rod.eionet.eu.int/spatial/2'
        with self.assertRaisesRegexp(exception, self.messages.get(exception)):
            BaseTest.create_envelope(self.col)

    def test_NoProcessAvailable_exception(self):
        self.assertCreateEnvelopeRaises(NoProcessAvailable)

    def test_only_one_available(self):
        process_path = WorkflowTestCase.create_process(self, 'p1')
        self.assertEqual(BaseTest.create_envelope(self.col).process_path, process_path)

    def test_explicitly_vs_wild_dataflow(self):
        p_path2 = WorkflowTestCase.create_process(self, 'p2')
        self.assertEqual(BaseTest.create_envelope(self.col).process_path, p_path2)

    def test_explicitly_vs_wild_country(self):
        p_path2 = WorkflowTestCase.create_process(self, 'p2')
        self.assertEqual(BaseTest.create_envelope(self.col).process_path, p_path2)

    def test_wild_dataflow_vs_wild_country(self):
        WorkflowTestCase.create_process(self, 'p1', dataflows=['*'])
        WorkflowTestCase.create_process(self, 'p2', countries=['*'])
        self.assertCreateEnvelopeRaises(CannotPickProcess)

    def test_both_wild(self):
        WorkflowTestCase.create_process(self, 'p1', dataflows=['*'], countries=['*'])
        WorkflowTestCase.create_process(self, 'p2', dataflows=['*'], countries=['*'])
        self.assertCreateEnvelopeRaises(CannotPickProcess)

    def test_both_explicitly_specified(self):
        WorkflowTestCase.create_process(self, 'p1')
        WorkflowTestCase.create_process(self, 'p2')
        self.assertCreateEnvelopeRaises(CannotPickProcess)


class EnvelopePeriodValidationTestCase(BaseTest, ConfigureReportek):
    def afterSetUp(self):
        super(EnvelopePeriodValidationTestCase, self).afterSetUp()
        self.createStandardDependencies()
        self.col = self.createStandardCollection()

    def test_year_before_1000_redirection(self):
        from DateTime.interfaces import SyntaxError
        self.app.standard_html_header = ""
        self.app.standard_html_footer = ""
        self.assertRaises(SyntaxError,
                          lambda : BaseTest.create_envelope(self.col, year='206', endyear='2008'))

    def test_year_not_integer(self):
        envelope = BaseTest.create_envelope(self.col, year='abc', endyear='2008')
        self.assertEqual(envelope.year, 2008)
        self.assertEqual(envelope.endyear, 2008)

    def test_endyear_not_integer(self):
        envelope = BaseTest.create_envelope(self.col, year='abc', endyear='abc')
        self.assertEqual(envelope.year, '')
        self.assertEqual(envelope.endyear, '')
