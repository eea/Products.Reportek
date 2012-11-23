import unittest
import tempfile
import shutil
from path import path
from Products.Reportek.tests.utils import create_fake_root
from extras.deploy_apps_migration.deploy_apps_migration_scripts import group_apps_by_process as gap
from extras.deploy_apps_migration.deploy_apps_migration_scripts import move_apps, apps_list
from OFS.SimpleItem import SimpleItem
from Products.Reportek.OpenFlowEngine import OpenFlowEngine
from Products.Reportek.ReportekEngine import ReportekEngine


class AppsMigrationDeploymentTest(unittest.TestCase):

    def create_app(self, _id):
        self.root._setObject(_id, SimpleItem(_id))
        getattr(self.root, _id).id = _id
        self.root.WorkflowEngine.addApplication(_id, getattr(self.root, _id).absolute_url())

    def setUp(self):
        self.root = create_fake_root()
        ob = OpenFlowEngine('WorkflowEngine', '')
        self.root._setObject(ob.id, ob)

        ob = ReportekEngine()
        self.root._setObject(ob.id, ob)

        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)

        tmp = path(tempfile.mkdtemp())
        self.addCleanup(tmp.rmtree)

        self.log_file = (tmp / 'log_file.txt')

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
        apps = gap(self.root)
        self.assertEqual(apps,
                         [('proc1', ['app1','app2']),
                          ('proc2', ['app3', 'app2'])])

    def test_apps_move(self):
        grouped_apps = gap(self.root)

        for proc, apps in grouped_apps:
            for app in apps:
                app_obj = getattr(self.root, app, None)
                if not app_obj:
                    self.fail('"%s" application was not found at "/%s"' %(app, app) )
                self.assertEqual(app_obj.absolute_url(), '%s' %app)
        host_folder='Applications'
        move_apps(self.root, delete=True)

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
        for app in apps_list(self.root).keys():
            self.assertNotIn(app, self.root.objectIds())

    def test_common_folder(self):
        """Test number of files in ./Common"""

        self.create_app('app4')
        self.root.WorkflowEngine.manage_addProcess('proc3', BeginEnd=0)
        self.root.WorkflowEngine.proc3.addActivity('act1', application='app3')
        self.root.WorkflowEngine.proc3.addActivity('act2', application='app4')

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

        grouped_apps = gap(self.root)
        host_folder='Applications'
        move_apps(self.root, grouped_apps, host_folder=host_folder)
        common_apps = 0
        dummy = lambda: self.root.unrestrictedTraverse('%s/proc2' %(host_folder))
        self.assertRaises(KeyError, dummy)

    def test_log_no_delete(self):
        with self.log_file.open('ab') as log_file:
            grouped_apps = gap(self.root)
            host_folder='Applications'
            move_apps(self.root, log=log_file)

        with self.log_file.open('rb') as log_file:
            actual_log = log_file.readlines()
            expected_log = ['Create Folder         | /Applications',
                            'Create Folder         | /Applications/Common',
                            'Create Folder         | /Applications/proc1',
                            'Move   simple item    | /app1 -> /Applications/proc1/app1',
                            'Update WorkflowEngine | app1',
                            'Move   simple item    | /app2 -> /Applications/Common/app2',
                            'Update WorkflowEngine | app2',
                            'Create Folder         | /Applications/proc2',
                            'Move   simple item    | /app3 -> /Applications/proc2/app3',
                            'Update WorkflowEngine | app3',
                            '\n',
                            'Processed: 3, Deleted: 0',]
            self.assertEqual(len(expected_log), len(actual_log))
            for expected, actual in zip(expected_log, actual_log):
                self.assertEqual(expected.strip(), actual.strip())

    def test_log_delete(self):
        with self.log_file.open('ab') as log_file:
            grouped_apps = gap(self.root)
            host_folder='Applications'
            move_apps(self.root, log=log_file, delete=True)

        with self.log_file.open('rb') as log_file:
            actual_log = log_file.readlines()
            expected_log = ['Create Folder         | /Applications',
                            'Create Folder         | /Applications/Common',
                            'Create Folder         | /Applications/proc1',
                            'Move   simple item    | /app1 -> /Applications/proc1/app1',
                            'Update WorkflowEngine | app1',
                            'Move   simple item    | /app2 -> /Applications/Common/app2',
                            'Update WorkflowEngine | app2',
                            'Create Folder         | /Applications/proc2',
                            'Move   simple item    | /app3 -> /Applications/proc2/app3',
                            'Update WorkflowEngine | app3',
                            '\n',
                            'Processed: 3, Deleted: 3',]
            self.assertEqual(len(expected_log), len(actual_log))
            for expected, actual in zip(expected_log, actual_log):
                self.assertEqual(expected.strip(), actual.strip())

    def test_wrong_app_name(self):
        """Test with wrong application name"""
        self.root.WorkflowEngine.manage_addProcess('proc3', BeginEnd=0)
        self.root.WorkflowEngine.proc3.addActivity('act1', application='worng')
        self.root.WorkflowEngine.proc3.addActivity('act2', application='mitsake')
        try:
            with self.log_file.open('ab') as log_file:
                move_apps(self.root, log=log_file)
        except TypeError as ex:
            if ex.message == "object of type 'NoneType' has no len()":
                self.fail('Process should not be interrupted by exception.')
        expected_log_tail = 'Not found             | worng, mitsake'
        with self.log_file.open('rb') as log_file:
            actual_log_tail = log_file.readlines()[-2]
            self.assertEqual(expected_log_tail, actual_log_tail.strip())

    def test_already_moved_app(self):
        from zExceptions import BadRequest
        try:
            move_apps(self.root)
            move_apps(self.root)
        except BadRequest as ex:
            self.fail("Exception shouldn't have been raised")

    def test_defined_but_not_used(self):
        self.create_app('app4')
        with self.log_file.open('ab') as log_file:
            move_apps(self.root, log=log_file)
        expected_log_tail = 'Not used              | app4'
        with self.log_file.open('rb') as log_file:
            actual_log_tail = log_file.readlines()[-2]
            self.assertEqual(expected_log_tail, actual_log_tail.strip())

    def test_apps_list(self):
        apps = apps_list(self.root)
        self.assertEqual([('app3', 1),
                          ('app2', 2),
                          ('app1', 1)],
                          apps.items())

    def test_update_path_to_QA_application(self):
        self.create_app('qa_application')
        self.root.ReportekEngine.QA_application = 'qa_application'
        self.root.WorkflowEngine.manage_addProcess('dummy_proc1', BeginEnd=0)
        self.root.WorkflowEngine.dummy_proc1.addActivity(
            'qa_application',
            application='qa_application')
        self.root.WorkflowEngine.manage_addProcess('dummy_proc2', BeginEnd=0)
        self.root.WorkflowEngine.dummy_proc2.addActivity(
            'qa_application',
            application='qa_application')
        move_apps(self.root)
        self.assertEqual(
            'Applications/Common/qa_application',
            self.root.ReportekEngine.QA_application)

