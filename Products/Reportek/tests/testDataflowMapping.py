import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
ZopeTestCase.installProduct('Reportek')

from Products.Reportek import constants

class DFMTestCase(ZopeTestCase.ZopeTestCase):

    def testAddOneDFM(self):
        """ Test that we can add a dataflow mapping """
        self.assertTrue(hasattr(self.app, constants.DATAFLOW_MAPPINGS),'Dataflow mappings folder is not created')
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema.xsd'],[])
        self.assertTrue(hasattr(mappingsFolder, 'dm1'),'Record did not get created')
        dm1 = getattr(mappingsFolder, 'dm1')
        self.assertEqual(['http://schema.xx/schema.xsd'], mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        dm1.manage_settings(title='changed title', dataflow_uri='http://rod.eionet.eu.int/obligations/22',
          allowedSchemas=['http://schema.xx/CHANGED.xsd'], webformSchemas=[])
        self.assertEqual(['http://schema.xx/CHANGED.xsd'], mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))

    def testAddTwoDFM(self):
        """ Create two DFMs with the same obligation """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema1.xsd'],[])
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema2.xsd'],[])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return empty list as there are no webforms
        self.assertEqual([],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testAddTwoDFMWithWebForm(self):
        """ Create two DFMs with the same obligation """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',[],['http://schema.xx/schema1.xsd'])
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',[],['http://schema.xx/schema2.xsd'])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return list of schemas with webforms
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testAddTwoDFMOneWithWebForm(self):
        """ Create two DFMs with the same obligation """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',[],['http://schema.xx/schema1.xsd'])
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema2.xsd'],[])
        # Must return all - two
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return list of schemas with webforms - one
        self.assertEqual(['http://schema.xx/schema1.xsd'],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))


    def testMultAddOneDFM(self):
        """ Test that we can attach multiple schemas when creating a dataflow mapping"""
        self.assertTrue(hasattr(self.app, constants.DATAFLOW_MAPPINGS),'Dataflow mappings folder is not created')
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema.xsd','http://schema.xx/schema.xsd'],[])
        self.assertTrue(hasattr(mappingsFolder, 'dm1'),'Record did not get created')
        dm1 = getattr(mappingsFolder, 'dm1')
        self.assertEqual(['http://schema.xx/schema.xsd','http://schema.xx/schema.xsd'], mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))

    def testMultAddTwoDFM(self):
        """ Create two DFMs with the same obligation and multiple schemas """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema1.xsd','http://schema.xx/schema2.xsd'],[])
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/24',[],['http://schema.xx/schema2.xsd'])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return empty list as there are no webforms for obl. 22
        self.assertEqual([],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testMultAddTwoDFMWithWebForm(self):
        """ Create two DFMs with webform with the same obligation and multiple schemas with webforms """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',[],['http://schema.xx/schema1.xsd','http://schema.xx/schema2.xsd'])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return list of schemas with webforms
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testMultAddTwoDFMOneWithWebForm(self):
        """ Create two DFMs with the same obligation """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema2.xsd'],['http://schema.xx/SCHEMAWITHFORM.xsd'])
        # Must return all - two
        self.assertEqual(['http://schema.xx/schema2.xsd', 'http://schema.xx/SCHEMAWITHFORM.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return list of schemas with webforms - one
        self.assertEqual(['http://schema.xx/SCHEMAWITHFORM.xsd'],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testMultAddTwoDFMEmpty(self):
        """ Create two DFMs with the same obligation and one empty schema
            The object is expected to filter out empty schemas.
        """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema1.xsd','http://schema.xx/schema2.xsd',''],[])
        mappingsFolder.manage_addProduct['Reportek'].manage_addDataflowMappingRecord('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/24',[],['http://schema.xx/schema2.xsd'])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return empty list as there are no webforms for obl. 22
        self.assertEqual([],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(DFMTestCase))
    return suite

if __name__ == '__main__':
    framework()
