import os, sys
import unittest
from StringIO import StringIO
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
ZopeTestCase.installProduct('Reportek')
ZopeTestCase.installProduct('PythonScripts')
from configurereportek import ConfigureReportek
from utils import create_fake_root, create_temp_reposit, create_upload_file
from utils import create_envelope, add_document, simple_addEnvelope
from mock import Mock, patch
import lxml.etree


def setUpModule(self):
    self._cleanup_temp_reposit = create_temp_reposit()

def tearDownModule(self):
    self._cleanup_temp_reposit()


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
        simple_addEnvelope(col.manage_addProduct['Reportek'], '', '', '2003', '2004', '',
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
        self.helpCreateEnvelope('2003', '2004', 'Whole Year')
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

    def test_invalid_period(self):
        col = self.app.collection
        self.login() # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        from Products.Reportek import exceptions
        with self.assertRaises(exceptions.InvalidPartOfYear) as ex:
            col.manage_addProduct['Reportek'].manage_addEnvelope('', '', '2003', '2004', 'invalid',
             'http://rod.eionet.eu.int/localities/1', REQUEST=None, previous_delivery='')


def get_xml_metadata(envelope, inline='false'):
    from Products.Reportek.XMLMetadata import XMLMetadata
    xml_data = XMLMetadata(envelope).envelopeMetadata(inline)
    return lxml.etree.parse(StringIO(xml_data)).getroot()


class EnvelopeMetadataTest(unittest.TestCase):

    def setUp(self):
        self.root = create_fake_root()
        self.envelope = create_envelope(self.root)

    def test_metadata_of_empty_envelope(self):
        envelope_el = get_xml_metadata(self.envelope)
        self.assertEqual(envelope_el.attrib['released'], 'false')
        self.assertEqual(envelope_el.xpath('//file'), [])

    def test_metadata_of_envelope_with_document(self):
        add_document(self.envelope, create_upload_file("blah", 'blah.txt'))
        envelope_el = get_xml_metadata(self.envelope)
        xml_file_list = envelope_el.xpath('//file')
        self.assertEqual(len(xml_file_list), 1)
        [xml_file] = xml_file_list
        self.assertEqual(xml_file.attrib['name'], 'blah.txt')
        self.assertEqual(xml_file.attrib['type'], 'text/plain')

    def test_inline_xml_document(self):
        upload_file = create_upload_file('<foo title="bar"/>', 'baz.xml')
        add_document(self.envelope, upload_file)

        with patch.object(self.envelope, 'canViewContent'):
            envelope_el = get_xml_metadata(self.envelope, inline='true')

        xml_instance_list = envelope_el.xpath('//instance')
        self.assertEqual(len(xml_instance_list), 1)

        [xml_instance] = xml_instance_list
        self.assertEqual(xml_instance.attrib['name'], "baz.xml")
        self.assertEqual(xml_instance.attrib['type'], "text/xml")

        self.assertEqual(xml_instance[0].tag, "foo")
        self.assertEqual(xml_instance[0].attrib['title'], "bar")


class EnvelopeCustomDataflowsXmlTest(unittest.TestCase):

    def setUp(self):
        self.root = create_fake_root()
        self.envelope = create_envelope(self.root)

    def test_custom_dataflows_xml(self):
        upload_file = create_upload_file('<foo title="bar"/>', 'baz.xml')
        add_document(self.envelope, upload_file)
        dom = self.envelope.getFormContentAsXML('baz.xml')
        self.assertEqual(dom.firstChild.nodeName, 'foo')
        self.assertEqual(dom.firstChild.attributes['title'].value, 'bar')
