import unittest
import zipfile
from collections import OrderedDict

from common import BaseTest, BaseUnitTest, ConfigureReportek
from DateTime import DateTime
from mock import Mock, patch
from StringIO import StringIO
from utils import (
    add_document,
    create_envelope,
    create_fake_root,
    create_upload_file,
)

from Products.Reportek import Converters, constants
from Products.Reportek.Envelope import Envelope
from Products.Reportek.ReportekEngine import (
    ReportekEngine,
    _group_ecr_content_data,
)


class ReportekEngineTest(BaseTest, ConfigureReportek):
    def afterSetUp(self):
        super(ReportekEngineTest, self).afterSetUp()
        self.createStandardCatalog()

        self.engine.localities_dict = Mock(
            return_value={
                "http://rod.eionet.eu.int/spatial/2": {"name": "Albania"},
                "http://rod.eionet.eu.int/spatial/3": {"name": "Austria"},
            }
        )
        self.engine.ZopeTime = Mock(return_value=DateTime())

    def test_searchfeedbacks_on_disk(self):
        self.createStandardDependencies()
        self.createStandardCollection()
        self.createStandardEnvelope()
        try:
            zpt = ReportekEngine.searchfeedbacks
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsfeedbacks_on_disk(self):
        try:
            zpt = ReportekEngine.resultsfeedbacks
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_recent_uploads_on_disk(self):
        try:
            zpt = ReportekEngine.recent
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_searchdataflow_on_disk(self):
        try:
            zpt = ReportekEngine._searchdataflow
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_searchxml_on_disk(self):
        try:
            zpt = ReportekEngine.searchxml
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    def test_resultsxml_on_disk(self):
        try:
            zpt = ReportekEngine.resultsxml
            zpt.read()
        except (AttributeError, IOError) as err:
            self.fail(err)

    # def test_getUniqueValuesFor(self):
    #     process = Mock()
    #     process.absolute_url = Mock(return_value="/ProcessURL")
    #     first_envelope = Envelope(
    #         process=process,
    #         title="FirstEnvelope",
    #         authUser="TestUser",
    #         year=2012,
    #         endyear=2013,
    #         partofyear="JANUARY",
    #         country="http://example.com/country/1",
    #         locality="TestLocality",
    #         descr="TestDescription",
    #     )
    #     first_envelope._content_registry_ping = Mock()
    #     first_envelope.id = "first_envelope"
    #     self.root._setObject(first_envelope.id, first_envelope)
    #     self.root[first_envelope.id].manage_changeEnvelope(
    #         dataflow_uris="http://example.com/dataflow/1"
    #     )
    #     # While running the coverage test, the following line returns
    #     # an empty tuple, but if we insert a pdb to debug, it returns
    #     # the proper value. This is a bug in the test, not in the code.
    #     results = self.engine.getUniqueValuesFor("dataflow_uris")
    #     self.assertEqual(results, ("http://example.com/dataflow/1",))

    @unittest.expectedFailure
    def test_manage_editEngine_GET(self):
        """
        This tests simulates a GET to ReportekEngine/manage_editEngine
        and checks that engine's attributes are not changed
        """
        from copy import copy

        self.engine.ZopeTime = Mock(return_value=DateTime())
        before_values = copy(self.engine.__dict__)
        # FIXME
        self.login()
        assert self.engine.manage_properties()
        self.assertEqual(before_values, self.engine.__dict__)

    @unittest.expectedFailure
    def test_manage_editEngine_no_REQUEST(self):
        """
        This tests simulates a programmatic call to
        ReportekEngine.manage_editEngine and checks that engine's attributes
        are changed accordingly
        """
        # FIXME
        self.engine.ZopeTime = Mock(return_value=DateTime())
        self.engine.title = "Before Title"
        self.engine.manage_editEngine(title="After Title", REQUEST=None)
        self.assertEqual("After Title", self.engine.title)

    @unittest.expectedFailure
    def test_manage_editEngine_POST(self):
        """
        This tests simulates a POST to ReportekEngine.manage_editEngine
        and checks that engine's attributes are changed accordingly
        """
        # FIXME
        self.root.REQUEST["REQUEST_METHOD"] = "POST"
        self.engine.ZopeTime = Mock(return_value=DateTime())
        self.engine.title = "Before Title"
        self.engine.manage_editEngine(
            title="After Title", REQUEST=self.root.REQUEST
        )
        self.assertEqual("After Title", self.engine.title)


class SearchResultsTest(BaseTest, ConfigureReportek):
    def afterSetUp(self):
        super(SearchResultsTest, self).afterSetUp()
        self.createStandardCatalog()

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
        first_envelope._content_registry_ping = Mock()
        first_envelope.id = "first_envelope"
        self.root._setObject(first_envelope.id, first_envelope)
        self.root[first_envelope.id].manage_changeEnvelope(
            dataflow_uris="http://example.com/dataflow/1"
        )
        self.root["first_envelope"].getEngine = Mock()
        setattr(
            self.root.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters(),
        )
        safe_html = Mock(convert=Mock(return_value=Mock(text="feedbacktext")))
        getattr(
            self.root.getPhysicalRoot(), constants.CONVERTERS_ID
        ).__getitem__ = Mock(return_value=safe_html)
        self.root["first_envelope"].manage_addFeedback(
            "feedbackid",
            "Title",
            "Feedback text",
            "",
            "WorkflowEngine/begin_end",
            1,
        )
        self.root["first_envelope"].manage_addFeedback(
            "feedback5",
            "Title",
            "Feedback text",
            "",
            "WorkflowEngine/begin_end",
            1,
        )
        self.root["first_envelope"].manage_addFeedback(
            "feedback10",
            "Title",
            "Feedback text",
            "",
            "WorkflowEngine/begin_end",
            1,
        )

        second_envelope = Envelope(
            process=process,
            title="SecondEnvelope",
            authUser="TestUser",
            year=2012,
            endyear=2013,
            partofyear="JUNE",
            country="http://example.com/country/2",
            locality="TestLocality",
            descr="TestDescription",
        )
        second_envelope._content_registry_ping = Mock()
        second_envelope.id = "second_envelope"
        self.root._setObject(second_envelope.id, second_envelope)
        self.root[second_envelope.id].manage_changeEnvelope(
            dataflow_uris="http://example.com/dataflow/2"
        )

    def test_returns_all(self):
        results = self.engine.getSearchResults()
        envs = [el.getObject() for el in results]
        self.assertItemsEqual(
            envs,
            [
                self.root.first_envelope,
                self.root.first_envelope["feedbackid"],
                self.root.first_envelope["feedback5"],
                self.root.first_envelope["feedback10"],
                self.root.second_envelope,
            ],
        )

    def test_filter_by_meta_type(self):
        results = self.engine.getSearchResults(meta_type="Report Feedback")
        envs = [el.getObject() for el in results]
        self.assertItemsEqual(
            envs,
            [
                self.root.first_envelope["feedbackid"],
                self.root.first_envelope["feedback5"],
                self.root.first_envelope["feedback10"],
            ],
        )

    def test_filter_by_dataflow_uris(self):
        results = self.engine.getSearchResults(
            dataflow_uris="http://example.com/dataflow/2"
        )
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.second_envelope])

    def test_filter_by_country(self):
        results = self.engine.getSearchResults(
            country="http://example.com/country/1"
        )
        res = [el.getObject() for el in results]
        self.assertEqual(res, [self.root.first_envelope])

    def test_filter_by_id(self):
        results = self.engine.getSearchResults(
            id={"range": "min:max", "query": ["feedback0", "feedback9"]}
        )
        feedbacks = [el.getObject() for el in results]
        self.assertEqual(
            feedbacks,
            [
                self.root.first_envelope["feedback5"],
                self.root.first_envelope["feedback10"],
            ],
        )

    def test_filter_by_reportingdate(self):
        self.root["first_envelope"].manage_changeEnvelope(
            reportingdate=DateTime("2010/07/02 00:00:00 GMT+2")
        )
        results = self.engine.getSearchResults(
            reportingdate={
                "range": "min:max",
                "query": [
                    DateTime("2010/07/01 00:00:00 GMT+2"),
                    DateTime("2010/07/03 00:00:00 GMT+2"),
                ],
            }
        )
        envs = [el.getObject() for el in results]
        self.assertEqual(envs, [self.root.first_envelope])


class ReportekEngineZipTest(BaseUnitTest):
    def test_zip_download(self):
        content = "test content for our document"
        root = create_fake_root()
        engine = BaseTest.create_reportek_engine(root)

        envelope = create_envelope(root)
        add_document(envelope, create_upload_file(content, "foo.txt"))
        envelope.released = True
        envelope.title = "TestedEnvelope"

        response_body = StringIO()
        mock_response = Mock(write=response_body.write)

        with patch("Products.Reportek.ReportekEngine.getSecurityManager"):
            engine.zipEnvelopes(["/envelope"], Mock(), mock_response)

        response_body.seek(0)
        response_zip = zipfile.ZipFile(response_body)
        self.assertEqual(
            response_zip.namelist(),
            [
                "TestedEnvelope/foo.txt",
                "TestedEnvelope/metadata.txt",
                "TestedEnvelope/README.txt",
                "TestedEnvelope/history.txt",
            ],
        )
        self.assertEqual(response_zip.read("TestedEnvelope/foo.txt"), content)


def _make_collection(title, path, country_code=""):
    """Build a mock collection for ECR grouping tests."""
    col = Mock()
    col.title_or_id = Mock(return_value=title)
    col.getPhysicalPath = Mock(return_value=path)
    col.getCountryCode = Mock(return_value=country_code)
    return col


def _make_envelope(company_name, reportingdate):
    """Build a mock envelope for ECR grouping tests."""
    env = Mock()
    env.get_zope_company_meta = Mock(return_value=(company_name, "id"))
    env.reportingdate = reportingdate
    return env


class GroupEcrContentDataTest(BaseUnitTest):
    """Tests for the ecr-collections grouping helper.

    These exercise _group_ecr_content_data directly so we don't need a
    BDR-deployed engine or a full Zope test stack.
    """

    def test_empty_input_returns_empty_groups(self):
        result = _group_ecr_content_data({})
        for key in (
            "rw_by_path",
            "ro_by_path",
            "audit_by_path",
            "client_by_path",
            "fgas_by_company",
        ):
            self.assertEqual(len(result[key]), 0)

    def test_none_input_returns_empty_groups(self):
        result = _group_ecr_content_data(None)
        self.assertEqual(len(result["rw_by_path"]), 0)
        self.assertEqual(len(result["fgas_by_company"]), 0)

    def test_returns_ordered_dicts(self):
        """All returned groups are OrderedDict for deterministic order."""
        result = _group_ecr_content_data({})
        for key in (
            "rw_by_path",
            "ro_by_path",
            "audit_by_path",
            "client_by_path",
            "fgas_by_company",
        ):
            self.assertIsInstance(result[key], OrderedDict)

    def test_rw_collections_grouped_by_path_first_segment(self):
        col_a = _make_collection("Alpha", ("", "fgases", "col1"))
        col_b = _make_collection("Beta", ("", "ods", "col2"))
        col_c = _make_collection("Gamma", ("", "fgases", "col3"))

        result = _group_ecr_content_data(
            {"ecr": {"rw": [col_a, col_b, col_c]}}
        )

        self.assertEqual(set(result["rw_by_path"].keys()), {"fgases", "ods"})
        self.assertEqual(len(result["rw_by_path"]["fgases"]), 2)
        self.assertEqual(len(result["rw_by_path"]["ods"]), 1)

    def test_rw_within_group_sorted_case_insensitive_by_title(self):
        col_b = _make_collection("Beta", ("", "fgases", "col1"))
        col_a = _make_collection("alpha", ("", "fgases", "col2"))
        col_c = _make_collection("Charlie", ("", "fgases", "col3"))

        result = _group_ecr_content_data(
            {"ecr": {"rw": [col_b, col_a, col_c]}}
        )

        titles = [c.title_or_id() for c in result["rw_by_path"]["fgases"]]
        self.assertEqual(titles, ["alpha", "Beta", "Charlie"])

    def test_ro_sorted_by_country_code_then_title(self):
        col_b_fr = _make_collection(
            "Beta", ("", "fgases", "col1"), country_code="FR"
        )
        col_a_de = _make_collection(
            "Alpha", ("", "fgases", "col2"), country_code="DE"
        )
        col_c_de = _make_collection(
            "Charlie", ("", "fgases", "col3"), country_code="DE"
        )

        result = _group_ecr_content_data(
            {"ecr": {"ro": [col_b_fr, col_c_de, col_a_de]}}
        )

        titles = [c.title_or_id() for c in result["ro_by_path"]["fgases"]]
        self.assertEqual(titles, ["Alpha", "Charlie", "Beta"])

    def test_audit_collections_use_auditor_key(self):
        col = _make_collection("Audit One", ("", "fgases", "audit1"))
        result = _group_ecr_content_data({"Auditor": [col]})
        self.assertEqual(len(result["audit_by_path"]["fgases"]), 1)

    def test_client_collections_use_client_key(self):
        col = _make_collection("Client One", ("", "fgases", "client1"))
        result = _group_ecr_content_data({"Client": [col]})
        self.assertEqual(len(result["client_by_path"]["fgases"]), 1)

    def test_fgas_envelopes_grouped_by_company_name(self):
        env1 = _make_envelope("Acme Corp", 100)
        env2 = _make_envelope("Beta Inc", 200)
        env3 = _make_envelope("Acme Corp", 150)

        result = _group_ecr_content_data(
            {"ecr": {"audit_paths": [env1, env2, env3]}}
        )

        self.assertEqual(
            set(result["fgas_by_company"].keys()),
            {"Acme Corp", "Beta Inc"},
        )
        self.assertEqual(len(result["fgas_by_company"]["Acme Corp"]), 2)
        self.assertEqual(len(result["fgas_by_company"]["Beta Inc"]), 1)

    def test_fgas_envelopes_within_company_sorted_by_reportingdate_desc(self):
        env_old = _make_envelope("Acme", 100)
        env_new = _make_envelope("Acme", 300)
        env_mid = _make_envelope("Acme", 200)

        result = _group_ecr_content_data(
            {"ecr": {"audit_paths": [env_old, env_new, env_mid]}}
        )

        dates = [e.reportingdate for e in result["fgas_by_company"]["Acme"]]
        self.assertEqual(dates, [300, 200, 100])

    def test_fgas_envelope_with_no_company_uses_unknown_label(self):
        env_unknown = _make_envelope(None, 100)
        env_known = _make_envelope("Acme", 200)

        result = _group_ecr_content_data(
            {"ecr": {"audit_paths": [env_unknown, env_known]}}
        )

        self.assertIn("Unknown Company", result["fgas_by_company"])
        self.assertEqual(
            len(result["fgas_by_company"]["Unknown Company"]), 1
        )

    def test_fgas_company_keys_alphabetically_sorted_case_sensitive(self):
        """Matches the original `sorted(fgas_by_company.keys())`."""
        env_z = _make_envelope("Zeta", 100)
        env_a = _make_envelope("alpha", 200)
        env_m = _make_envelope("Mid", 300)

        result = _group_ecr_content_data(
            {"ecr": {"audit_paths": [env_z, env_a, env_m]}}
        )

        # Case-sensitive sort: capitals before lowercase in ASCII
        self.assertEqual(
            list(result["fgas_by_company"].keys()),
            ["Mid", "Zeta", "alpha"],
        )

    def test_fgas_get_zope_company_meta_called_once_per_envelope(self):
        """Regression guard: previously called up to 3 times per env."""
        env_a = _make_envelope("Acme", 100)
        env_b = _make_envelope("Beta", 200)

        _group_ecr_content_data(
            {"ecr": {"audit_paths": [env_a, env_b]}}
        )

        self.assertEqual(env_a.get_zope_company_meta.call_count, 1)
        self.assertEqual(env_b.get_zope_company_meta.call_count, 1)

    def test_all_sections_populated_independently(self):
        rw = _make_collection("R", ("", "fgases", "rw1"))
        ro = _make_collection("O", ("", "fgases", "ro1"))
        audit = _make_collection("A", ("", "fgases", "a1"))
        client = _make_collection("C", ("", "fgases", "c1"))
        fgas_env = _make_envelope("Co", 100)

        result = _group_ecr_content_data(
            {
                "ecr": {
                    "rw": [rw],
                    "ro": [ro],
                    "audit_paths": [fgas_env],
                },
                "Auditor": [audit],
                "Client": [client],
            }
        )

        self.assertEqual(len(result["rw_by_path"]["fgases"]), 1)
        self.assertEqual(len(result["ro_by_path"]["fgases"]), 1)
        self.assertEqual(len(result["audit_by_path"]["fgases"]), 1)
        self.assertEqual(len(result["client_by_path"]["fgases"]), 1)
        self.assertEqual(len(result["fgas_by_company"]["Co"]), 1)
