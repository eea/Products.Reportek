import unittest

from Products.Reportek.constants import DATAFLOW_MAPPINGS
from Products.Reportek.DataflowMappings import DataflowMappings
from Products.Reportek.DataflowMappingRecord import DataflowMappingRecord
from Products.Reportek.DataflowMappingTable import DataflowMappingTable
from utils import create_fake_root



obligation = 'http://rod.eionet.eu.int/obligations/22'
schema = 'http://schema.xx/schema.xsd'
schema1 = 'http://schema.xx/schema1.xsd'
schema2 = 'http://schema.xx/schema2.xsd'


class DFMTestCase(unittest.TestCase):

    id = DATAFLOW_MAPPINGS


    def setUp(self):
        self.app = create_fake_root()
        dm = DataflowMappings()
        self.app._setObject(self.id, dm)
        self.mappings = self.app[self.id]


    def add_mapping(self, oid, *args, **kwargs):
        ob = DataflowMappingRecord(oid, *args, **kwargs)
        self.mappings._setObject(oid, ob)
        self.mappings[oid]._fix_attributes()


    def add_table(self, oid, dataflow_uri, mapping):
        ob = DataflowMappingTable(oid, oid, dataflow_uri)
        self.mappings._setObject(oid, ob)
        self.mappings[oid].mapping = mapping


    def test_add_dataflow_mapping(self):
        self.add_mapping('test','test title',obligation,[schema],[])
        self.assertTrue(hasattr(self.mappings, 'test'))
        self.assertEqual(
                [schema],
                self.mappings.getXMLSchemasForDataflows([obligation]))

        changed_schema = 'http://schema.xx/CHANGED.xsd'
        self.mappings.test.manage_settings(
                title='changed test title',
                dataflow_uri=obligation,
                allowedSchemas=[changed_schema],
                webformSchemas=[])
        self.assertEqual(
                [changed_schema],
                self.mappings.getXMLSchemasForDataflows([obligation]))


    def test_add_multiple_dataflow_mappings(self):
        self.add_mapping('test1','test title',obligation,[schema1],[])
        self.add_mapping('test2','test title',obligation,[schema2],[])
        self.assertEqual(
                [schema1, schema2],
                self.mappings.getXMLSchemasForDataflows([obligation]))

        # Must return empty list as there are no webforms
        self.assertEqual([],
              self.mappings.getXMLSchemasForDataflow(obligation))


    def test_add_multiple_dataflow_mappings_with_webform(self):
        self.add_mapping('test1','test title',obligation,[],[schema1])
        self.add_mapping('test2','test title',obligation,[],[schema2])
        self.assertEqual(
                [schema1, schema2],
                self.mappings.getXMLSchemasForDataflows([obligation]))

        # Must return list of schemas with webforms
        self.assertEqual(
                [schema1, schema2],
                self.mappings.getXMLSchemasForDataflow(obligation))


    def test_add_multiple_dataflow_mappings_one_with_webform(self):
        self.add_mapping('with_form','test title',obligation,[],[schema1])
        self.add_mapping('no_form','test title',obligation,[schema2],[])

        # Must return all - two
        self.assertEqual(
                [schema1, schema2],
                self.mappings.getXMLSchemasForDataflows([obligation]))

        # Must return list of schemas with webforms - one
        self.assertEqual(
                [schema1],
                self.mappings.getXMLSchemasForDataflow(obligation))


    def test_multiple_schemas(self):
        self.add_mapping('test','test title',obligation,[schema1,schema2],[])
        self.assertTrue(hasattr(self.mappings, 'test'))

        self.assertEqual(
                [schema1, schema2],
                self.mappings.test.getXMLSchemasForDataflows([obligation]))


    def test_multiple_schemas_same_obligation(self):
        new_obligation = 'http://rod.eionet.eu.int/obligations/24'
        self.add_mapping('test1','test title',obligation,[schema1,schema2],[])
        self.add_mapping('test2','test title',new_obligation,[],[schema2])

        self.assertEqual(
                [schema1, schema2],
                self.mappings.getXMLSchemasForDataflows([obligation]))

        self.assertEqual(
                [],
                self.mappings.getXMLSchemasForDataflow(obligation))


    def test_same_schema_multiple_obligations(self):
        self.add_mapping('test','test title',obligation,[],[schema1,schema2])
        self.assertEqual(
                [schema1, schema2],
                self.mappings.getXMLSchemasForDataflows([obligation]))

        # Must return list of schemas with webforms
        self.assertEqual(
                [schema1, schema2],
                self.mappings.getXMLSchemasForDataflow(obligation))


    def test_two_mappings_same_obligation(self):
        schema_with_form = 'http://schema.xx/SCHEMAWITHFORM.xsd'
        self.add_mapping('test',
                'test title',
                obligation,
                [schema2],
                [schema_with_form])

        # Must return all - two
        self.assertEqual(
                [schema2, schema_with_form],
                self.mappings.getXMLSchemasForDataflows([obligation]))

        # Must return list of schemas with webforms - one
        self.assertEqual(
                [schema_with_form],
                self.mappings.getXMLSchemasForDataflow(obligation))


    def test_two_mappings_same_obligation_one_with_empty_schema(self):
        new_obligation = 'http://rod.eionet.eu.int/obligations/24'

        self.add_mapping('test1',
                'test title',
                obligation,
                [schema1,schema2,''],
                [])
        self.add_mapping('test2',
                'test title',
                new_obligation,
                [],
                [schema2])
        self.assertEqual(
                [schema1, schema2],
                self.mappings.getXMLSchemasForDataflows([obligation]))

        # Must return empty list as there are no webforms for obl. 22
        self.assertEqual(
                [],
                self.mappings.getXMLSchemasForDataflow(obligation))


    # DataflowMappingTable tests

    def test_api_returns_empty_result_for_empty_query(self):
        self.assertEqual(self.mappings.get_schemas_for_dataflows([]), [])


    def test_api_returns_item(self):
        self.add_mapping('test', 'test title', obligation, [schema])
        schemas = self.mappings.get_schemas_for_dataflows([obligation])
        self.assertEqual(len(schemas), 1)

        [schema_info] = schemas
        self.assertDictContainsSubset({
            'title': 'test title',
            'uri': schema,
            'webform_filename': 'test.xml',
        }, schema_info)


    def test_api_filters_out_non_matching_dataflows(self):
        other_obligation = 'http://rod.eionet.eu.int/obligations/23'
        self.add_mapping('test', 'test title', obligation, [schema])
        self.add_table(
                'test_table',
                obligation,
                [{
                    'url': schema,
                    'name': 'test title',
                    'has_webform': False}
                ])

        schemas = self.mappings.get_schemas_for_dataflows([other_obligation])
        self.assertEqual(len(schemas), 0)


    def test_api_returns_results_from_mapping_table(self):
        self.add_table(
                'test',
                obligation,
                [{
                    'url': schema,
                    'name': 'test title',
                    'has_webform': False}
                ])
        schemas = self.mappings.get_schemas_for_dataflows([obligation])
        self.assertEqual(len(schemas), 1)

        [schema_info] = schemas
        self.assertDictContainsSubset({
            'title': 'test title',
            'uri': schema,
        }, schema_info)
