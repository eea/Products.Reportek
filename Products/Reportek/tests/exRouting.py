import os, sys
from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')

class routingSimpleTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with two activity (Begin, End) and one transition.
        self.of.manage_addProcess(id='begin_end', BeginEnd=1)
        self.pd = getattr(self.of, 'begin_end')
        self.pd.addTransition(id='begin_end', From='Begin', To='End')

        # Create a Process Instance of the Process definition mentioned above
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 0)
        self.pi = self.of.getInstance(pid)

    def testGetInstance(self):
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 0)
        self.pi = self.of.getInstance(pid)

    def testDummyFlow(self):
        getattr(self.pd, 'Begin').edit(kind='dummy')
        getattr(self.pd, 'End').edit(kind='dummy')
        self.of.startInstance(self.pi.id)
        assert len(self.pi.objectIds('Workitem')) == 2, self.pi.objectIds('Workitem')
        assert self.pi.status == 'complete', self.pi.status

    def testCreation(self):
        """ Check for the correct creation of the test objects """
        assert self.of, 'openflow folder not created'
        assert self.pd, 'process definition not created'
        assert hasattr(self.pd, 'Begin'), 'Begin activity not created'
        assert hasattr(self.pd, 'End'), 'End activity not created'
        assert hasattr(self.pd, 'begin_end'), 'begin_end transition not created'
        assert self.pi, 'process instance not created'


    def testActivateInstance(self):
        """ Check the Process Instance activation """
        assert self.pi.status == 'initiated', 'process instance starting status not correct'
        self.of.startInstance(self.pi.id)
        assert self.pi.status == 'running', 'process instance activation not correct'


    def testAssignUnassignedWorkitem(self):
        """ Check the workitem creation and activation """
        self.of.startInstance(self.pi.id)
        self.w = getattr(self.pi, '0')
        assert self.w.status == 'inactive', 'workitem creation not correct'
        self.of.assignWorkitem(self.pi.id, self.w.id, 'testActor')
        assert self.w.actor == 'testActor', 'workitem assignement not correct'
        self.of.unassignWorkitem(self.pi.id, self.w.id)
        assert self.w.actor == '', 'workitem unassignement not correct'


    def testActivateWorkitem(self):
        """ Check the workitem creation and activation """
        self.of.startInstance(self.pi.id)
        self.w = getattr(self.pi, '0')
        assert self.w.status == 'inactive', 'workitem creation not correct'
        self.of.activateWorkitem(self.pi.id, self.w.id)
        assert self.w.status == 'active', 'workitem activation not correct'


    def testInactivateWorkitem(self):
        """ Check the workitem inactivation """
        self.of.startInstance(self.pi.id)
        self.w = getattr(self.pi, '0')
        assert self.w.status == 'inactive', 'workitem creation not correct'
        self.of.activateWorkitem(self.pi.id, self.w.id)
        assert self.w.status == 'active', 'workitem activation not correct'
        self.of.inactivateWorkitem(self.pi.id, self.w.id)
        assert self.w.status == 'inactive', 'workitem inactivation not correct'


    def testSuspendWorkitem(self):
        """ Check the workitem suspended """
        self.of.startInstance(self.pi.id)
        self.w = getattr(self.pi, '0')
        assert self.w.status == 'inactive', 'workitem creation not correct'
        self.of.suspendWorkitem(self.pi.id, self.w.id)
        assert self.w.status == 'suspended', 'workitem suspension not correct'


    def testResumeWorkitem(self):
        """ Check the workitem resume """
        self.of.startInstance(self.pi.id)
        self.w = getattr(self.pi, '0')
        assert self.w.status == 'inactive', 'workitem creation not correct'
        self.of.suspendWorkitem(self.pi.id, self.w.id)
        assert self.w.status == 'suspended', 'workitem suspension not correct'
        self.of.resumeWorkitem(self.pi.id, self.w.id)
        assert self.w.status == 'inactive', 'workitem inactivation not correct'


    def testCompleteWorkitem(self):
        """ Check the workitem completion """
        self.of.startInstance(self.pi.id)
        self.w = getattr(self.pi, '0')
        self.of.activateWorkitem(self.pi.id, self.w.id)
        self.of.completeWorkitem(self.pi.id, self.w.id)
        assert self.w.status == 'complete', 'workitem completion not correct'


    def testForwardWorkitem(self):
        """ Check the workitem forwarding """
        self.of.startInstance(self.pi.id)
        self.w0 = getattr(self.pi, '0')
        self.of.activateWorkitem(self.pi.id, self.w0.id)
        self.of.completeWorkitem(self.pi.id, self.w0.id)
        self.of.forwardWorkitem(self.pi.id, self.w0.id)
        assert hasattr(self.pi, '1'), 'new workitem not created'
        assert getattr(self.pi, '1').status == 'inactive', 'new workitem status not correct'


    def testCompleteInstance(self):
        """ Check the process instance completion """
        self.of.startInstance(self.pi.id)
        self.w0 = getattr(self.pi, '0')
        self.of.activateWorkitem(self.pi.id, self.w0.id)
        self.of.completeWorkitem(self.pi.id, self.w0.id)
        self.of.forwardWorkitem(self.pi.id, self.w0.id)
        self.w1 = getattr(self.pi, '1')
        self.of.activateWorkitem(self.pi.id, self.w1.id)
        self.of.completeWorkitem(self.pi.id, self.w1.id)
        assert self.w0.status == 'complete', 'first workitem completion not correct'
        assert self.w1.status == 'complete', 'last workitem completion not correct'
        assert self.pi.status == 'complete', 'process instance completion not correct'


class routingAndSplitTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):

        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with two activity (Begin, End) and one transition.
        self.of.manage_addProcess(id='begin_end', BeginEnd=1)
        self.pd = getattr(self.of, 'begin_end')
        self.pd.addActivity('a1')
        self.pd.addActivity('a2')
        self.pd.addTransition(id='Begin_a1', From='Begin', To='a1')
        self.pd.addTransition(id='Begin_a2', From='Begin', To='a2')
        self.pd.addTransition(id='a1_End', From='a1', To='End')
        self.pd.addTransition(id='a2_End', From='a2', To='End')

        # Create and activate a Process Instance of the Process definition mentioned above
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 0)
        self.pi = self.of.getInstance(pid)
        self.of.startInstance(self.pi.id)

        # Forward first workitem
        self.w0 = getattr(self.pi, '0')
        self.of.activateWorkitem(self.pi.id, self.w0.id)
        self.of.completeWorkitem(self.pi.id, self.w0.id)
        self.of.forwardWorkitem(self.pi.id, self.w0.id)

    def testPass(self):
        """ assertions on setup """
        destionations = self.of.getDestinations(self.pi.id, '0')
        assert len(destionations)==2, destionations

    def testWorkitemSplit(self):
        """ Check the workitem split """
        assert hasattr(self.pi, '1'), 'workitem 1 not created'
        assert hasattr(self.pi, '2'), 'workitem 2 not created'
        wi1 = getattr(self.pi, '1')
        wi2 = getattr(self.pi, '2')
        assert wi1.status == 'inactive', 'workitem 1 status not correct'
        assert wi2.status == 'inactive', 'workitem 2 status not correct'
        assert wi1.workitems_from == ['0'], 'Workitem from 1: %s' % wi1.workitems_from
        assert wi2.workitems_from == ['0'], 'Workitem from 2: %s' % wi2.workitems_from


    def testWorkitemJoin(self):
        """ Check the workitem join """
        self.w1 = getattr(self.pi, '1')
        self.of.activateWorkitem(self.pi.id, self.w1.id)
        self.of.completeWorkitem(self.pi.id, self.w1.id)
        self.of.forwardWorkitem(self.pi.id, self.w1.id)
        assert hasattr(self.pi, '3'), 'workitem 3 not created'
        assert getattr(self.pi, '3').status=='blocked', 'workitem 3 is not blocked'
        assert getattr(self.pi, '3').blocked==1, \
               'workitem 3 is not correctly blocked %s' % getattr(self.pi, '3').blocked
        self.w2 = getattr(self.pi, '2')
        self.of.activateWorkitem(self.pi.id, self.w2.id)
        self.of.completeWorkitem(self.pi.id, self.w2.id)
        self.of.forwardWorkitem(self.pi.id, self.w2.id)
        assert len(self.pi.objectIds())==4, [(wi.id, wi.workitems_from, wi.workitems_to, wi.status) for wi in self.pi.objectValues()]
        assert getattr(self.pi, '3').blocked==0, \
               'workitem 3 is still blocked %s' % getattr(self.pi, '3').blocked
        assert getattr(self.pi, '3').status == 'inactive', 'workitem 3 is not inactive'


class routingXOrSplitTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):

        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with two activity (Begin, End) and one transition.
        self.of.manage_addProcess(id='xor_split', BeginEnd=1)
        self.pd = getattr(self.of, 'xor_split')
        begin = getattr(self.pd, 'Begin')
        begin.edit(split_mode='xor')
        end = getattr(self.pd, 'End')
        end.edit(join_mode='xor')
        self.pd.addActivity('a1')
        self.pd.addActivity('a2')
        self.pd.addTransition(id='Begin_a1', From='Begin', To='a1', condition='python:1')
        self.pd.addTransition(id='Begin_a2', From='Begin', To='a2', condition='python:0')
        self.pd.addTransition(id='a1_End', From='a1', To='End')
        self.pd.addTransition(id='a2_End', From='a2', To='End')

        # Create and activate a Process Instance of the Process definition mentioned above
        pid = self.of.addInstance('xor_split', 'test', 'testComment', 'TestTitle', 0)
        self.pi = self.of.getInstance(pid)
        self.of.startInstance(self.pi.id)

        # Forward first workitem
        self.w0 = getattr(self.pi, '0')
        self.of.activateWorkitem(self.pi.id, self.w0.id)
        self.of.completeWorkitem(self.pi.id, self.w0.id)
        self.of.forwardWorkitem(self.pi.id, self.w0.id)


    def testConditionTALExpressions(self):
        self.pd.Begin.manage_addProperty('flag', 1, 'int')
        self.pd.Begin_a1.edit(From='Begin', To='a1', condition='activity/flag', description='')
        pid = self.of.addInstance('xor_split', 'test', 'testComment', 'TestTitle', 1)
        self.of.activateWorkitem(pid, '0')
        self.of.completeWorkitem(pid, '0')
        self.of.forwardWorkitem(pid, '0')
        p = self.of.getInstance(pid)
        assert len(p.objectIds('Workitem'))==2
        assert getattr(p, '1').activity_id == 'a1'

 
    def testWorkitemSplit(self):
        """ Check the workitem split """
        assert hasattr(self.pi, '1'), 'workitem 1 not created'
        assert getattr(self.pi, '1').activity_id == 'a1', 'workitem 1 activity not correct'


    def testWorkitemJoin(self):
        """ Check the workitem join """
        self.w1 = getattr(self.pi, '1')
        self.of.activateWorkitem(self.pi.id, self.w1.id)
        self.of.completeWorkitem(self.pi.id, self.w1.id)
        self.of.forwardWorkitem(self.pi.id, self.w1.id)
        assert hasattr(self.pi, '2'), 'workitem 2 not created'
        assert getattr(self.pi, '2').activity_id == 'End', 'activity of workitem 2 is not correct'

        
class routingExceptionHandlingTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with two activity (Begin, End) and one transition.
        self.of.manage_addProcess(id='exception_handling', BeginEnd=1)
        self.pd = getattr(self.of, 'exception_handling')
        self.pd.addTransition(id='exception_handling', From='Begin', To='End')

        # Create a Process Instance of the Process definition mentioned above
        pid = self.of.addInstance('exception_handling', 'test', 'testComment', 'TestTitle', 1)
        self.pi = self.of.getInstance(pid)
    

    def testFallout1(self):
        self.of.falloutWorkitem(self.pi.id, '0')
        assert getattr(self.pi, '0').status == 'fallout', 'first workitem status not correct' 
        self.of.changeWorkitem(self.pi.id, '0', push_roles=['somerole'])
        assert getattr(self.pi, '0').push_roles == ['somerole'], \
               'workitem not changed %s' % getattr(self.pi, '0').push_roles
        self.of.fallinWorkitem(self.pi.id, '0', 'exception_handling', 'Begin')
        assert getattr(self.pi, '0').activity_id == 'Begin' , \
               'workitem not in correct activity %s' % getattr(self.pi, '0').activity_id
        self.of.endFallinWorkitem(self.pi.id, '0')
        assert getattr(self.pi, '0').status != 'fallout', 'first workitem status not correct'

    def testFallout2(self):
        wi0 = getattr(self.pi, '0')
        self.of.falloutWorkitem(self.pi.id, '0')
        assert getattr(self.pi, '0').status == 'fallout', 'first workitem status not correct' 
        self.of.changeWorkitem(self.pi.id, '0', status='active')
        assert getattr(self.pi, '0').status == 'active', 'first workitem status not correct'
        self.of.endFallinWorkitem(self.pi.id, '0')
        assert len(wi0.activation_log) == 1
        assert wi0.activation_log[-1]['end'] == None


class routingAutoAppTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with two activity (Begin, End) and one transition.
        self.of.manage_addProcess(id='begin_end', BeginEnd=1)
        self.pd = getattr(self.of, 'begin_end')
        self.pd.addTransition(id='begin_end', From='Begin', To='End')
        begin = getattr(self.pd, 'Begin')
        begin.edit(start_mode=1, finish_mode=1)
        # Create a Process Instance of the Process definition mentioned above
        pid = self.of.addInstance('begin_end', 'test', 'testComment', 'TestTitle', 1)
        self.pi = self.of.getInstance(pid)

    
    def testCompleteInstance(self):
        """ Check the process instance completion """
        assert getattr(self.pd, 'Begin').isAutoStart() == 1, 'activity not AutoStart'
        assert hasattr(self.pi, '0'), 'first workitem not created'
        assert getattr(self.pi, '0').status == 'complete', 'first workitem not completed'
        self.w1 = getattr(self.pi, '1')
        self.of.activateWorkitem(self.pi.id, self.w1.id)
        self.of.completeWorkitem(self.pi.id, self.w1.id)
        assert self.w1.status == 'complete', 'last workitem completion not correct'
        assert self.pi.status == 'complete', 'process instance completion not correct'


class routingSubflowTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with a subflow activity.
        self.of.manage_addProcess(id='main', BeginEnd=1)
        self.main_pd = getattr(self.of, 'main')
        self.main_pd.addActivity('sub', subflow='test_subflow', kind='subflow')
        self.main_pd.addTransition(id='Begin_sub', From='Begin', To='sub')
        self.main_pd.addTransition(id='sub_End', From='sub', To='End')
        begin = getattr(self.main_pd, 'Begin')
        begin.edit(kind='dummy')

        # Create a Process Definition "subflow" that will act as a subflow.
        self.of.manage_addProcess(id='test_subflow', BeginEnd=1)
        self.sub_pd = getattr(self.of, 'test_subflow')
        self.sub_pd.addTransition(id='Begin_End', From='Begin', To='End')
        #end = getattr(self.sub_pd, 'End')
        #end.edit(start_mode=1, finish_mode=1)

        # Create a Process Instance of "main"
        pid = self.of.addInstance('main', 'test', 'testComment', 'TestTitle', 1)
        self.pi = self.of.getInstance(pid)
    

    def testSubflowWorkitemsCreation(self):
        """ Check the workitems creation """
        assert hasattr(self.pi, '1'), 'workitem 1 not created'
        assert hasattr(self.pi, '2'), [(wi.activity_id, wi.id) for wi in self.pi.objectValues()]
        'workitem 2 not created'
        assert getattr(self.pi, '2').activity_id == 'Begin' , 'workitem 2 activity not correct'
        assert getattr(self.pi, '2').process_id == 'test_subflow' , 'workitem 2 process not correct'
        self.w = getattr(self.pi, '2')
        self.of.activateWorkitem(self.pi.id, self.w.id)
        self.of.completeWorkitem(self.pi.id, self.w.id)
        self.of.forwardWorkitem(self.pi.id, self.w.id)
        assert getattr(self.pi, '3').activity_id == 'End' , 'workitem 3 activity not correct'
        assert getattr(self.pi, '3').process_id == 'test_subflow' , 'workitem 3 process not correct'
        

    def testCompleteSubflow(self):
        """ Check the subflow completion """
        self.w = getattr(self.pi, '2')
        self.of.activateWorkitem(self.pi.id, self.w.id)
        self.of.completeWorkitem(self.pi.id, self.w.id)
        self.of.forwardWorkitem(self.pi.id, self.w.id)
        assert hasattr(self.pi, '3'), 'workitem 3  not created'
        assert self.of.getSubflowWorkitem(self.pi.id, '3') == '1', 'subflow workitem not correct'
        self.of.activateWorkitem(self.pi.id, '3')
        self.of.completeWorkitem(self.pi.id, '3')
        assert getattr(self.pi, '1').status == 'complete', 'subflow workitem status not correct'
        assert hasattr(self.pi, '4'), 'workitem 4 not created'


class routingDummySubflowTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with a subflow activity.
        self.of.manage_addProcess(id='main', BeginEnd=1)
        self.main_pd = getattr(self.of, 'main')
        self.main_pd.addActivity('sub', subflow='test_subflow', kind='subflow')
        self.main_pd.addTransition(id='Begin_sub', From='Begin', To='sub')
        self.main_pd.addTransition(id='sub_End', From='sub', To='End')
        begin = getattr(self.main_pd, 'Begin')
        begin.edit(kind='dummy')
        end = getattr(self.main_pd, 'End')
        end.edit(kind='dummy')

        # Create a Process Definition "subflow" that will act as a subflow.
        self.of.manage_addProcess(id='test_subflow', BeginEnd=1)
        self.sub_pd = getattr(self.of, 'test_subflow')
        self.sub_pd.addTransition(id='Begin_End', From='Begin', To='End')
        begin = getattr(self.sub_pd, 'Begin')
        begin.edit(kind='dummy')
        end = getattr(self.sub_pd, 'End')
        end.edit(kind='dummy')

        # Create a Process Instance of "main"
        pid = self.of.addInstance('main', 'test', 'testComment', 'TestTitle', 1)
        self.pi = self.of.getInstance(pid)

    def testComplete(self):
        assert self.pi.status == 'complete', self.pi.status
