import unittest

from Products.Reportek.constants import DATAFLOW_MAPPINGS
from Products.Reportek.DataflowMappingsRecord import DataflowMappingsRecord
from Products.Reportek.DataflowMappings import DataflowMappings
from utils import makerequest, create_fake_root, create_catalog
from mock import Mock


class DFMTestCase(unittest.TestCase):

    id = DATAFLOW_MAPPINGS

    def setUp(self):
        self.app = makerequest(create_fake_root())
        self.catalog = create_catalog(self.app)
        dm = DataflowMappings()
        self.app._setObject(self.id, dm)
        self.mappings = self.app[self.id]

    def add_mapping(self, oid, *args, **kwargs):
        ob = DataflowMappingsRecord(
            oid,
            title=args[0],
            dataflow_uri=args[1])
        self.mappings._setObject(oid, ob)

        mapping = []
        for schema in args[2]:
            if schema:
                mapping.append(
                    {
                        'url': schema,
                        'name': 'x',
                        'has_webform': False
                    }
                )

        for schema in args[3]:
            if schema:
                mapping.append(
                    {
                        'url': schema,
                        'name': 'x',
                        'has_webform': True
                    }
                )
        self.mappings[oid].mapping = {'schemas': mapping}

    def test_add_multiple_dataflow_mappings(self):

        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'

        self.add_mapping('test', 'test title', obligation,
                         [schema1, schema2], [])
        self.assertEqual(
            [schema1, schema2],
            self.mappings.getSchemasForDataflows(obligation))

        # Must return empty list as there are no webforms
        self.assertEqual([],
                         self.mappings.getSchemasForDataflows(obligation, web_form_only=True))

    def test_add_multiple_dataflow_mappings_with_webform(self):

        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'

        self.add_mapping('test1', 'test title', obligation,
                         [], [schema1, schema2])
        self.assertEqual(
            [schema1, schema2],
            self.mappings.getSchemasForDataflows(obligation))

        # Must return list of schemas with webforms
        self.assertEqual(
            [schema1, schema2],
            self.mappings.getSchemasForDataflows(obligation, web_form_only=True))

    def test_add_multiple_dataflow_mappings_one_with_webform(self):

        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'

        self.add_mapping(
            'with_form', 'test title',
            obligation,
            [schema1],
            [schema2])

        # Must return all - two
        self.assertEqual(
            [schema1, schema2],
            self.mappings.getSchemasForDataflows(obligation))

        # Must return list of schemas with webforms - one
        self.assertEqual(
            [schema2],
            self.mappings.getSchemasForDataflows(obligation, web_form_only=True))

    def test_multiple_schemas(self):

        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'

        self.add_mapping('test', 'test title', obligation,
                         [schema1, schema2], [])
        self.assertTrue(hasattr(self.mappings, 'test'))

        self.assertEqual([schema1, schema2],
                         self.mappings.test.getSchemasForDataflows(obligation))

    def test_add_schema(self):
        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'

        self.add_mapping('test', 'test title', obligation, [schema1], [])
        self.assertTrue(hasattr(self.mappings, 'test'))
        request = Mock(form=dict(schema=schema2,
                                 name='schema2'))
        self.mappings.test.add_schema(request)
        self.assertEqual([schema1, schema2],
                         self.mappings.test.getSchemasForDataflows(obligation))

    def test_delete_schemas(self):
        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'
        # never added; delete_schemas should hold robust though
        schema3 = 'http://schema.xx/schema3.xsd'

        self.add_mapping('test', 'test title', obligation,
                         [schema1, schema2], [])
        self.assertTrue(hasattr(self.mappings, 'test'))
        self.assertEqual([schema1, schema2],
                         self.mappings.test.getSchemasForDataflows(obligation))
        request = Mock(form=dict(ids=[schema1, schema3]))
        self.mappings.test.delete_schemas(request)
        self.assertEqual([schema2],
                         self.mappings.test.getSchemasForDataflows(obligation))

    def test_edit_add(self):
        obligation = 'http://rod.eionet.eu.int/obligations/22'
        self.add_mapping('test', 'test title', obligation, [], [])

        self.mappings.test._edit = Mock()
        self.mappings.test.add_schema = Mock()
        request = Mock(method='POST',
                       form=dict(add=True))
        self.mappings.test.edit(request)
        self.assertTrue(self.mappings.test.add_schema.called)
        self.assertTrue(self.mappings.test._edit.called)

    def test_edit_delete(self):
        obligation = 'http://rod.eionet.eu.int/obligations/22'
        self.add_mapping('test', 'test title', obligation, [], [])

        self.mappings.test._edit = Mock()
        self.mappings.test.delete_schemas = Mock()
        request = Mock(method='POST',
                       form=dict(delete=True))
        self.mappings.test.edit(request)
        self.assertTrue(self.mappings.test.delete_schemas.called)
        self.assertTrue(self.mappings.test._edit.called)

    def test_edit_update(self):
        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        self.add_mapping('test', 'test title', obligation, [schema1], [])
        newTitle = 'new test title'
        newObligation = 'http://rod.eionet.eu.int/obligations/22_new'

        self.mappings.test._edit = Mock()
        #self.mappings.test.delete_schemas = Mock()
        request = Mock(method='POST',
                       form=dict(update=True,
                                 dataflow_uris=newObligation,
                                 title=newTitle))
        self.mappings.test.edit(request)
        self.assertEqual(self.mappings.test.title, newTitle)
        self.assertEqual(self.mappings.test.dataflow_uri, newObligation)
        self.assertTrue(self.mappings.test._edit.called)

    def test_multiple_records(self):

        obligation = 'http://rod.eionet.eu.int/obligations/22'
        new_obligation = 'http://rod.eionet.eu.int/obligations/24'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'

        self.add_mapping('test1', 'test title', obligation,
                         [schema1, schema2], [])
        self.add_mapping('test2', 'test title', new_obligation, [], [schema2])

        self.assertEqual(
            [schema1, schema2],
            self.mappings.getSchemasForDataflows(obligation))

        self.assertEqual(
            [],
            self.mappings.getSchemasForDataflows(obligation, web_form_only=True))

    def test_same_schema_multiple_obligations(self):

        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'

        self.add_mapping('test', 'test title', obligation,
                         [], [schema1, schema2])
        self.assertEqual(
            [schema1, schema2],
            self.mappings.getSchemasForDataflows(obligation))

        # Must return list of schemas with webforms
        self.assertEqual(
            [schema1, schema2],
            self.mappings.getSchemasForDataflows(obligation, web_form_only=True))

    def test_two_mappings_same_obligation(self):

        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema = 'http://schema.xx/schema.xsd'
        schema_with_form = 'http://schema.xx/SCHEMAWITHFORM.xsd'

        self.add_mapping('test',
                         'test title',
                         obligation,
                         [schema],
                         [schema_with_form])

        # Must return all - two
        self.assertEqual(
            [schema, schema_with_form],
            self.mappings.getSchemasForDataflows(obligation))

        # Must return list of schemas with webforms - one
        self.assertEqual(
            [schema_with_form],
            self.mappings.getSchemasForDataflows(obligation, web_form_only=True))

    def test_two_mappings_with_empty_schema(self):

        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'

        self.add_mapping('test1',
                         'test title',
                         obligation,
                         [schema1, schema2, ''],
                         [])
        self.assertEqual(
            [schema1, schema2],
            self.mappings.getSchemasForDataflows(obligation))

        # Must return empty list as there are no webforms for obl. 22
        self.assertEqual(
            [],
            self.mappings.getSchemasForDataflows(obligation, web_form_only=True))

    def test_getSchemaObjectsForDataflow(self):
        obligation = 'http://rod.eionet.eu.int/obligations/22'
        schema1 = 'http://schema.xx/schema1.xsd'
        schema2 = 'http://schema.xx/schema2.xsd'
        self.add_mapping('test1',
                         'test title',
                         obligation,
                         [schema1],
                         [schema2])
        expected = [
            {'has_webform': False,
             'name': 'x',
             'url': schema1},
            {'has_webform': True,
             'name': 'x',
             'url': schema2}]

        results = list(
            self.mappings.getSchemaObjectsForDataflows(obligation, False))
        self.assertEqual(expected, results)
