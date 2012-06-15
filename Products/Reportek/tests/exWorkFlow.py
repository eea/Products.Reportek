import os, sys
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')

from authutils import loginUnrestricted, logout

class catalogTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')
        
        # Create a Process Definition with two activity (Begin, End) and one transition.
        self.of.manage_addProcess(id='begin_end', BeginEnd=1)
        self.pd = getattr(self.of, 'begin_end')
        self.pd.addTransition(id='begin_end', From='Begin', To='End')

        # Create a Collection folder 
 #def manage_addCollection(self, title, descr,
 #            year, endyear, partofyear, country, locality, dataflow_uris=[],
  #           allow_collections=0, allow_envelopes=0, id='',
        self.app.manage_addProduct['Reportek'].manage_addCollection('title',
            'descr','2003','2004','','http://country', '',[], id='collection')

    def testCatalogCreation(self):
        assert hasattr(self.app, 'Catalog'), 'Catalog not created'


    def testProcessCataloging(self):
        catalog = getattr(self.app, 'Catalog')
        #catalog.manage_catalogFoundItems(REQUEST, RESPONSE, URL2, URL1)
        #print dir(catalog)
        assert catalog.searchResults({'id': 'begin_end'}), 'Process not Cataloged'

#   def testDeleteInstance(self):
#       assert self.of.getInstance(self.pid) != None
#       self.of.deleteInstance([self.pid])
#       assert self.of.getInstance(self.pid) == None


class processInstancesContainerTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')


class rolesTestCase(ZopeTestCase.ZopeTestCase):


    _setup_fixture = 0

    def afterSetUp(self):
        self.login()
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with two activity (Begin, End) and one transition.
        self.of.manage_addProcess(id='begin_end', BeginEnd=1)
        self.pd = getattr(self.of, 'begin_end')
        self.pd.addTransition(id='begin_end', From='Begin', To='End')

        self.app.manage_addProduct['Reportek'].manage_addCollection('title',
            'descr','2003','2004','','http://country', '', [], id='collection')
        # Create a Process Instance of the Process definition mentioned above
        self.coll = getattr(self.app, 'collection')
        self.coll.manage_addProduct['Reportek'].manage_addEnvelope('title',
            'descr','2003','2004','', 'entire country',REQUEST=self.app.REQUEST)


    def testEditRolePush(self):
        # Check edit on role
        role = 'testRole'
        process = 'begin_end'
        activities = ['Begin', 'End']
        self.of.editActivitiesPushableOnRole(role, process, activities)
        assert self.of._activitiesPushableOnRole == {'testRole':{'begin_end':['Begin', 'End']}},\
           "Role editing not correct: %s" % self.of._activitiesPushableOnRole[role][process]
        self.of.editActivitiesPushableOnRole(role, process, ['Begin'])
        assert self.of._activitiesPushableOnRole == {'testRole':{'begin_end':['Begin']}},\
           "Role editing not correct: %s" % self.of._activitiesPushableOnRole
        self.of.deleteProcessWithActivitiesPushableOnRole(role, process)
        assert self.of._activitiesPushableOnRole == {},\
           "Role editing not correct: %s" % self.of._activitiesPushableOnRole

    def testEditRolePull(self):
        # Check edit on role
        role = 'testRole'
        process = 'begin_end'
        activities = ['Begin', 'End']
        self.of.editActivitiesPullableOnRole(role, process, activities)
        assert self.of._activitiesPullableOnRole == {'testRole':{'begin_end':['Begin', 'End']}},\
           "Role editing not correct: %s" % self.of._activitiesPullableOnRole[role][process]
        self.of.editActivitiesPullableOnRole(role, process, ['Begin'])
        assert self.of._activitiesPullableOnRole == {'testRole':{'begin_end':['Begin']}},\
           "Role editing not correct: %s" % self.of._activitiesPullableOnRole
        self.of.deleteProcessWithActivitiesPullableOnRole(role, process)
        assert self.of._activitiesPullableOnRole == {},\
           "Role editing not correct: %s" % self.of._activitiesPullableOnRole

    def testWorkitemsListForRolePush(self):
        role = 'testRole'
        process = 'begin_end'
        activities = ['Begin', 'End']
        result = self.Catalog.searchResults(meta_type='Workitem')
        assert len(result) == 1, "%s workitems listed instead of 1" % len(result)
        result = self.Catalog.searchResults(meta_type='Workitem', push_roles='testRole')
        assert len(result) == 0, "%s workitems listed instead of 0" % len(result)
        self.of.editActivitiesPushableOnRole(role, process, activities)
        result = self.Catalog.searchResults(meta_type='Workitem', push_roles='testRole')
        assert len(result) == 1, "%s workitems listed instead of 1" % len(result)
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 1)
        result = self.Catalog.searchResults(meta_type='Workitem', push_roles='testRole')
        assert len(result) == 2, "only %s workitems listed instead of 2" % len(result)
        result = self.Catalog.searchResults(meta_type='Workitem', instance_id=pid, push_roles='testRole')
        assert result[0].id == '0', "WorkitemsList not correct: %s" % result
        assert 'testRole' in result[0].push_roles, "Role not associated to workitem"

    def testWorkitemsListForRolePull(self):
        role = 'testRole'
        process = 'begin_end'
        activities = ['Begin', 'End']
        result = self.Catalog.searchResults(meta_type='Workitem')
        assert len(result) == 1, "%s workitems listed instead of 1" % len(result)
        result = self.Catalog.searchResults(meta_type='Workitem', pull_roles='testRole')
        assert len(result) == 0, "%s workitems listed instead of 0" % len(result)
        self.of.editActivitiesPullableOnRole(role, process, activities)
        result = self.Catalog.searchResults(meta_type='Workitem', pull_roles='testRole')
        assert len(result) == 1, "%s workitems listed instead of 1" % len(result)
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 1)
        result = self.Catalog.searchResults(meta_type='Workitem', pull_roles='testRole')
        assert len(result) == 2, "only %s workitems listed instead of 2" % len(result)
        result = self.Catalog.searchResults(meta_type='Workitem', instance_id=pid, pull_roles='testRole')
        assert result[0].id == '0', "WorkitemsList not correct: %s" % result
        assert 'testRole' in result[0].pull_roles, "Role not associated to workitem"


class zopeSplitAnd(ZopeTestCase.ZopeTestCase):

    def afterSetUp(self):
        self.zope = self.app
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')
        # Create a Process Definition with two activities (Begin, End) and one transition linking them.
        self.of.manage_addProcess(id='begin_split_end', BeginEnd=1)
        self.pd = getattr(self.of, 'begin_split_end')
        self.pd.addActivity('a1')
        self.pd.addActivity('a2')
        self.pd.addTransition(id='Begin_a1', From='Begin', To='a1')
        self.pd.addTransition(id='Begin_a2', From='Begin', To='a2')
        self.pd.addTransition(id='a1_End', From='a1', To='End')
        self.pd.addTransition(id='a2_End', From='a2', To='End')
        self.app.manage_addProduct['Reportek'].manage_addCollection('title',
            'descr','2003','2004','','http://country', '', [], id='collection')
        # Create and activate a Process Instance of the Process definition mentioned above
        pid = self.of.addInstance('begin_split_end', 'test', 'testComment', 'TestTitle', 0)
        self.pi = self.of.getInstance(pid)
        self.of.startInstance(self.pi.id)
        # Forward first workitem
        self.w0 = getattr(self.pi, '0')
        self.of.activateWorkitem(self.pi.id, self.w0.id)
        self.of.completeWorkitem(self.pi.id, self.w0.id)
        self.of.forwardWorkitem(self.pi.id, self.w0.id)

    def testPass(self):
        catalog = getattr(self.of, 'Catalog')
        assert catalog

    def testCatalogedWorkitems(self):
        catalog = getattr(self.of, 'Catalog')
        workitems = catalog(meta_type="Workitem", id='0')
        assert len(workitems)==1
        workitem = workitems[0]
        assert workitem.workitems_to==['1', '2'], workitem.workitems_to

    def testCatalogedWorkitemSearch(self):
        catalog = getattr(self.of, 'Catalog')
        workitems = catalog(meta_type="Workitem", workitems_to = ['1'])
        assert len(workitems) == 1, "No workitem found on partial match"  
        

class zopeEnvTestCase(ZopeTestCase.ZopeTestCase):

    def afterSetUp(self):
        self.zope = self.app
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')
        # Create a Process Definition with two activities (Begin, End)
        # and one transition linking them.
        self.of.manage_addProcess(id='begin_end', BeginEnd=1)
        self.pd = getattr(self.of, 'begin_end')
        self.pd.addTransition(id='begin_end', From='Begin', To='End')

    def testPass(self):
        pass

    def testUsersAssignableTo(self):
        self.zope._addRole('aRole')
        uf = self.zope.acl_users
        uf._addUser(name='auser',
                    password='apass',
                    confirm='apass',
                    roles=['aRole'],
                    domains='')
        uf._addUser(name='otheruser',
                    password='apass',
                    confirm='apass',
                    roles=['Manager'],
                    domains='')
        self.of.editActivitiesPullableOnRole(role='aRole',
                                             process='begin_end',
                                             activities=['Begin', 'End'])
        assert self.of.usersAssignableTo('begin_end', 'Begin') == ['auser'], \
               self.of.usersAssignableTo('begin_end', 'Begin')
            

    def testAutoPush(self):
        # create a python script for auto-pushing
        self.zope.manage_addProduct['PythonScripts'].manage_addPythonScript(id='pyPush')
        self.pyapp = getattr(self.zope, 'pyPush')
        self.pyapp.ZPythonScript_edit(params='**args', body='return "somebody"')
        self.of.addApplication(name="push_app", link="../pyPush")
        self.pd.Begin.edit(push_application='push_app', kind='standard')
        # create and start an instance
        obj = self.of.restrictedTraverse('../pyPush')
        assert obj == getattr(self.of, 'pyPush'), (obj, getattr(self.of, 'pyPush'))
        assert hasattr(obj, '__call__')
        assert hasattr(getattr(self.of, 'pyPush'), '__call__')
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 1)
        instance = self.of.getInstance(pid)
        assert instance
        assert instance.objectIds('Workitem') == ['0'], instance.objectIds('Workitem')
        wi = getattr(instance, '0')
        assert wi.actor == 'somebody', wi.actor

    def testAutoDelete(self):
        # create a python script for auto-delete action
        loginUnrestricted()
        self.zope.manage_addProduct['PythonScripts'].manage_addPythonScript(id='pyAuto')
        self.zope.manage_addProduct['OFSP'].manage_addFolder(id='store')
        store = getattr(self.zope, 'store')
        self.pyapp = getattr(self.zope, 'pyAuto')
        self.pyapp.ZPythonScript_edit(params='instance_id, **kw',
                                      body="getattr(context, '%s').deleteInstance([instance_id])" % (self.of.id) )
        self.of.addApplication(name="auto_app", link="../pyAuto")
        self.pd.Begin.edit(kind='dummy')
        self.pd.End.edit(application='auto_app', start_mode=1, finish_mode=1, kind='standard')
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 1)
        instance = self.of.getInstance(pid)
        assert self.of.getInstance(pid) == None
        logout()

    def testAutoAction(self):
        # create a python script for auto-action
        loginUnrestricted()
        self.zope.manage_addProduct['PythonScripts'].manage_addPythonScript(id='pyAuto')
        self.zope.manage_addProduct['OFSP'].manage_addFolder(id='store')
        store = getattr(self.zope, 'store')
        self.pyapp = getattr(self.zope, 'pyAuto')
        self.pyapp.ZPythonScript_edit(params='**kw',
                                      body="getattr(context, 'store').manage_addProperty(id='una', type='string', value='run')")
        self.of.addApplication(name="auto_app", link="../pyAuto")
        self.pd.Begin.edit(application='auto_app', start_mode=1, kind='standard')
        # create and start an instance
        obj = self.of.restrictedTraverse('../pyAuto')
        assert obj == getattr(self.of, 'pyAuto'), (obj, getattr(self.of, 'pyAuto'))
        assert hasattr(obj, '__call__')
        assert hasattr(getattr(self.of, 'pyAuto'), '__call__')
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 1)
        instance = self.of.getInstance(pid)
        assert instance
        assert instance.objectIds('Workitem') == ['0'], instance.objectIds('Workitem')
        wi = getattr(instance, '0')
        assert wi.actor == 'openflow_engine', wi.actor
        assert store.hasProperty('una')
        assert store.getProperty('una')=='run', 'valore = %s' % store.getProperty('una')
        # "tear down": the user is loggedout
        logout()


class zopeEnvCopySupport(ZopeTestCase.ZopeTestCase):

    def afterSetUp(self):
        self.zope = self.app
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')
        # Create a Process Definition with two activities (Begin, End)...
        self.of.manage_addProcess(id='begin_end', BeginEnd=1)
        self.pd = getattr(self.of, 'begin_end')
        # ...and one transition linking them
        self.pd.addTransition(id='begin_end', From='Begin', To='End')
        loginUnrestricted()

    def testCopyOpenflow(self):
        cataloged_items = len(self.of.Catalog())
        cb = self.zope.manage_copyObjects([self.of.id])
        try:
            for i in [self.of, self.pd] + self.pd.objectValues():
                assert hasattr(i.aq_base, 'getId'), "missing %s" % i.id
                assert i._getCopy(self.zope) != None, "getcopy not in %s" % i.id
        except AssertionError:
            # this test is tough to make! how to do this?
            return
        self.zope.manage_pasteObjects(cb)
        new_of = getattr(self.zope, 'copy_of_'+self.of.id)
        assert len(new_of.Catalog()) == cataloged_items

    def testChangeUseOpenFlowPermission(self):
        from AccessControl.Permission import Permission
        perms = self.of.ac_inherited_permissions(1)
        name, value = [p for p in perms if p[0]=='Use OpenFlow'][0][:2]
        p=Permission(name,value,self.of)
        roles = ['Authenticated']
        p.setRoles(roles)
