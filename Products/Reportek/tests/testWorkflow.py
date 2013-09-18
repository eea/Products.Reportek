import unittest
import tempfile
import shutil
from path import path

from utils import create_fake_root

from StringIO import StringIO
from Products.Reportek import RepUtils
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
from configurereportek import ConfigureReportek
from Products.Reportek.constants import CONVERTERS_ID
from Products.Reportek.exceptions import CannotPickProcess, NoProcessAvailable
from common import (create_process, create_envelope, create_mock_request,
                    createStandardCollection, _BaseTest)
from Products.Reportek.OpenFlowEngine import OpenFlowEngine
from OFS.SimpleItem import SimpleItem


class EnvelopeRenderingTestCase(_BaseTest):

    def setUp(self):
        super(EnvelopeRenderingTestCase, self).setUp()
        envelope = create_envelope(self)
        envelope.standard_html_header = ""
        envelope.standard_html_footer = ""
        self.envelope = envelope

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
        w_item_0 = getattr(self.envelope,'0')
        w_item_0.status = 'active'
        w_item_0.actor = 'gigel'
        user = User('gigel', 'gigel', ['manager'], '')
        self.assertEqual('Envelope Test Template', chase_response(self.envelope, user=user).body.strip())


class FindProcessTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    messages = {
      CannotPickProcess: 'More than one process associated with this envelope',
      NoProcessAvailable: 'No process associated with this envelope'
    }


    def assertCreateEnvelopeRaises(self, exception,
                                   dataflow=None, country=None):
        if not dataflow:
            dataflow = 'http://rod.eionet.eu.int/obligations/8'
        if not country:
            country = 'http://rod.eionet.eu.int/spatial/2'
        with self.assertRaisesRegexp(exception, self.messages.get(exception)):
            create_envelope(self)

    def afterSetUp(self):
        self.createStandardCollection()
        self.wf = self.app.WorkflowEngine
        from mock import Mock
        self.app.REQUEST.AUTHENTICATED_USER = Mock()
        self.app.REQUEST.AUTHENTICATED_USER.getUserName.return_value = 'gigel'

    def test_NoProcessAvailable_exception(self):
        self.assertCreateEnvelopeRaises(NoProcessAvailable)

    def test_only_one_available(self):
        process_path = create_process(self, 'p1')
        self.assertEqual(create_envelope(self).process_path, process_path)

    def test_explicitly_vs_wild_dataflow(self):
        p_path1 = create_process(self, 'p1', dataflows=['*'])
        p_path2 = create_process(self, 'p2')
        self.assertEqual(create_envelope(self).process_path, p_path2)

    def test_explicitly_vs_wild_country(self):
        p_path1 = create_process(self, 'p1', countries=['*'])
        p_path2 = create_process(self, 'p2')
        self.assertEqual(create_envelope(self).process_path, p_path2)

    def test_wild_dataflow_vs_wild_country(self):
        create_process(self, 'p1', dataflows=['*'])
        create_process(self, 'p2', countries=['*'])
        self.assertCreateEnvelopeRaises(CannotPickProcess)

    def test_both_wild(self):
        create_process(self, 'p1', dataflows=['*'], countries=['*'])
        create_process(self, 'p2', dataflows=['*'], countries=['*'])
        self.assertCreateEnvelopeRaises(CannotPickProcess)

    def test_both_explicitly_specified(self):
        create_process(self, 'p1')
        create_process(self, 'p2')
        self.assertCreateEnvelopeRaises(CannotPickProcess)


class EnvelopePeriodValidationTestCase(_BaseTest):

    def test_year_before_1000_redirection(self):
        from DateTime.interfaces import SyntaxError
        self.app.standard_html_header = ""
        self.app.standard_html_footer = ""
        self.assertRaises(SyntaxError,
                          lambda : create_envelope(self, year='206', endyear='2008'))

    def test_year_not_integer(self):
        envelope = create_envelope(self, year='abc', endyear='2008')
        self.assertEqual(envelope.year, 2008)
        self.assertEqual(envelope.endyear, 2008)

    def test_endyear_not_integer(self):
        envelope = create_envelope(self, year='abc', endyear='abc')
        self.assertEqual(envelope.year, '')
        self.assertEqual(envelope.endyear, '')
