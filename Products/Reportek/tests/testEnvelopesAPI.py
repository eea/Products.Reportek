"""Tests for the workflow properties of the envelopes API."""

import json
from types import SimpleNamespace
from unittest.mock import patch

from Products.Reportek.api import envelopes
from Products.Reportek.api.envelopes import EnvelopesAPI

from .common import BaseUnitTest


class FakeDate:
    def HTML4(self):
        return "2026-01-01T00:00:00Z"


class FakeBrain:
    years = [2025, 2026]
    dataflow_uris = []
    Description = ""
    country = None
    released = 1
    partofyear = "WHOLE_YEAR"
    activation_log = []
    reportingdate = FakeDate()
    bobobase_modification_time = FakeDate()

    def __init__(self, id, status):
        self.id = id
        self.title = "Envelope " + id
        self.status = status

    def getURL(self):
        return "http://cdr/c/" + self.id

    def getPath(self):
        return "/c/" + self.id


class FakeCatalog:
    def __init__(self, brains):
        self.brains = brains

    def searchResults(self, **query):
        return self.brains


class FakeRequest:
    def __init__(self, form):
        self.form = form
        self.environ = {}
        self.RESPONSE = SimpleNamespace(setHeader=lambda *args: None)


class WorkflowPropertiesTest(BaseUnitTest):
    FILES = {"documents": [{"title": "a.xml"}], "errors": []}
    FEEDBACKS = {"feedbacks": [{"title": "Feedback"}]}

    def setUp(self):
        self.brains = [FakeBrain("env1", "Draft"), FakeBrain("env2", "Final")]
        self.additional_calls = []

    def additional_props(self, view, brain):
        self.additional_calls.append(brain.id)
        return {
            "isBlockedByQCError": 0,
            "status": brain.status,
            "activity": brain.status,
            "statusDate": "2026-02-02T00:00:00Z",
            "activityDate": "2026-02-02T00:00:00Z",
            "activityStatus": "active",
            "creator": "gigel",
            "hasUnknownQC": 1,
        }

    def call(self, **form):
        """Return the envelopes of the API for the given request form."""
        view = EnvelopesAPI(
            SimpleNamespace(ReportekEngine=SimpleNamespace()), FakeRequest(form)
        )
        with patch.object(
            envelopes, "getToolByName", return_value=FakeCatalog(self.brains)
        ), patch.object(
            EnvelopesAPI,
            "get_additional_props",
            lambda view, brain: self.additional_props(view, brain),
        ), patch.object(
            EnvelopesAPI, "getCountryCode", return_value="xx"
        ), patch.object(
            EnvelopesAPI, "get_files", return_value=self.FILES
        ), patch.object(
            EnvelopesAPI, "get_feedbacks", return_value=self.FEEDBACKS
        ), patch.object(
            EnvelopesAPI, "get_env_history", return_value=[{"id": "1"}]
        ), patch.object(
            EnvelopesAPI,
            "get_envelope_company_metadata",
            return_value={"company_id": 7, "company": "ACME"},
        ):
            return json.loads(view())["envelopes"]

    def test_the_default_fields_do_not_need_the_workflow(self):
        envs = self.call(url="/c")
        self.assertEqual(len(envs), 2)
        self.assertEqual(self.additional_calls, [])

    def test_fields_of_the_catalog_do_not_need_the_workflow(self):
        envs = self.call(url="/c", fields="title,isReleased,reportingDate")
        self.assertEqual(
            envs,
            [
                {
                    "title": "Envelope env1",
                    "isReleased": 1,
                    "reportingDate": "2026-01-01T00:00:00Z",
                },
                {
                    "title": "Envelope env2",
                    "isReleased": 1,
                    "reportingDate": "2026-01-01T00:00:00Z",
                },
            ],
        )
        self.assertEqual(self.additional_calls, [])

    def test_files_feedbacks_and_history_do_not_need_the_workflow(self):
        for fields in ("files", "feedbacks", "history", "companyId,companyName"):
            self.additional_calls[:] = []
            envs = self.call(url="/c", fields=fields)
            self.assertEqual(len(envs), 2, fields)
            self.assertEqual(self.additional_calls, [], fields)

    def test_the_values_of_files_feedbacks_and_history_are_unchanged(self):
        envs = self.call(url="/c", fields="title,files,feedbacks,history,companyId")
        self.assertEqual(
            envs[0],
            {
                "title": "Envelope env1",
                "files": self.FILES["documents"],
                "feedbacks": self.FEEDBACKS["feedbacks"],
                "history": [{"id": "1"}],
                "companyId": 7,
            },
        )

    def test_catalog_filters_do_not_need_the_workflow(self):
        for form in (
            {"reportingDateStart": "2026-01-01"},
            {"reportingDateEnd": "2026-12-31"},
            {"modifiedDateStart": "2026-01-01"},
            {"isReleased": "1"},
            {"periodDescription": "whole year"},
            {"title": "Envelope env1"},
        ):
            self.additional_calls[:] = []
            self.call(fields="files", **form)
            self.assertEqual(self.additional_calls, [], form)

    def test_workflow_fields_are_computed_for_each_envelope(self):
        for field in EnvelopesAPI.WORKFLOW_PROPS:
            self.additional_calls[:] = []
            envs = self.call(url="/c", fields=field)
            self.assertEqual(self.additional_calls, ["env1", "env2"], field)
            self.assertEqual(
                envs[0][field], self.additional_props(None, self.brains[0])[field]
            )

    def test_workflow_fields_next_to_others_are_computed(self):
        envs = self.call(url="/c", fields="files,status,title")
        self.assertEqual(self.additional_calls, ["env1", "env2"])
        self.assertEqual(
            envs[1],
            {
                "files": self.FILES["documents"],
                "status": "Final",
                "title": "Envelope env2",
            },
        )

    def test_workflow_filters_are_computed_for_each_envelope(self):
        for form in (
            {"status": "draft"},
            {"activity": "draft"},
            {"statusDate": "2026-02-02"},
            {"activityDate": "2026-02-02"},
            {"statusDateStart": "2026-01-01"},
            {"statusDateEnd": "2026-12-31"},
            {"activityDateStart": "2026-01-01"},
            {"activityDateEnd": "2026-12-31"},
            {"creator": "gigel"},
            {"hasUnknownQC": "1"},
            {"isBlockedByQCError": "0"},
            {"activityStatus": "active"},
        ):
            self.additional_calls[:] = []
            self.call(url="/c", fields="files", **form)
            self.assertEqual(self.additional_calls, ["env1", "env2"], form)

    def test_the_workflow_filters_still_filter(self):
        envs = self.call(url="/c", fields="title", status="final")
        self.assertEqual(envs, [{"title": "Envelope env2"}])
        envs = self.call(url="/c", fields="files", activity="draft,final")
        self.assertEqual(len(envs), 2)
        self.assertEqual(self.call(url="/c", fields="files", creator="nobody"), [])

    def test_unknown_fields_are_ignored(self):
        self.assertEqual(self.call(url="/c", fields="nothing"), [])
        envs = self.call(url="/c", fields="nothing,title")
        self.assertEqual(envs[0], {"title": "Envelope env1"})
        self.assertEqual(self.additional_calls, [])

    def test_the_default_properties_are_the_default_fields(self):
        envs = self.call(url="/c")
        self.assertEqual(
            sorted(envs[0]),
            [
                "countryCode",
                "description",
                "isReleased",
                "modifiedDate",
                "obligations",
                "periodDescription",
                "periodEndYear",
                "periodStartYear",
                "reportingDate",
                "title",
                "url",
            ],
        )


class WorkflowFiltersTest(BaseUnitTest):
    def test_the_workflow_filters_are_the_filters_that_are_not_of_the_catalog(self):
        # A filter that is neither answered by the catalog nor by a default
        # property is answered by the workflow properties, which are only
        # computed for the filters and fields of WORKFLOW_FILTERS.
        view = EnvelopesAPI(SimpleNamespace(ReportekEngine=SimpleNamespace()), None)
        with patch.object(EnvelopesAPI, "getCountryCode", return_value="xx"):
            default_props = view.get_default_props(FakeBrain("env1", "Draft"))
        not_in_the_catalog = {
            name
            for name, filter_ in EnvelopesAPI.AVAILABLE_FILTERS.items()
            if not filter_["catalog_mapping"]
        }
        self.assertEqual(
            not_in_the_catalog - set(default_props), set(EnvelopesAPI.WORKFLOW_FILTERS)
        )

    def test_the_workflow_fields_are_the_properties_of_get_additional_props(self):
        view = EnvelopesAPI(SimpleNamespace(ReportekEngine=SimpleNamespace()), None)
        brain = FakeBrain("env1", "Draft")
        workitem = SimpleNamespace(
            activity_id="Draft", actor="gigel", blocker=False, status="active"
        )
        workitem.getObject = lambda: workitem
        with patch.object(
            EnvelopesAPI, "get_env_children", return_value=[workitem]
        ), patch.object(EnvelopesAPI, "has_unknown_qc", return_value=0):
            props = view.get_additional_props(brain)
        self.assertEqual(sorted(props), sorted(EnvelopesAPI.WORKFLOW_PROPS))
