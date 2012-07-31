import unittest
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
from configurereportek import ConfigureReportek
from Products.Reportek.constants import CONVERTERS_ID
from Products.Reportek.exceptions import CannotPickProcess

class ExceptionsTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    def afterSetUp(self):
        self.createStandardDependencies()
        self.createStandardCollection()
        self.wf = self.app.WorkflowEngine

    def test_CannotPickProcess_exception(self):
        self.wf.manage_addProcess('process1', BeginEnd=1)
        self.wf.setProcessMappings('process1', '', '',
                                   ['http://rod.eionet.eu.int/obligations/8'],
                                   ['http://rod.eionet.eu.int/spatial/2'])
        self.wf.manage_addProcess('process2', BeginEnd=1)
        self.wf.setProcessMappings('process2', '', '',
                                   ['http://rod.eionet.eu.int/obligations/8'],
                                   ['http://rod.eionet.eu.int/spatial/2'])
        err_code, result = self.wf.findProcess(['http://rod.eionet.eu.int/obligations/9'],
                                  'http://rod.eionet.eu.int/spatial/2')
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        message = 'More than one process associated with this envelope'
        with self.assertRaisesRegexp(CannotPickProcess, message) as raised:
            col.manage_addProduct['Reportek'].manage_addEnvelope('', '', '2003', '2004', '',
             'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
