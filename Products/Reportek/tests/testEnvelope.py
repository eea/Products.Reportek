import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
from AccessControl import getSecurityManager
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from configurereportek import ConfigureReportek


class EnvelopeTestCase(ZopeTestCase.ZopeTestCase, ConfigureReportek):

    def afterSetUp(self):
        self.createStandardDependencies()
	self.createStandardCollection()
        self.assertTrue(hasattr(self.app, 'collection'),'Collection did not get created')
        self.assertNotEqual(self.app.collection, None)

    def test_addEnvelope(self):
        """ To create an envelope the following is needed:
            1) self.REQUEST.AUTHENTICATED_USER.getUserName() must return something
            2) There must exist a default workflow
        """
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        col.manage_addProduct['Reportek'].manage_addEnvelope('', '', '2003', '2004', '',
         'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
        self.envelope = None
        for env in col.objectValues('Report Envelope'):
            self.envelope = env
            break
        self.assertNotEqual(self.envelope, None)

    def helpCreateEnvelope(self,startYear, endYear, duration):
        """ To create an envelope the following is needed:
            1) self.REQUEST.AUTHENTICATED_USER.getUserName() must return something
            2) There must exist a default workflow
        """
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        col.manage_addProduct['Reportek'].manage_addEnvelope('', '', startYear, endYear, duration,
         'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')
        self.envelope = None
        for env in col.objectValues('Report Envelope'):
            self.envelope = env
            break
        self.assertNotEqual(self.envelope, None)

    def test_endDateMultipleYears(self):
        self.helpCreateEnvelope('2003', '2004', '')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2003-01-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2004-12-31')

    def test_endDateFirstHalf(self):
        self.helpCreateEnvelope('2003', '', 'First Half')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2003-01-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2003-06-30')

    def test_endDateFirstQuarter(self):
        self.helpCreateEnvelope('2009', '', 'First Quarter')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2009-01-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2009-03-31')

    def test_endDateThirdQuarter(self):
        self.helpCreateEnvelope('2009', '', 'Third Quarter')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2009-07-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2009-09-30')

    def test_endDateMultipleYearsQuarter(self):
        self.helpCreateEnvelope('2004', '2009', 'First Quarter')
        s = self.envelope.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'),'2004-01-01')
        r = self.envelope.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'),'2009-12-31')
        self.envelope.release_envelope()
        rdf = self.envelope.rdf(self.app.REQUEST)
        assert rdf.find('startOfPeriod') > -1
        assert rdf.find('endOfPeriod') > -1

    def test_DateNoDates(self):
        self.helpCreateEnvelope('', '', 'First Quarter')
        s = self.envelope.getStartDate()
        self.assertEqual(s, None)
        r = self.envelope.getEndDate()
        self.assertEqual(r, None)
        self.envelope.release_envelope()
        rdf = self.envelope.rdf(self.app.REQUEST)
        self.assertEqual(-1,rdf.find('startOfPeriod'))

    def test_workitem(self):
        """ Test the first workitem """
        self.test_addEnvelope()
        # Check that exactly on workitem was created
        assert len(self.envelope.objectIds('Workitem')) == 1
        wi = self.envelope.objectValues('Workitem')[0]
        user = getSecurityManager().getUser().getUserName()
        # Activate envelope's workitem
        self.envelope.activateWorkitem(wi.id, actor=user)
        # Check that it did it correctly
        self.assertEquals(wi.actor, 'test_user_1_')
        self.assertEquals(self.envelope.id, wi.instance_id)
        self.assertEquals('Begin', wi.activity_id)
        self.envelope.completeWorkitem(wi.id, actor=user)
        self.assertEquals('complete', wi.status)

def test_suite():
    import unittest
    suite = unittest.makeSuite(EnvelopeTestCase)
    return suite

if __name__ == '__main__':
    framework()

