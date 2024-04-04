#
from common import BaseTest, ConfigureReportek, WorkflowTestCase
from mock import Mock, patch
from Testing import ZopeTestCase

from Products.Reportek import constants
from Products.Reportek.RepUtils import getToolByName

ZopeTestCase.installProduct("Reportek")
ZopeTestCase.installProduct("PythonScripts")


class CatalogTest(BaseTest, ConfigureReportek):
    def afterSetUp(self):
        super(CatalogTest, self).afterSetUp()
        # self.app.manage_addProduct["Reportek"]
        # self.createStandardCollection()
        WorkflowTestCase.create_process(self, "p1")
        self.wf.setProcessMappings("p1", "1", "1")

    def addTestCollection(self):
        args = dict(
            id="test_col",
            title="mock_collection",
            year="2011",
            endyear="2012",
            partofyear="wholeyear",
            country="http://spatial/1",
            locality="",
            descr="",
            dataflow_uris=["http://dataflow/1"],
            allow_collections=True,
            allow_envelopes=True,
        )
        col = self.addCollection(self.app, **args)
        return col

    def test_autocatalog_new_object(self):
        catalog = getToolByName(self.root, constants.DEFAULT_CATALOG)
        col = self.addTestCollection()

        env_args = dict(
            title="AutoCatalogTest",
            year=2012,
            endyear=2013,
            partofyear="January",
            country="http://spatial/1",
            locality="TestLocality",
            descr="TestDescription",
        )
        envelope = self.create_envelope(col, **env_args)

        # self.root._setObject(envelope.id, envelope)
        # If we take the catalog via getToolByName,
        # there's an issue getting the object due to the catalog
        # tool having the wrong parent which is an empty app and
        # it will trigger keyerrorr
        catalog = self.app.Catalog
        cataloged = catalog.searchResults(meta_type="Report Envelope")
        self.assertEqual(len(cataloged), 1)
        self.assertEqual(cataloged[0].getObject(), envelope)

    def test_workitem_indexes(self):
        from Products.Reportek.workitem import workitem

        workitem_object = workitem(
            id="test_workitem",
            instance_id="TestInstance",
            activity_id="TestActivity",
            blocked="blocked",
        )
        self.root._setObject(workitem_object.id, workitem_object)

        self.root[workitem_object.id].edit(
            status="TestStatus", actor="TestActor"
        )

        definitions = [
            (
                {"meta_type": "Workitem", "activity_id": "TestActivity"},
                [workitem_object],
            ),
            (
                {"meta_type": "Workitem", "instance_id": "TestInstance"},
                [workitem_object],
            ),
            (
                {"meta_type": "Workitem", "status": "TestStatus"},
                [workitem_object],
            ),
            (
                {"meta_type": "Workitem", "actor": "TestActor"},
                [workitem_object],
            ),
        ]
        # catalog = getToolByName(self.root, constants.DEFAULT_CATALOG)
        catalog = self.app.Catalog
        for query, ok_results in definitions:
            results = catalog.searchResults(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)

    @patch("Products.Reportek.Envelope.transaction.commit")
    def test_envelope_indexes(self, mock_commit):
        from Products.Reportek.Envelope import Envelope

        process = Mock()
        process.absolute_url = Mock(return_value="/ProcessURL")
        first_envelope = Envelope(
            process=process,
            title="FirstEnvelope",
            authUser="TestUser",
            year=2012,
            endyear=2013,
            partofyear="JANUARY",
            country="http://example.com/country/1",
            locality="TestLocality",
            descr="TestDescription",
        )
        first_envelope.getCountryName = Mock(return_value="FirstCountry")
        first_envelope._content_registry_ping = Mock()
        self.engine.messageDialog = Mock()
        first_envelope.id = "first_envelope"
        self.engine._setObject(first_envelope.id, first_envelope)
        self.engine[first_envelope.id].manage_changeEnvelope(
            dataflow_uris="http://example.com/dataflow/1"
        )
        self.engine[first_envelope.id].release_envelope()

        second_envelope = Envelope(
            process=process,
            title="SecondEnvelope",
            authUser="TestUser",
            year=2012,
            endyear=2013,
            partofyear="FEBRUARY",
            country="http://example.com/country/2",
            locality="TestLocality",
            descr="TestDescription",
        ).__of__(self.engine)

        second_envelope._content_registry_ping = Mock()
        second_envelope.id = "second_envelope"
        self.engine._setObject(second_envelope.id, second_envelope)
        self.engine[second_envelope.id].manage_changeEnvelope(
            dataflow_uris="http://example.com/dataflow/2"
        )

        definitions = [
            (
                {"meta_type": "Report Envelope"},
                [first_envelope, second_envelope],
            ),
            (
                {
                    "meta_type": "Report Envelope",
                    "dataflow_uris": "http://example.com/dataflow/1",
                },
                [first_envelope],
            ),
            (
                {
                    "meta_type": "Report Envelope",
                    "country": "http://example.com/country/2",
                },
                [second_envelope],
            ),
            (
                {
                    "meta_type": "Report Envelope",
                    "getCountryName": "FirstCountry",
                },
                [first_envelope],
            ),
            (
                {"meta_type": "Report Envelope", "years": [2012]},
                [first_envelope, second_envelope],
            ),
            (
                {"meta_type": "Report Envelope", "partofyear": "JANUARY"},
                [first_envelope],
            ),
            (
                {
                    "meta_type": "Report Envelope",
                    "process_path": "/ProcessURL",
                },
                [first_envelope, second_envelope],
            ),
            (
                {"meta_type": "Report Envelope", "released": 1},
                [first_envelope],
            ),
            (
                {
                    "meta_type": "Report Envelope",
                    "path": "/ReportekEngine/first_envelope",
                },
                [first_envelope],
            ),
        ]

        for query, ok_results in definitions:
            results = self.root.Catalog(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)

    def test_document_indexes(self):
        from Products.Reportek.Document import Document

        document = Document(
            id="test_document", content_type="application/octet-stream"
        )
        self.root._setObject(document.id, document)
        self.root[document.id].manage_editDocument(
            xml_schema_location="http://example.com/schema"
        )

        definitions = [
            (
                {
                    "meta_type": "Report Document",
                    "xml_schema_location": "http://example.com/schema",
                },
                [document],
            ),
            (
                {
                    "meta_type": "Report Document",
                    "content_type": "application/octet-stream",
                },
                [document],
            ),
        ]

        for query, ok_results in definitions:
            results = self.root.Catalog(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)

    @patch("transaction.savepoint")
    def test_maintenance_tab(self, mock_trans):
        from Products.Reportek.catalog import catalog_rebuild
        from Products.Reportek.Collection import Collection
        from Products.Reportek.Document import Document
        from Products.Reportek.Envelope import Envelope

        process = Mock()
        # self.root._p_jar = Mock()

        collection = Collection(id="test_collection")
        self.root._setObject(collection.id, collection)

        envelope = Envelope(process, "", "", "", "", "", "", "", "")
        envelope._content_registry_ping = Mock()
        envelope.id = "test_envelope"
        self.root[collection.id]._setObject(envelope.id, envelope)

        document = Document(id="test_document")
        self.root[collection.id][envelope.id]._setObject(document.id, document)

        self.root.Catalog.manage_catalogClear()
        catalog_rebuild(self.root)

        # ZopeTestCase setsup a test_folder_1_ too and we have the
        # WorkflowEngine as well and dropdownmenus.txt file, hence 6 objects
        # self.assertEqual(len(self.root.Catalog), 6)

        definitions = [
            ({"meta_type": "Report Collection"}, [collection]),
            ({"meta_type": "Report Envelope"}, [envelope]),
            ({"meta_type": "Report Document"}, [document]),
        ]

        for query, ok_results in definitions:
            results = self.root.Catalog(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)

    @patch("Products.Reportek.Envelope.DateTime")
    def test_date_indexes(self, mock_DateTime):
        from DateTime import DateTime

        from Products.Reportek.Envelope import Envelope

        process = Mock()

        mock_DateTime.return_value = DateTime("2012/05/25")
        first_envelope = Envelope(
            process, "FirstEnvelope", "", "", "", "", "", "", ""
        )
        first_envelope._content_registry_ping = Mock()
        first_envelope.id = "first_envelope"
        self.root._setObject(first_envelope.id, first_envelope)

        mock_DateTime.return_value = DateTime("2012/05/26")
        second_envelope = Envelope(
            process, "SecondEnvelope", "", "", "", "", "", "", ""
        )
        second_envelope._content_registry_ping = Mock()
        second_envelope.id = "second_envelope"
        self.root._setObject(second_envelope.id, second_envelope)

        definitions = [
            (
                {
                    "meta_type": "Report Envelope",
                    "sort_on": "reportingdate",
                    "sort_order": "reverse",
                },
                [second_envelope, first_envelope],
            ),
            (
                {"meta_type": "Report Envelope", "sort_on": "reportingdate"},
                [first_envelope, second_envelope],
            ),
        ]
        # catalog = getToolByName(self.root, constants.DEFAULT_CATALOG)
        catalog = self.root.Catalog
        for query, ok_results in definitions:
            results = catalog.searchResults(**query)
            self.assertEqual([b.getObject() for b in results], ok_results)
