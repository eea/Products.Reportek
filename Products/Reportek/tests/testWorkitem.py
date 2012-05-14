import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')
from Products.Reportek.workitem import workitem

class WorkitemTestCase(ZopeTestCase.ZopeTestCase):

    _setup_fixture = 0

    def afterSetUp(self):
        blocked = 0
        self.w = workitem('id', 'instance_id', 'process_id', blocked)
        
    
    def testCreation(self):
        """ Check for the correct creation of a workitem """
        assert self.w, 'workitem not created'


    def testUnblock(self):
        """ Check unblock attribute consistency with unusual values """
        self.w.unblock()
        assert self.w.blocked >= 0, 'uncorrect values for blocked attribute'


    def testIsActive(self):
        """ we have big problems here """
        pass


    def testEdit(self):
        """ Check the names of the set methods """
        assert self.w.edit(instance_id = '',
                           activity_id = '',
                           blocked = 0,
                           priority = 1,
                           workitems_from = [],
                           workitems_to = [],
                           status = 'active',
                           actor = 'openflow_test',
                           graph_level = 0) == None, 'incorrect edit'

def test_suite():
    import unittest
    suite = unittest.makeSuite(WorkitemTestCase, 'test')
    return suite

if __name__ == '__main__':
    framework()
