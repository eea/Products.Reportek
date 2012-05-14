import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')

from Products.Reportek.process import process
from Products.Reportek.activity import activity
from Products.Reportek.transition import transition


class processDefinitionCreationTestCase(ZopeTestCase.ZopeTestCase):


    _setup_fixture = 0

    def afterSetUp(self):

        # Create a Process Definition with two activity (Begin, End) and one transition
        self.pd = process('begin_end', 'Testprocess','', 0, 0, 0, 0 )
    
    def testProcessInstanceCreation(self):
        """ Check a simple process definition creation """
        self.pd.addActivity('Begin')
        assert hasattr(self.pd, 'Begin'), 'Begin activity not created'
        self.pd.addActivity('Act')
        self.pd.addActivity('End')
        self.pd.manage_changeProperties(begin='Begin')
        assert self.pd.begin == 'Begin', 'Wrong BEGIN activity settings %s' % self.pd.getBegin()
        self.pd.manage_changeProperties(end='End')
        assert self.pd.end == 'End', 'Wrong END activity settings'
        self.pd.addTransition(id='begin_act', From='Begin', To='Act')
        assert hasattr(self.pd, 'begin_act'), 'begin_act transition not created'
        self.pd.addTransition(id='act_end', From='Act', To='End')

def test_suite():
    import unittest
    suite = unittest.makeSuite(processDefinitionCreationTestCase, 'test')
    return suite
    
if __name__ == '__main__':
    framework()
