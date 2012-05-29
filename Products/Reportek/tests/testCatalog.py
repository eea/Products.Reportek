import unittest
from utils import create_fake_root, makerequest
from mock import patch


class CatalogTest(unittest.TestCase):

    def setUp(self):
        from Products.ZCatalog.ZCatalog import ZCatalog
        from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
        from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex
        from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
        from Products.PluginIndexes.PathIndex.PathIndex import PathIndex
        from Products.Reportek import create_reportek_indexes

        self.root = makerequest(create_fake_root())

        catalog = ZCatalog('Catalog', 'Default Catalog for Reportek')
        self.root._setObject('Catalog', catalog)
        self.root.Catalog.meta_types = [
            {'name': 'FieldIndex', 'instance': FieldIndex},
            {'name': 'KeywordIndex', 'instance': KeywordIndex},
            {'name': 'DateIndex', 'instance': DateIndex},
            {'name': 'PathIndex', 'instance': PathIndex},]
        create_reportek_indexes(self.root.Catalog)

    def test_autocatalog_new_object(self):
        from Products.Reportek.EnvelopeInstance import EnvelopeInstance
        from mock import Mock

        process = Mock()
        envelope = EnvelopeInstance(process)
        envelope.id = 'new-envelope'
        self.root._setObject(envelope.id, envelope)

        cataloged_objects = self.root.Catalog()
        self.assertEqual(len(cataloged_objects), 1)
        self.assertEqual(cataloged_objects[0].getObject(), envelope)

    def test_workitem_indexes(self):
        from Products.Reportek.workitem import workitem

        workitem_object = workitem(id='test_workitem',
                                    instance_id='TestInstance',
                                    activity_id='TestActivity',
                                    blocked='blocked')
        self.root._setObject(workitem_object.id, workitem_object)

        self.root[workitem_object.id].edit(status='TestStatus',
                                            actor = 'TestActor')

        definitions = [
            ({'meta_type': 'Workitem', 'activity_id': 'TestActivity'}, [workitem_object]),
            ({'meta_type': 'Workitem', 'instance_id': 'TestInstance'}, [workitem_object]),
            ({'meta_type': 'Workitem', 'status': 'TestStatus'}, [workitem_object]),
            ({'meta_type': 'Workitem', 'actor': 'TestActor'}, [workitem_object])]

        for query, ok_results in definitions:
            results = self.root.Catalog(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)

    def test_envelope_indexes(self):
        from Products.Reportek.Envelope import Envelope
        from mock import Mock

        self.root.localities_table = Mock(return_value=[
                    {
                        'iso': 'FC',
                        'name': 'FirstCountry',
                        'uri': 'http://example.com/country/1'
                    },
                    {
                        'iso': 'SC',
                        'name': 'SecondCountry',
                        'uri': 'http://example.com/country/2'
                    }])

        process = Mock()
        process.absolute_url = Mock(return_value='/ProcessURL')
        first_envelope = Envelope(process=process,
                            title='FirstEnvelope',
                            authUser='TestUser',
                            year=2012,
                            endyear=2013,
                            partofyear='January',
                            country='http://example.com/country/1',
                            locality='TestLocality',
                            descr='TestDescription')

        first_envelope.id = 'first_envelope'
        self.root._setObject(first_envelope.id, first_envelope)
        self.root[first_envelope.id].manage_changeEnvelope(dataflow_uris='http://example.com/dataflow/1')
        self.root[first_envelope.id].release_envelope()

        second_envelope = Envelope(process=process,
                            title='SecondEnvelope',
                            authUser='TestUser',
                            year=2012,
                            endyear=2013,
                            partofyear='February',
                            country='http://example.com/country/2',
                            locality='TestLocality',
                            descr='TestDescription')

        second_envelope.id = 'second_envelope'
        self.root._setObject(second_envelope.id, second_envelope)
        self.root[second_envelope.id].manage_changeEnvelope(dataflow_uris='http://example.com/dataflow/2')

        definitions = [
            ({'meta_type': 'Report Envelope'}, [first_envelope, second_envelope]),
            ({'meta_type': 'Report Envelope', 'dataflow_uris': 'http://example.com/dataflow/1'}, [first_envelope]),
            ({'meta_type': 'Report Envelope', 'country': 'http://example.com/country/2'}, [second_envelope]),
            ({'meta_type': 'Report Envelope', 'getCountryName': 'FirstCountry'}, [first_envelope]),
            ({'meta_type': 'Report Envelope', 'years': [2012]}, [first_envelope, second_envelope]),
            ({'meta_type': 'Report Envelope', 'partofyear': 'January'}, [first_envelope]),
            ({'meta_type': 'Report Envelope', 'process_path': '/ProcessURL'}, [first_envelope, second_envelope]),
            ({'meta_type': 'Report Envelope', 'released': 1}, [first_envelope]),
            ({'meta_type': 'Report Envelope', 'path': '/first_envelope'}, [first_envelope]),
            ]

        for query, ok_results in definitions:
            results = self.root.Catalog(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)

    def test_document_indexes(self):
        from Products.Reportek.Document import Document

        document = Document(id='test_document', content_type='application/octet-stream')
        self.root._setObject(document.id, document)
        self.root[document.id].manage_editDocument(xml_schema_location='http://example.com/schema')

        definitions = [
            ({'meta_type': 'Report Document', 'xml_schema_location': 'http://example.com/schema'}, [document]),
            ({'meta_type': 'Report Document', 'content_type': 'application/octet-stream'}, [document]),
            ]

        for query, ok_results in definitions:
            results = self.root.Catalog(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)

    def test_maintenance_tab(self):
        from mock import Mock
        from Products.Reportek.Collection import Collection
        from Products.Reportek.Envelope import Envelope
        from Products.Reportek.Document import Document
        from Products.Reportek.catalog import catalog_rebuild

        process = Mock()
        self.root._p_jar = Mock()

        collection = Collection(id='test_collection')
        self.root._setObject(collection.id, collection)

        envelope = Envelope(process, '', '', '', '', '', '', '', '')
        envelope.id = 'test_envelope'
        self.root[collection.id]._setObject(envelope.id, envelope)

        document = Document(id='test_document')
        self.root[collection.id][envelope.id]._setObject(document.id, document)

        self.root.Catalog.manage_catalogClear()
        catalog_rebuild(self.root)
        self.assertEqual(len(self.root.Catalog), 3)

        definitions = [
            ({'meta_type': 'Report Collection'}, [collection]),
            ({'meta_type': 'Report Envelope'}, [envelope]),
            ({'meta_type': 'Report Document'}, [document]),
            ]

        for query, ok_results in definitions:
            results = self.root.Catalog(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)

    @patch('Products.Reportek.Envelope.DateTime')
    def test_date_indexes(self, mock_DateTime):
        from Products.Reportek.Envelope import Envelope
        from DateTime import DateTime
        from mock import Mock

        process = Mock()

        mock_DateTime.return_value = DateTime('2012/05/25')
        first_envelope = Envelope(process, 'FirstEnvelope', '', '', '', '', '', '', '')
        first_envelope.id = 'first_envelope'
        self.root._setObject(first_envelope.id, first_envelope)

        mock_DateTime.return_value = DateTime('2012/05/26')
        second_envelope = Envelope(process, 'SecondEnvelope', '', '', '', '', '', '', '')
        second_envelope.id = 'second_envelope'
        self.root._setObject(second_envelope.id, second_envelope)

        definitions = [
            ({'meta_type': 'Report Envelope', 'sort_on': 'reportingdate', 'sort_order': 'reverse'},
                    [second_envelope, first_envelope]),
            ({'meta_type': 'Report Envelope', 'sort_on': 'reportingdate'},
                    [first_envelope, second_envelope]),
            ]

        for query, ok_results in definitions:
            results = self.root.Catalog(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)
