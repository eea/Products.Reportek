import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
from AccessControl import getSecurityManager
from configurereportek import ConfigureReportek
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')

class exceptionsTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

#   _setup_fixture = 0

    def afterSetUp(self):
	self.createStandardDependencies()
        # Assume the workflow engine was created automatically
        self.of = getattr(self.app, 'WorkflowEngine')

        # Create a Process Definition with two activity (Begin, End) and one transition.
        self.of.manage_addProcess(id='TestProcess', BeginEnd=1)
        self.pd = getattr(self.of, 'TestProcess')
        self.pd.addTransition(id='Begin_End', From='Begin', To='End')
        self.pd.Begin.edit(kind='dummy')
        self.pd.End.edit(kind='dummy')

        # Create a Process Instance of the Process definition mentioned above
	self.createStandardCollection()
        col = self.app.collection
        #  title, descr, year, endyear, partofyear, locality,
        # REQUEST=None, previous_delivery=''
        self.login()
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        col.manage_addProduct['Reportek'].manage_addEnvelope('', '', '2003', '2004', '',
         'http://rod.eionet.eu.int/spatial/2', REQUEST=None, previous_delivery='')
        for e in col.objectValues():
            if e.id[:3] == "env":
                self.env = e
		break


    def testMissingTransition(self):
        self.pd.manage_delObjects(['Begin_End'])
        self.env.startInstance()
        assert len(self.env.objectIds())==1, self.env.objectIds()
        assert getattr(self.env, '0').activity_id == 'Begin'
        assert getattr(self.env, '0').status == 'fallout'

    def testMissingAction(self):
        self.pd.manage_delObjects(['End'])
        self.env.startInstance()
        assert len(self.env.objectIds())==1, self.env.objectIds()
        assert getattr(self.env, '0').activity_id == 'Begin'
        assert getattr(self.env, '0').status == 'fallout'

    def testTooManyXor(self):
        self.pd.addTransition(id='Begin_End2', From='Begin', To='End')
        self.pd.Begin.edit(split_mode='xor')
        self.env.startInstance()
        assert len(self.env.objectIds())==1, self.env.objectIds()
        assert getattr(self.env, '0').activity_id == 'Begin'
        assert getattr(self.env, '0').status == 'fallout'

    def testDeleteActivity(self):
        self.pd.Begin.edit(kind='standard')
        self.env.startInstance()
        self.pd.manage_delObjects(['Begin'])
        assert getattr(self.env, '0').activity_id == 'Begin'
        assert getattr(self.env, '0').status == 'fallout', getattr(self.env, '0').status

def test_suite():
    import unittest
    suite = unittest.makeSuite(exceptionsTestCase, 'test')
    return suite


if __name__ == '__main__':
    framework()

