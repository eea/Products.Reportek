import unittest
from Products.Reportek import constants
from Products.Reportek import DataflowMappings
from Products.Reportek import DataflowMappingRecord
from Products.Reportek import DataflowMappingTable
from utils import create_fake_root


class DFMTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_fake_root()
        dm = DataflowMappings.DataflowMappings()
        self.app._setObject(constants.DATAFLOW_MAPPINGS, dm)
        self.mappings = self.app[constants.DATAFLOW_MAPPINGS]

    def add_mapping(self, id_, *args, **kwargs):
        func = DataflowMappingRecord.manage_addDataflowMappingRecord
        mappingsFolder = self.app[constants.DATAFLOW_MAPPINGS]
        func(mappingsFolder, id_, *args, **kwargs)
        ob = mappingsFolder[id_]
        ob._fix_attributes()

    def add_table(self, id_, dataflow_uri, mapping):
        func = DataflowMappingTable.manage_addDataflowMappingTable
        mappingsFolder = self.app[constants.DATAFLOW_MAPPINGS]
        func(mappingsFolder, id_, id_, dataflow_uri)
        ob = mappingsFolder[id_]
        ob.mapping = mapping

    def testAddOneDFM(self):
        """ Test that we can add a dataflow mapping """
        self.assertTrue(hasattr(self.app, constants.DATAFLOW_MAPPINGS),'Dataflow mappings folder is not created')
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        self.add_mapping('dm1','TestTitle',
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
        self.add_mapping('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema1.xsd'],[])
        self.add_mapping('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema2.xsd'],[])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return empty list as there are no webforms
        self.assertEqual([],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testAddTwoDFMWithWebForm(self):
        """ Create two DFMs with the same obligation """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        self.add_mapping('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',[],['http://schema.xx/schema1.xsd'])
        self.add_mapping('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',[],['http://schema.xx/schema2.xsd'])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return list of schemas with webforms
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testAddTwoDFMOneWithWebForm(self):
        """ Create two DFMs with the same obligation """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        self.add_mapping('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',[],['http://schema.xx/schema1.xsd'])
        self.add_mapping('dm2','TestTitle',
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
        self.add_mapping('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema.xsd','http://schema.xx/schema.xsd'],[])
        self.assertTrue(hasattr(mappingsFolder, 'dm1'),'Record did not get created')
        dm1 = getattr(mappingsFolder, 'dm1')
        self.assertEqual(['http://schema.xx/schema.xsd','http://schema.xx/schema.xsd'], mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))

    def testMultAddTwoDFM(self):
        """ Create two DFMs with the same obligation and multiple schemas """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        self.add_mapping('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema1.xsd','http://schema.xx/schema2.xsd'],[])
        self.add_mapping('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/24',[],['http://schema.xx/schema2.xsd'])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return empty list as there are no webforms for obl. 22
        self.assertEqual([],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testMultAddTwoDFMWithWebForm(self):
        """ Create two DFMs with webform with the same obligation and multiple schemas with webforms """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        self.add_mapping('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',[],['http://schema.xx/schema1.xsd','http://schema.xx/schema2.xsd'])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return list of schemas with webforms
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def testMultAddTwoDFMOneWithWebForm(self):
        """ Create two DFMs with the same obligation """
        mappingsFolder = getattr(self.app, constants.DATAFLOW_MAPPINGS)
        self.add_mapping('dm2','TestTitle',
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
        self.add_mapping('dm1','TestTitle',
           'http://rod.eionet.eu.int/obligations/22',['http://schema.xx/schema1.xsd','http://schema.xx/schema2.xsd',''],[])
        self.add_mapping('dm2','TestTitle',
           'http://rod.eionet.eu.int/obligations/24',[],['http://schema.xx/schema2.xsd'])
        self.assertEqual(['http://schema.xx/schema1.xsd', 'http://schema.xx/schema2.xsd'],
              mappingsFolder.getXMLSchemasForDataflows(['http://rod.eionet.eu.int/obligations/22']))
        # Must return empty list as there are no webforms for obl. 22
        self.assertEqual([],
              mappingsFolder.getXMLSchemasForDataflow('http://rod.eionet.eu.int/obligations/22'))

    def test_api_returns_empty_result_for_empty_query(self):
        self.assertEqual(self.mappings.get_schemas_for_dataflows([]), [])

    def test_api_returns_item(self):
        obli22_uri = 'http://rod.eionet.eu.int/obligations/22'
        schema_title = "Obligation twenty-two"
        schema_uri = 'http://schema.xx/schema1.xsd'
        self.add_mapping('obli22', schema_title, obli22_uri, [schema_uri])

        schemas = self.mappings.get_schemas_for_dataflows([obli22_uri])
        self.assertEqual(len(schemas), 1)
        [schema_info] = schemas
        self.assertDictContainsSubset({
            'title': schema_title,
            'uri': schema_uri,
            'webform_filename': 'obli22.xml',
        }, schema_info)

    def test_api_filters_out_non_matching_dataflows(self):
        obli22_uri = 'http://rod.eionet.eu.int/obligations/22'
        obli23_uri = 'http://rod.eionet.eu.int/obligations/23'
        schema_title = "Obligation twenty-two"
        schema_uri = 'http://schema.xx/schema1.xsd'
        self.add_mapping('obli22_map', schema_title, obli22_uri, [schema_uri])
        self.add_table('obli22_table', obli22_uri,
            [{'url': schema_uri, 'name': schema_title, 'has_webform': False}])

        schemas = self.mappings.get_schemas_for_dataflows([obli23_uri])
        self.assertEqual(len(schemas), 0)

    def test_api_returns_results_from_mapping_table(self):
        obli22_uri = 'http://rod.eionet.eu.int/obligations/22'
        schema_uri = 'http://schema.xx/schema1.xsd'
        schema_title = "Obligation twenty-two"
        self.add_table('obli22', obli22_uri,
            [{'url': schema_uri, 'name': schema_title, 'has_webform': False}])
        schemas = self.mappings.get_schemas_for_dataflows([obli22_uri])
        self.assertEqual(len(schemas), 1)
        [schema_info] = schemas
        self.assertDictContainsSubset({
            'title': schema_title,
            'uri': schema_uri,
        }, schema_info)
