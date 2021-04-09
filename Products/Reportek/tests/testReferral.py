from common import BaseTest, ConfigureReportek
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')


class ReferralTestCase(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(ReferralTestCase, self).afterSetUp()
        self.createStandardDependencies()
        self.createStandardCollection()

    def test_addReferral(self):
        """ To create an referral the following is needed:
            1) self.REQUEST.AUTHENTICATED_USER.getUserName() must return something
            2) There must exist a default workflow
        """
        col = self.app.collection
        self.login()  # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        col.manage_addProduct['Reportek'].manage_addReferral('title', 'description', 'url', '2003', '2004', '',
                                                             'http://rod.eionet.eu.int/localities/1', '', [], REQUEST=self.app.REQUEST)
        self.referral = None
        for env in col.objectValues('Repository Referral'):
            self.referral = env
            break
        self.assertNotEqual(self.referral, None)

    def helpCreateReferral(self, startYear, endYear, duration):
        """ To create an referral the following is needed:
            1) self.REQUEST.AUTHENTICATED_USER.getUserName() must return something
            2) There must exist a default workflow
        """
        col = self.app.collection
        self.login()  # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        col.manage_addProduct['Reportek'].manage_addReferral('title', 'description', 'url', startYear, endYear, duration,
                                                             'http://rod.eionet.eu.int/localities/1', '', [], REQUEST=self.app.REQUEST)
        self.referral = None
        for env in col.objectValues('Repository Referral'):
            self.referral = env
            break
        self.assertNotEqual(self.referral, None)

    def test_endDateMultipleYears(self):
        self.helpCreateReferral('2003', '2004', '')
        s = self.referral.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'), '2003-01-01')
        r = self.referral.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'), '2004-12-31')

    def test_endDateFirstHalf(self):
        self.helpCreateReferral('2003', '', 'FIRST_HALF')
        s = self.referral.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'), '2003-01-01')
        r = self.referral.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'), '2003-06-30')

    def test_endDateFirstQuarter(self):
        self.helpCreateReferral('2009', '', 'FIRST_QUARTER')
        s = self.referral.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'), '2009-01-01')
        r = self.referral.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'), '2009-03-31')

    def test_endDateThirdQuarter(self):
        self.helpCreateReferral('2009', '', 'THIRD_QUARTER')
        s = self.referral.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'), '2009-07-01')
        r = self.referral.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'), '2009-09-30')

    def test_endDateMultipleYearsQuarter(self):
        self.helpCreateReferral('2004', '2009', 'FIRST_QUARTER')
        s = self.referral.getStartDate()
        self.assertEqual(s.strftime('%Y-%m-%d'), '2004-01-01')
        r = self.referral.getEndDate()
        self.assertEqual(r.strftime('%Y-%m-%d'), '2009-12-31')
        rdf = self.referral.rdf(self.app.REQUEST)
        assert rdf.find('startOfPeriod') > -1
        assert rdf.find('endOfPeriod') > -1

    def test_DateNoDates(self):
        self.helpCreateReferral('', '', 'FIRST_QUARTER')
        s = self.referral.getStartDate()
        self.assertEqual(s, None)
        r = self.referral.getEndDate()
        self.assertEqual(r, None)
        rdf = self.referral.rdf(self.app.REQUEST)
        self.assertEqual(-1, rdf.find('startOfPeriod'))
