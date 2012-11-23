import unittest
from StringIO import StringIO
from Products.Reportek import RepUtils
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
from configurereportek import ConfigureReportek
from Products.Reportek.constants import CONVERTERS_ID
from Products.Reportek.exceptions import CannotPickProcess, NoProcessAvailable
from common import (create_process, create_envelope, create_mock_request,
                    createStandardCollection, _BaseTest)


class EnvelopeRenderingTestCase(_BaseTest):

    def setUp(self):
        super(EnvelopeRenderingTestCase, self).setUp()
        envelope = create_envelope(self)
        envelope.standard_html_header = ""
        envelope.standard_html_footer = ""
        self.envelope = envelope

    def test_overview_without_rights(self):
        from utils import publish_view
        self.assertIn('This envelope is not yet available for public view.\nWork is still in progress.',
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


class DeploymentTest(unittest.TestCase):

    def create_app(self, _id):
        from OFS.SimpleItem import SimpleItem
        self.root._setObject(_id, SimpleItem(_id))
        getattr(self.root, _id).id = _id
        self.root.WorkflowEngine.addApplication(_id, getattr(self.root, _id).absolute_url())

    def setUp(self):
        super(DeploymentTest, self).setUp()
        from utils import create_fake_root
        from Products.Reportek.OpenFlowEngine import OpenFlowEngine
        self.root = create_fake_root()
        ob = OpenFlowEngine('WorkflowEngine', '')
        self.root._setObject(ob.id, ob)

        self.create_app('app1')
        self.create_app('app2')
        self.create_app('app3')

        self.root.WorkflowEngine.manage_addProcess('proc1', BeginEnd=0)
        self.root.WorkflowEngine.proc1.addActivity('act1', application='app1')
        self.root.WorkflowEngine.proc1.addActivity('act2', application='app2')

        self.root.WorkflowEngine.manage_addProcess('proc2', BeginEnd=0)
        self.root.WorkflowEngine.proc2.addActivity('act1', application='app3')
        self.root.WorkflowEngine.proc2.addActivity('act2', application='app2')

    def test_grouped_apps_list(self):
        from Products.Reportek.deploy_scripts import group_apps_by_process as gap
        apps = gap(self.root)
        self.assertEqual(apps,
                         [('proc1', ['app1','app2']),
                          ('proc2', ['app3', 'app2'])])

    def test_apps_move(self):
        from Products.Reportek.deploy_scripts import group_apps_by_process as gap
        from Products.Reportek.deploy_scripts import move_apps, apps_list
        grouped_apps = gap(self.root)

        for proc, apps in grouped_apps:
            for app in apps:
                app_obj = getattr(self.root, app, None)
                if not app_obj:
                    self.fail('"%s" application was not found at "/%s"' %(app, app) )
                self.assertEqual(app_obj.absolute_url(), '%s' %app)
        host_folder='Applications'
        move_apps(self.root, grouped_apps, host_folder=host_folder)

        for proc, apps in grouped_apps:
            host_folder_obj = getattr(self.root, host_folder)
            if not getattr(host_folder_obj, proc, None):
                self.fail('"%s" folder was not found in %s' %(proc, host_folder))
            for app in apps:
                path = 'Applications/%s/%s' %(proc, app)
                if apps_list(self.root)[app] > 1:
                    path = 'Applications/Common/%s' % app

                proc_obj = getattr(self.root.Applications, proc, None)
                app_obj = self.root.unrestrictedTraverse(path)
                if not app_obj:
                    self.fail('"%s" application was not found in "/Applications/%s"' %(app, proc) )

                #Check actual location
                self.assertEqual(app_obj.absolute_url(), path)

                #Check link to app in WorkflowEngine
                self.assertEqual(path, self.root.WorkflowEngine._applications[app]['url'])

    def test_common_folder(self):
        """Test number of files in ./Common"""

        self.create_app('app4')
        self.root.WorkflowEngine.manage_addProcess('proc3', BeginEnd=0)
        self.root.WorkflowEngine.proc3.addActivity('act1', application='app3')
        self.root.WorkflowEngine.proc3.addActivity('act2', application='app4')

        from Products.Reportek.deploy_scripts import group_apps_by_process as gap
        from Products.Reportek.deploy_scripts import move_apps, apps_list
        grouped_apps = gap(self.root)
        host_folder='Applications'
        move_apps(self.root, grouped_apps, host_folder=host_folder)
        common_apps = 0
        apps = apps_list(self.root)
        for value in apps.values():
            if value > 1:
                common_apps+=1
        self.assertEqual(2, common_apps)

    def test_proc_with_common_apps_has_no_folder(self):
        self.create_app('app4')
        self.root.WorkflowEngine.manage_addProcess('proc3', BeginEnd=0)
        self.root.WorkflowEngine.proc3.addActivity('act1', application='app3')
        self.root.WorkflowEngine.proc3.addActivity('act2', application='app4')

        from Products.Reportek.deploy_scripts import group_apps_by_process as gap
        from Products.Reportek.deploy_scripts import move_apps, apps_list
        grouped_apps = gap(self.root)
        host_folder='Applications'
        move_apps(self.root, grouped_apps, host_folder=host_folder)
        common_apps = 0
        dummy = lambda: self.root.unrestrictedTraverse('%s/proc2' %(host_folder))
        self.assertRaises(KeyError, dummy)



    def test_apps_list(self):
        from Products.Reportek.deploy_scripts import apps_list
        apps = apps_list(self.root)
        self.assertEqual([('app3', 1),
                          ('app2', 2),
                          ('app1', 1)],
                          apps.items())
