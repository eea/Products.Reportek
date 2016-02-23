from AccessControl.Permissions import view_management_screens
from Products.Five import zcml
from Products.Five.testbrowser import Browser
from Products.PageTemplates.ZopePageTemplate import manage_addPageTemplate
from Products.PythonScripts.PythonScript import manage_addPythonScript
from Testing import ZopeTestCase as ztc
import os
import Products.Five
import Products.GenericSetup
import transaction

from OFS.Folder import Folder
from OFS.Image import manage_addFile
from OFS.SimpleItem import SimpleItem
from Products.Reportek import create_reportek_indexes, create_reportek_objects
from Products.Reportek import constants
from Products.Reportek.config import *
from Products.Reportek.ReportekEngine import ReportekEngine
from datetime import date, timedelta

ztc.installProduct('PluginIndexes')
ztc.installProduct('PythonScripts')
ztc.installProduct('PageTemplates')
ztc.installProduct('ZCatalog')
ztc.installProduct('ZCTextIndex')
ztc.installProduct('Reportek')
ztc.installProduct('GenericSetup')

zcml.load_config('meta.zcml', Products.Five)
zcml.load_config('configure.zcml', Products.Five)
zcml.load_config('meta.zcml', Products.GenericSetup)
zcml.load_config('configure.zcml', Products.GenericSetup)

user_name = ztc.user_name
user_password = ztc.user_password


class MockedLDAPPlugin(Folder):
    acl_users = None


class MockedACLUsers(Folder):

    def getUserById(self, name):
        return getattr(self, name, None)

    def getLDAPSchema(self):
        return (('cn', 'Canonical Name'), ('mail', 'Mail'),
                ('sn', 'Last Name'), ('uid', 'uid'))

    def findUser(self, *args, **kwargs):
        search_term = kwargs.pop('search_term')
        search_param = kwargs.pop('search_param')
        users = []

        for obj_id in self.objectIds():
            user = self._getOb(obj_id)
            if getattr(user, search_param, None) == search_term:
                user_dict = {
                    'dn': '',
                    'mail': user.mail,
                    'uid': user.uid,
                    'sn': user.sn,
                    'cn': user.cn
                }
                users.append(user_dict)
        return users


class MockedLDAPUser(SimpleItem):

    def __init__(self, uid):
        self.uid = uid

    def __getitem__(self, name):
        return getattr(self, name, None)

    def getProperty(self, prop, default=''):
        return getattr(self, prop, default)

    @property
    def cn(self):
        return self._cn

    @cn.setter
    def cn(self, value):
        self._cn = value

    @property
    def mail(self):
        return self._mail

    @mail.setter
    def mail(self, value):
        self._mail = value

    @property
    def sn(self):
        return self._sn

    @sn.setter
    def sn(self, value):
        self._sn = value

    @property
    def uid(self):
        return self._uid

    @uid.setter
    def uid(self, value):
        self._uid = value

DTMLS = [
    {
        'dtml_id': 'standard_html_header',
        'title': 'Standard Html Header',
        'filename': 'standard_html_header.dtml'
    },
    {
        'dtml_id': 'breadcrumbtrail',
        'title': 'Trail of breadcrumbs',
        'filename': 'breadcrumbtrail.dtml'
    },
    {
        'dtml_id': 'standard_html_footer',
        'title': 'Standard Html Footer',
        'filename': 'standard_html_footer.dtml'
    }
]

SCRIPTS = [
    {
        'script_id': 'buttons_loginout',
        'filename': 'buttons_loginout.py'
    },
    {
        'script_id': 'buttons_py',
        'filename': 'buttons_py.py'
    }
]

FILES = [
    {
        'file_id': 'dropdownmenus.txt',
        'contenttype': 'text/plain',
        'title': 'dropdownmenus.txt',
        'filename': 'dropdownmenus.txt'
    }
]

TEMPLATES = [
    {
        'template_id': 'standard_template.pt',
        'title': '',
        'filename': 'standard_template.pt'
    },
    {
        'template_id': 'breadcrumbs_views',
        'title': '',
        'filename': 'breadcrumbs_views.pt'
    }
]


def get_localities_rod(self):
    return [
        {
            'iso': 'tc',
            'name': 'Test Country',
            'uri': 'http://nohost/spatial/1'
        },
        {
            'iso': 'oc',
            'name': 'Other Country',
            'uri': 'http://nohost/spatial/2'
        }
    ]


def get_dataflow_rod(self):
    return [
        {
            'terminated': '0',
            'PK_RA_ID': '8',
            'SOURCE_TITLE': 'Fictive Convention',
            'details_url': 'http://nohost/obligations/1',
            'TITLE': 'Yearly report to the Fictive Convention',
            'uri': 'http://nohost/obligations/1',
            'LAST_UPDATE': '2009-12-15',
            'PK_SOURCE_ID': '142'
        }
    ]

orig_localities_rod = ReportekEngine.localities_rod
orig_dataflow_rod = ReportekEngine.dataflow_rod


class BaseFunctionalTestCase(ztc.FunctionalTestCase):
    # _setup_fixture = 0

    def addObject(self, container, name, id, product='Reportek', **kw):
        getattr(container.manage_addProduct[product],
                'manage_add%s' % name)(id=id, **kw)
        transaction.savepoint()
        return getattr(container, id)

    def _setupReportek(self):
        create_reportek_objects(self.app)
        catalog = getattr(self.app, 'Catalog')
        create_reportek_indexes(catalog)
        r_utilities = getattr(self.app, constants.REPORTEK_UTILITIES)
        r_utilities.manage_permission(view_management_screens,
                                      roles=['Owner'])
        r_utilities._p_changed = True

    def _setupDTMLS(self):
        for dtml in DTMLS:
            dtml_path = os.path.join(os.path.dirname(__file__),
                                     'data', dtml.get('filename'))
            with open(dtml_path, 'rb') as f:
                f.seek(0)
                dtml_content = f.read()
                self.app.manage_addDTMLMethod(dtml.get('dtml_id'),
                                              dtml.get('title'),
                                              dtml_content)

    def _setupSCRIPTS(self):
        for script in SCRIPTS:
            script_path = os.path.join(os.path.dirname(__file__),
                                       'data', script.get('filename'))
            with open(script_path, 'rb') as f:
                f.seek(0)
                script_content = f.read()
                manage_addPythonScript(self.app, id=script.get('script_id'))
                script1 = getattr(self.app, script.get('script_id'))
                script1.write(script_content)

    def _setupFILES(self):
        for file in FILES:
            file_path = os.path.join(os.path.dirname(__file__),
                                     'data', file.get('filename'))
            with open(file_path, 'rb') as f:
                manage_addFile(self.app, file.get('file_id'), file=f,
                               title=file.get('title'),
                               content_type=file.get('contenttype'))

    def _setupTMPLS(self):
        for tmpl in TEMPLATES:
            tmpl_path = os.path.join(os.path.dirname(__file__),
                                     'data', tmpl.get('filename'))
            with open(tmpl_path, 'rb') as f:
                f.seek(0)
                tmpl_content = f.read()
                manage_addPageTemplate(self.app, id=tmpl.get('template_id'),
                                       title=tmpl.get('title'),
                                       text=tmpl_content)

    def _setup_users(self):
        local_roles = ['Reporter', 'Client']
        data = list(self.app.__ac_roles__)

        for role in local_roles:
            data.append(role)
        self.app.__ac_roles__ = tuple(data)

        self.app.acl_users.userFolderAddUser(user_name, user_password,
                                             ['Manager', 'Reporter'], [])
        self.setRoles('Reporter', name=user_name)
        self.login(user_name)
        self.browser.addHeader('Authorization',
                               'Basic ' + user_name + ':' + user_password)
        transaction.commit()

    def _setup_collections(self):
        collection = self.addObject(self.app,
                                    name='Collection',
                                    id='tc',
                                    title='Test Country',
                                    descr='',
                                    year=None,
                                    endyear=None,
                                    partofyear='Whole Year',
                                    country='http://nohost/spatial/1',
                                    locality='',
                                    dataflow_uris=['http://nohost/obligations/1'],
                                    allow_collections=1,
                                    allow_envelopes=1)
        dict = collection.__ac_local_roles__
        local_roles = list(dict.get(user_name, []))
        local_roles.append('Reporter')
        dict[user_name] = local_roles
        collection.reindex_object()
        collection._p_changed = True

        collection = self.addObject(self.app,
                                    name='Collection',
                                    id='oc',
                                    title='Other Country',
                                    descr='',
                                    year=None,
                                    endyear=None,
                                    partofyear='Whole Year',
                                    country='http://nohost/spatial/2',
                                    locality='',
                                    dataflow_uris=['http://nohost/obligations/1'],
                                    allow_collections=1,
                                    allow_envelopes=1)
        dict = collection.__ac_local_roles__
        local_roles = list(dict.get(user_name, []))
        local_roles.append('Reporter')
        dict[user_name] = local_roles
        collection.reindex_object()
        collection._p_changed = True

        collection = self.addObject(collection,
                                    name='Collection',
                                    id='eea',
                                    title='EEA Folder',
                                    descr='',
                                    year=None,
                                    endyear=None,
                                    partofyear='Whole Year',
                                    country='http://nohost/spatial/2',
                                    locality='',
                                    dataflow_uris=['http://nohost/obligations/1'],
                                    allow_collections=1,
                                    allow_envelopes=1)
        dict = collection.__ac_local_roles__
        local_roles = list(dict.get(user_name, []))
        local_roles.append('Reporter')
        dict[user_name] = local_roles
        collection.reindex_object()
        collection._p_changed = True

        collection = self.addObject(collection,
                                    name='Collection',
                                    id='requests',
                                    title='Requests Folder',
                                    descr='',
                                    year=None,
                                    endyear=None,
                                    partofyear='Whole Year',
                                    country='http://nohost/spatial/2',
                                    locality='',
                                    dataflow_uris=['http://nohost/obligations/1'],
                                    allow_collections=1,
                                    allow_envelopes=1)
        dict = collection.__ac_local_roles__
        local_roles = list(dict.get(user_name, []))
        local_roles.append('Reporter')
        dict[user_name] = local_roles
        collection.reindex_object()
        collection._p_changed = True

    def setUp(self):
        super(BaseFunctionalTestCase, self).setUp()
        ReportekEngine.localities_rod = get_localities_rod
        ReportekEngine.dataflow_rod = get_dataflow_rod

    def tearDown(self):
        ReportekEngine.localities_rod = orig_localities_rod
        ReportekEngine.dataflow_rod = orig_dataflow_rod

    def afterSetUp(self):
        self.browser = Browser()
        self.browser.handleErrors = False
        try:
            import Products.Reportek
            zcml.load_config('configure.zcml', Products.Reportek)
        except ImportError:
            pass

        self.setRoles('Reporter')
        self._setup_users()
        self._setupReportek()

        self.app.manage_addProperty('management_page_charset',
                                    'utf-8', 'string')
        self._setupDTMLS()
        self._setupSCRIPTS()
        self._setupFILES()
        self._setupTMPLS()
        self._setup_collections()

        # create wf process
        wf_engine = getattr(self.app, 'WorkflowEngine')
        p_dataflows = ['http://nohost/obligations/1']
        p_countries = ['http://nohost/spatial/1', 'http://nohost/spatial/2']
        wf_engine.manage_addProcess('process', BeginEnd=1)
        wf_engine.setProcessMappings('process', '1', '1', p_dataflows,
                                     p_countries)

        # add our mocked ldapmultiplugin
        ldapmultiplugin = MockedLDAPPlugin()
        self.app.acl_users.ldapmultiplugin = ldapmultiplugin
        acl_users = MockedACLUsers()
        self.app.acl_users.ldapmultiplugin._setObject('acl_users', acl_users)
        mock_user = MockedLDAPUser('test_user_1_')
        mock_user.cn = 'test_user_1_'
        mock_user.sn = 'user'
        mock_user.mail = 'test_user_1_@test.com'
        acl_users._setObject('test_user_1_', mock_user)

    # FIXME test config does not include views.cdr.zcml
    if False and REPORTEK_DEPLOYMENT != DEPLOYMENT_BDR:
        def test_build_collections(self):
            # Go to ReportekUtilities index_html view
            r_utilities = getattr(self.app, constants.REPORTEK_UTILITIES)
            ru_url = r_utilities.absolute_url()
            index_url = ru_url + '/index_html'
            self.browser.open(index_url)
            self.assertEqual(self.browser.url, index_url)

            # Test with one country
            # Go to build collections
            users_access_link = self.browser.getLink(text='Build collections')
            users_access_link.click()
            self.assertTrue('Build collections' in self.browser.contents)

            # Select test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            # Select test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                if c_ctl.optionValue == 'tc':
                    c_ctl.selected = True

            self.browser.getControl(name='cid').value = 'test'
            self.browser.getControl(name='btn.submit').click()
            self.assertTrue('Successfully created collection for' in self.browser.contents)
            self.assertTrue('Test Country' in self.browser.contents)

            # Test with multiple countries
            # Select test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            # Select test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                c_ctl.selected = True

            self.browser.getControl(name='cid').value = 'test1'
            self.browser.getControl(name='btn.submit').click()
            self.assertTrue('Successfully created collection for' in self.browser.contents)
            self.assertTrue('Test Country' in self.browser.contents)
            self.assertTrue('Other Country' in self.browser.contents)

            # Test inexistent path
            # Select test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            # Select test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                if c_ctl.optionValue == 'tc':
                    c_ctl.selected = True

            self.browser.getControl(name='cid').value = 'test2'
            self.browser.getControl(name='pattern').value = 'eea'
            self.browser.getControl(name='btn.submit').click()
            self.assertTrue('the specified path does not exist' in self.browser.contents)
            self.assertTrue('Test Country' in self.browser.contents)

            # Test existent path
            # Select test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            # Select test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                if c_ctl.optionValue == 'oc':
                    c_ctl.selected = True

            self.browser.getControl(name='cid').value = 'test2'
            self.browser.getControl(name='pattern').value = 'eea'
            self.browser.getControl(name='btn.submit').click()
            self.assertTrue('Successfully created collection for' in self.browser.contents)
            self.assertTrue('Other Country' in self.browser.contents)

            # Test existent multilevel path
            # Select test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            # Select test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                if c_ctl.optionValue == 'oc':
                    c_ctl.selected = True

            self.browser.getControl(name='cid').value = 'test3'
            self.browser.getControl(name='pattern').value = 'eea/requests'
            self.browser.getControl(name='btn.submit').click()
            self.assertTrue('Successfully created collection for' in self.browser.contents)
            self.assertTrue('Other Country' in self.browser.contents)

            # Test existent path with leading slash
            # Select test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            # Select test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                if c_ctl.optionValue == 'oc':
                    c_ctl.selected = True

            self.browser.getControl(name='cid').value = 'test4'
            self.browser.getControl(name='pattern').value = '/eea'
            self.browser.getControl(name='btn.submit').click()
            self.assertTrue('Successfully created collection for' in self.browser.contents)
            self.assertTrue('Other Country' in self.browser.contents)

            # Test existent path with backslash
            # Select test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            # Select test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                if c_ctl.optionValue == 'oc':
                    c_ctl.selected = True

            self.browser.getControl(name='cid').value = 'test5'
            self.browser.getControl(name='pattern').value = '\eea'
            self.browser.getControl(name='btn.submit').click()
            self.assertTrue('Successfully created collection for' in self.browser.contents)
            self.assertTrue('Other Country' in self.browser.contents)

    def _check_controls(self, contents):
        self.assertTrue('Back to utilities' in contents)

    def test_reportek_utilities(self):
        # Go to ReportekUtilities index_html view
        self.setRoles('Manager')
        r_utilities = getattr(self.app, constants.REPORTEK_UTILITIES)
        ru_url = r_utilities.absolute_url()
        index_url = ru_url + '/index_html'
        self.browser.open(index_url)
        self.assertEqual(self.browser.url, index_url)

        # Go to users that have access
        users_access_link = self.browser.getLink(text='Show where users have roles')
        users_access_link.click()
        self._check_controls(self.browser.contents)
        self.assertTrue('Yearly report to the Fictive Convention' in
                        self.browser.contents)

        # Select test obligation
        o_controls = self.browser.getControl(name='obligations:list').controls
        for o_control in o_controls:
            if o_control.optionValue == '8':
                o_control.selected = True

        # Select test country
        c_controls = self.browser.getControl(name='countries:list').controls
        for c_ctl in c_controls:
            if c_ctl.optionValue == 'tc':
                c_ctl.selected = True

        # Filter
        self.browser.getControl(name='btnFilter').click()
        self._check_controls(self.browser.contents)

        # We have an ajax call that we need to see the result of
        ajax_url = self.app.absolute_url() + '/api.get_users_by_path'
        self.browser.post(ajax_url, 'obligation=8&role=&countries%5B%5D=tc')
        expected_result = ('{"data": [{"obligations": ['
                          '["http://nohost/obligations/1", '
                          '"Yearly report to the Fictive Convention"]], '
                          '"users": {"test_user_1_": {'
                          '"role": ["Owner", "Reporter"], '
                          '"uid": "test_user_1_"}}, '
                          '"collection": {"path": "/tc", '
                          '"type": "Report Collection", '
                          '"title": "Test Country"}}]}')
        self.assertEqual(expected_result, self.browser.contents)

        # Go back to ReportekUtilities index_html
        self.browser.goBack(count=3)

        if REPORTEK_DEPLOYMENT != DEPLOYMENT_BDR:
            # Click on the list country reporters
            self.browser.getLink(text='List country reporters').click()
            self._check_controls(self.browser.contents)
            self.browser.getControl(label='Show reporters').click()
            self._check_controls(self.browser.contents)
            # test_user_1_ should come up in the reporters list
            self.assertTrue('test_user_1_@test.com' in self.browser.contents)

            self.browser.goBack(count=2)
            self.browser.getLink(text='Assign roles by obligation').click()
            self._check_controls(self.browser.contents)
            self.assertEqual(ru_url + '/@@assign_role', self.browser.url)
            search_term_ctl = self.browser.getControl(name='search_term')
            search_term_ctl.value = 'test_user_1_'
            self.browser.getControl(name='btnFind').click()

            # Select our test user
            username_ctl = self.browser.getControl(name='username')
            for ctl in username_ctl.controls:
                if ctl.optionValue == 'test_user_1_':
                    ctl.selected = True

            # Select our test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                if c_ctl.optionValue == 'tc':
                    c_ctl.selected = True

            # Select our test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            # Set role to 'Client'
            r_controls = self.browser.getControl(name='role').controls
            for r_control in r_controls:
                if r_control.optionValue == 'Client':
                    r_control.selected = True

            # Get available collections
            self.browser.getControl(name='btn.find_collections').click()
            col_controls = self.browser.getControl(name='collections:list').controls
            self.assertEqual(col_controls[0].optionValue, '/tc,')
            self.assertTrue('(Owner, Reporter)' in self.browser.contents)
            col_controls[0].selected = True

            # Assign new role
            self.browser.getControl(name='btn.assign').click()
            self._check_controls(self.browser.contents)
            self.assertTrue('Roles assigned: ' in self.browser.contents)

            search_term_ctl = self.browser.getControl(name='search_term')
            search_term_ctl.value = 'test_user_1_'
            self.browser.getControl(name='btnFind').click()
            self.browser.getControl(name='username').controls[0].selected = True
            self.browser.getControl(name='countries:list').controls[0].selected = True
            self.browser.getControl(name='obligations:list').controls[0].selected = True
            r_controls = self.browser.getControl(name='role').controls
            for r_control in r_controls:
                if r_control.optionValue == 'Client':
                    r_control.selected = True
            self.browser.getControl(name='btn.find_collections').click()
            self.assertTrue('(Owner, Client, Reporter)' in self.browser.contents)

            # Go to ReportekUtilities
            self.browser.goBack(count=6)

            # Go to search Search for collection with obligation view
            self.browser.getLink(text='Create envelopes').click()
            self._check_controls(self.browser.contents)
            self.browser.getControl(name='obligations:list').controls[0].selected = True
            self.browser.getControl(name='btn.search').click()
            self.assertTrue('Test Country' in self.browser.contents)

            # Create test empty envelope
            self.browser.getControl(name='title').value = 'Test envelope'
            self.browser.getControl(name='year:int').value = '2014'
            self.browser.getControl(name='btn.create').click()
            self._check_controls(self.browser.contents)
            self.assertTrue('Operations completed succesfully.' in
                            self.browser.contents)

            self.browser.goBack(count=3)

            # Go the Collections allocated to the wrong country view
            self.browser.getLink(text='Collections allocated to the wrong country').click()
            self._check_controls(self.browser.contents)
            self.assertTrue('All the collections in this site have the correct country.' in
                            self.browser.contents)

            self.browser.goBack(count=1)

            # Go to Envelopes allocated to the wrong country view
            self.browser.getLink(text='Envelopes allocated to the wrong country').click()
            self.assertTrue('All the envelopes in this site have the correct country.' in
                            self.browser.contents)

            self.browser.goBack(count=1)

            # Go to Recent uploads view
            self.browser.getLink(text='Recent uploads').click()
            self._check_controls(self.browser.contents)

            # Select our test country
            c_controls = self.browser.getControl(name='countries:list').controls
            for c_ctl in c_controls:
                if c_ctl.optionValue == 'tc':
                    c_ctl.selected = True

            # Select our test obligation
            o_controls = self.browser.getControl(name='obligations:list').controls
            for o_control in o_controls:
                if o_control.optionValue == '8':
                    o_control.selected = True

            min_date = date.today() - timedelta(days=3)
            mid_date = date.today() - timedelta(days=1)
            max_date = date.today() + timedelta(days=3)

            # Test without start and end dates
            self.browser.getControl(name='btn.search').click()
            self.assertTrue('Test envelope' in self.browser.contents)
            # Test with end date
            self.browser.getControl(name='enddate').value = min_date.strftime('%Y-%m-%d')
            self.browser.getControl(name='btn.search').click()
            self.assertTrue('No envelopes.' in self.browser.contents)
            # Test with start date
            self.browser.getControl(name='startdate').value = min_date.strftime('%Y-%m-%d')
            self.browser.getControl(name='btn.search').click()
            self.assertTrue('Test envelope' in self.browser.contents)
            # Test with start and end dates
            self.browser.getControl(name='startdate').value = min_date.strftime('%Y-%m-%d')
            self.browser.getControl(name='enddate').value = max_date.strftime('%Y-%m-%d')
            self.browser.getControl(name='btn.search').click()
            self.assertTrue('Test envelope' in self.browser.contents)
            # Test with start and end dates
            self.browser.getControl(name='startdate').value = min_date.strftime('%Y-%m-%d')
            self.browser.getControl(name='enddate').value = mid_date.strftime('%Y-%m-%d')
            self.browser.getControl(name='btn.search').click()
            self.assertTrue('No envelopes.' in self.browser.contents)
            self.browser.goBack(count=6)

            # FIXME test config does not include views.cdr.zcml
            #if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
            #    # Go to statistics view
            #    self.browser.getLink(text='Statistics').click()
            #    self.assertTrue('<li>Number of envelopes: <span>4</span></li>' in
            #                    self.browser.contents)

            # Go to evenlopes.autocomplete view
            self.browser.open(ru_url + '/envelopes.autocomplete')
            self._check_controls(self.browser.contents)

            # Search our inactive test envelope
            self.browser.getControl(name='obligations:list').controls[0].selected = True
            status = self.browser.getControl(name='status').controls
            for status_ctl in status:
                if status_ctl.optionValue == 'Inactive':
                    status_ctl.selected = True

            self.browser.getControl(name='btn.search').click()
            self.assertTrue('Test envelope' in self.browser.contents)

            # Move forward our envelope
            self.browser.getControl(name='btn.autocomplete').click()
            self.assertTrue('Operations completed succesfully.' in
                            self.browser.contents)

            self.browser.goBack(count=3)

        # Go to revoke roles view
        self.browser.getLink(text='Revoke roles').click()
        self._check_controls(self.browser.contents)
        self.assertEqual(ru_url + '/@@revoke_roles',
                         self.browser.url)

        # Search for our test user
        search_term_ctl = self.browser.getControl(name='search_term')
        search_term_ctl.value = 'test_user_1_'
        self.browser.getControl(name='btnFind').click()

        # Select our test user
        self.browser.getControl(name='username').controls[0].selected = True
        self.browser.getControl(name='btn.find_roles').click()

        # Select previously added role
        r_controls = self.browser.getControl(name='collections:list').controls
        for r_ctl in r_controls:
            if r_ctl.optionValue == '/tc,':
                r_ctl.selected = True

        # We need to explicitly select the role to be removed here
        r_controls = self.browser.getControl(name='_tc:list').controls
        for r_ctl in r_controls:
            if r_ctl.optionValue == 'Client':
                r_ctl.selected = True

        self.browser.getControl(name='btn.revoke').click()
        self._check_controls(self.browser.contents)
        self.assertTrue('Roles removed: ' in
                        self.browser.contents)

        # Search for our test user
        search_term_ctl = self.browser.getControl(name='search_term')
        search_term_ctl.value = 'test_user_1_'
        self.browser.getControl(name='btnFind').click()

        # Select our test user
        self.browser.getControl(name='username').controls[0].selected = True
        self.browser.getControl(name='btn.find_roles').click()
        roles = self.browser.getControl(name='_tc:list').controls
        self.assertEqual(len(roles), 2)

        # self.browser.goBack(count=6)
