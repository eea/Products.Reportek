# Those are old tests written by moregale that were renamed to never be executetd
# for some while; some other tests regarding workflow have been written.
# in the mean time, none of the test, not even the runnable ones, have been run
# thus most of them remained more or less outdated
# What is left here are the tests that have been easily brought back to life
# One can see the rest of them using version control history
import unittest
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from common import BaseTest, ConfigureReportek

from authutils import loginUnrestricted


class rolesTestCase(BaseTest, ConfigureReportek):

    _setup_fixture = 0

    def afterSetUp(self):
        super(rolesTestCase, self).afterSetUp()
        self.createStandardCatalog()
        self.createStandardDependencies()
        self.createStandardCollection()
        #self.createStandardEnvelope()
        #self.login()

        #self.app.manage_addProduct['Reportek'].manage_addCollection('title',
        #    'descr','2003','2004','','http://country', '', [], id='collection')
        # Create a Process Instance of the Process definition mentioned above
        self.coll = getattr(self.app, 'collection')
        self.coll.manage_addProduct['Reportek'].manage_addEnvelope('title',
            'descr','2003','2004', 'Whole Year', 'entire country',REQUEST=self.app.REQUEST)
        self.of = getattr(self.app, 'WorkflowEngine')

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
        result = self.app.Catalog.searchResults(meta_type='Workitem')
        assert len(result) == 1, "%s workitems listed instead of 1" % len(result)
        result = [ o.getObject() for o in result if role in o.getObject().push_roles ]
        assert len(result) == 0, "%s workitems listed instead of 0" % len(result)
        self.of.editActivitiesPushableOnRole(role, process, activities)
        result = self.app.Catalog.searchResults(meta_type='Workitem')
        result = [ o.getObject() for o in result if role in o.getObject().push_roles ]
        assert len(result) == 1, "%s workitems listed instead of 1" % len(result)

    def testWorkitemsListForRolePull(self):
        role = 'testRole'
        process = 'begin_end'
        activities = ['Begin', 'End']
        result = self.app.Catalog.searchResults(meta_type='Workitem')
        assert len(result) == 1, "%s workitems listed instead of 1" % len(result)
        result = [ o.getObject() for o in result if role in o.getObject().pull_roles ]
        assert len(result) == 0, "%s workitems listed instead of 0" % len(result)
        self.of.editActivitiesPullableOnRole(role, process, activities)
        result = self.app.Catalog.searchResults(meta_type='Workitem')
        result = [ o.getObject() for o in result if role in o.getObject().pull_roles ]
        assert len(result) == 1, "%s workitems listed instead of 1" % len(result)


class zopeEnvTestCase(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(zopeEnvTestCase, self).afterSetUp()
        self.createStandardCatalog()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.coll = getattr(self.app, 'collection')
        self.coll.manage_addProduct['Reportek'].manage_addEnvelope('title',
            'descr','2003','2004', 'Whole Year', 'entire country',REQUEST=self.app.REQUEST)
        self.of = getattr(self.app, 'WorkflowEngine')
        self.pd = getattr(self.of, 'begin_end')

    def testUsersAssignableTo(self):
        self.app._addRole('aRole')
        uf = self.app.acl_users
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


class zopeEnvCopySupport(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(zopeEnvCopySupport, self).afterSetUp()
        self.createStandardCatalog()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.coll = getattr(self.app, 'collection')
        self.coll.manage_addProduct['Reportek'].manage_addEnvelope('title',
            'descr','2003','2004', 'Whole Year', 'entire country',REQUEST=self.app.REQUEST)
        self.of = getattr(self.app, 'WorkflowEngine')
        self.pd = getattr(self.of, 'begin_end')
        loginUnrestricted()

    # TODO BaseTest is supposed to be used in unit tests, it uses Mock objects
    # that are not pickable
    # we need some mechanism to implement functional, vertical tests, such the one below
    @unittest.expectedFailure
    def testCopyOpenflow(self):
        cataloged_items = len(self.of.Catalog())
        cb = self.app.manage_copyObjects([self.of.id])
        try:
            for i in [self.of, self.pd] + self.pd.objectValues():
                assert hasattr(i.aq_base, 'getId'), "missing %s" % i.id
                assert i._getCopy(self.app) != None, "getcopy not in %s" % i.id
        except AssertionError:
            # this test is tough to make! how to do this?
            return
        self.app.manage_pasteObjects(cb)
        new_of = getattr(self.app, 'copy_of_'+self.of.id)
        assert len(new_of.Catalog()) == cataloged_items

    def testChangeUseOpenFlowPermission(self):
        from AccessControl.Permission import Permission
        perms = self.of.ac_inherited_permissions(1)
        name, value = [p for p in perms if p[0]=='Use OpenFlow'][0][:2]
        p=Permission(name,value,self.of)
        roles = ['Authenticated']
        p.setRoles(roles)
