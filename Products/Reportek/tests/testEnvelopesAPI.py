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
        return "http://example.com/c/" + self.id

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


class ChildBrain:
    def __init__(self, parent, id, meta_type, **metadata):
        self.id = str(id)
        self.meta_type = meta_type
        self._path = "%s/%s" % (parent, id)
        self.__dict__.update(metadata)

    def getPath(self):
        return self._path

    def getObject(self):
        return SimpleNamespace(status="active")


class ChildrenCatalog:
    """Answers the queries of the envelopes, the workitems and the feedbacks."""

    def __init__(self, envelopes, children):
        self.envelopes = envelopes
        self.children = children
        self.queries = []

    def searchResults(self, **query):
        self.queries.append(query)
        if query["meta_type"] == "Report Envelope":
            return self.envelopes
        path = query["path"]
        if isinstance(path, dict):
            assert path["depth"] == 1
            parents = set(path["query"])
            return [
                b
                for b in self.children
                if b.meta_type == query["meta_type"]
                and b.getPath().rsplit("/", 1)[0] in parents
            ]
        return [
            b
            for b in self.children
            if b.meta_type == query["meta_type"] and b.getPath().startswith(path + "/")
        ]

    def children_queries(self):
        return [q for q in self.queries if q["meta_type"] != "Report Envelope"]


class PrefetchTest(BaseUnitTest):
    PATHS = ["/c/env%d" % i for i in range(30)]

    def setUp(self):
        self.children = []
        for path in self.PATHS[:-1]:  # the last envelope has no children
            for id in (10, 9, 2):
                self.children.append(
                    ChildBrain(
                        path,
                        id,
                        "Workitem",
                        activity_id="Draft",
                        actor="gigel",
                        blocker=False,
                        title="Draft, status: active",
                    )
                )
            self.children.append(
                ChildBrain(path, "fb1", "Report Feedback", title="AutomaticQA")
            )
            self.children.append(
                ChildBrain(
                    path, "fb2", "Report Feedback", title="Other", feedback_status=None
                )
            )
        self.catalog = ChildrenCatalog([], self.children)

    def view(self):
        view = EnvelopesAPI(SimpleNamespace(), FakeRequest({}))
        patcher = patch.object(envelopes, "getToolByName", return_value=self.catalog)
        patcher.start()
        self.addCleanup(patcher.stop)
        return view

    def test_the_children_of_all_the_envelopes_are_one_query(self):
        view = self.view()
        view.prefetch_env_children(self.PATHS, "Workitem")
        self.assertEqual(len(self.catalog.queries), 1)
        for path in self.PATHS:
            self.assertIn((path, "Workitem"), view._children_cache)

    def test_the_workitems_of_an_envelope_are_sorted_by_id(self):
        view = self.view()
        view.prefetch_env_children(self.PATHS, "Workitem")
        ids = [b.id for b in view._children_cache[(self.PATHS[0], "Workitem")]]
        self.assertEqual(ids, ["2", "9", "10"])

    def test_the_children_belong_to_their_envelope(self):
        view = self.view()
        view.prefetch_env_children(self.PATHS, "Report Feedback")
        for path in self.PATHS[:-1]:
            brains = view._children_cache[(path, "Report Feedback")]
            self.assertEqual([b.id for b in brains], ["fb1", "fb2"])
            self.assertEqual({b.getPath().rsplit("/", 1)[0] for b in brains}, {path})

    def test_an_envelope_without_children_gets_an_empty_list(self):
        view = self.view()
        view.prefetch_env_children(self.PATHS, "Workitem")
        self.assertEqual(view._children_cache[(self.PATHS[-1], "Workitem")], [])

    def test_the_brains_are_the_ones_of_the_query_of_each_envelope(self):
        prefetched = self.view()
        prefetched.prefetch_env_children(self.PATHS, "Workitem")
        prefetched.prefetch_env_children(self.PATHS, "Report Feedback")
        single = self.view()
        for path in self.PATHS:
            for children_type in ("Workitem", "Report Feedback"):
                self.assertEqual(
                    prefetched.get_env_children(path, children_type),
                    single.get_env_children(path, children_type),
                    (path, children_type),
                )

    def test_the_prefetched_children_are_not_queried_again(self):
        view = self.view()
        view.prefetch_env_children(self.PATHS, "Workitem")
        queries = len(self.catalog.queries)
        for path in self.PATHS:
            view.get_env_children(path, "Workitem")
        view.prefetch_env_children(self.PATHS, "Workitem")
        self.assertEqual(len(self.catalog.queries), queries)

    def test_only_the_envelopes_not_in_the_cache_are_queried(self):
        view = self.view()
        view.prefetch_env_children(self.PATHS[:10], "Workitem")
        view.prefetch_env_children(self.PATHS, "Workitem")
        self.assertEqual(self.catalog.queries[-1]["path"]["query"], self.PATHS[10:])

    def test_there_is_no_query_without_envelopes(self):
        view = self.view()
        view.prefetch_env_children([], "Workitem")
        self.assertEqual(self.catalog.queries, [])


class QueriesOfTheApiTest(BaseUnitTest):
    def setUp(self):
        self.brains = [FakeBrain("env%d" % i, "Draft") for i in range(30)]
        self.paths = [b.getPath() for b in self.brains]
        children = []
        for path in self.paths:
            for id in (3, 1, 2):
                children.append(
                    ChildBrain(
                        path,
                        id,
                        "Workitem",
                        activity_id="Draft",
                        actor="gigel",
                        blocker=False,
                        title="Draft, status: active",
                        bobobase_modification_time=FakeDate(),
                        activation_log=[],
                    )
                )
            children.append(ChildBrain(path, "fb", "Report Feedback", title="Other"))
        self.catalog = ChildrenCatalog(self.brains, children)

    def call(self, **form):
        view = EnvelopesAPI(
            SimpleNamespace(ReportekEngine=SimpleNamespace()), FakeRequest(form)
        )
        with patch.object(
            envelopes, "getToolByName", return_value=self.catalog
        ), patch.object(EnvelopesAPI, "getCountryCode", return_value="xx"):
            return json.loads(view())["envelopes"]

    def test_the_workflow_properties_need_two_queries_for_all_the_envelopes(self):
        envs = self.call(url="/c", fields="status,creator,hasUnknownQC")
        self.assertEqual(len(envs), 30)
        self.assertEqual(
            envs[0], {"status": "Draft", "creator": "gigel", "hasUnknownQC": 0}
        )
        self.assertEqual(
            sorted(q["meta_type"] for q in self.catalog.children_queries()),
            ["Report Feedback", "Workitem"],
        )

    def test_the_history_needs_one_query_for_all_the_envelopes(self):
        envs = self.call(url="/c", fields="history")
        self.assertEqual([h["id"] for h in envs[0]["history"]], ["1", "2", "3"])
        self.assertEqual(
            [q["meta_type"] for q in self.catalog.children_queries()], ["Workitem"]
        )

    def test_the_other_fields_need_no_query_for_the_children(self):
        for fields in (None, "title", "files,feedbacks"):
            with patch.object(
                EnvelopesAPI, "get_files", return_value={"documents": [], "errors": []}
            ), patch.object(
                EnvelopesAPI, "get_feedbacks", return_value={"feedbacks": []}
            ):
                self.call(url="/c", **({"fields": fields} if fields else {}))
            self.assertEqual(self.catalog.children_queries(), [], fields)


class FakeUser:
    def __init__(self, id, roles, groups=None):
        self.id = id
        self.roles = roles
        if groups is not None:
            self.groups = groups

    def getId(self):
        return self.id

    def getUserName(self):
        return self.id

    def getRoles(self):
        return list(self.roles)

    def getGroups(self):
        return self.groups


class FakeUserWithoutGroups:
    def __init__(self, id, roles):
        self.id = id
        self.roles = roles

    def getId(self):
        return self.id

    def getRoles(self):
        return list(self.roles)


class RestrictedBrain(FakeBrain):
    def __init__(self, id, allowed, rid=None):
        super().__init__(id, "Draft")
        self.allowed = allowed
        self.rid = id if rid is None else rid

    def getRID(self):
        return self.rid


class SecurityCatalog(FakeCatalog):
    """Keeps the brains of which allowedRolesAndUsers match the query."""

    def __init__(self, brains):
        super().__init__(brains)
        self.queries = []

    def searchResults(self, **query):
        self.queries.append(query)
        allowed = query.get("allowedRolesAndUsers")
        if allowed is None:
            return self.brains
        return [b for b in self.brains if set(b.allowed) & set(allowed)]


class SecurityQueryTest(BaseUnitTest):
    PUBLIC = ["Anonymous"]
    RESTRICTED = ["Manager", "RoleA", "RoleB", "user:group-a", "user:gigel"]

    def setUp(self):
        self.brains = [
            RestrictedBrain("public1", self.PUBLIC),
            RestrictedBrain("restricted1", self.RESTRICTED),
            RestrictedBrain("public2", self.PUBLIC),
            RestrictedBrain("restricted2", self.RESTRICTED),
        ]
        self.catalog = SecurityCatalog(self.brains)

    def query(self, user, deployment="CDR"):
        view = EnvelopesAPI(SimpleNamespace(), None)
        with patch.object(envelopes, "REPORTEK_DEPLOYMENT", deployment), patch.object(
            envelopes,
            "getSecurityManager",
            return_value=SimpleNamespace(getUser=lambda: user),
        ):
            return view.get_security_query()

    def titles(self, user, deployment="CDR", **form):
        view = EnvelopesAPI(
            SimpleNamespace(ReportekEngine=SimpleNamespace()),
            FakeRequest(dict(url="/c", **form)),
        )
        with patch.object(envelopes, "REPORTEK_DEPLOYMENT", deployment), patch.object(
            envelopes,
            "getSecurityManager",
            return_value=SimpleNamespace(getUser=lambda: user),
        ), patch.object(
            envelopes, "getToolByName", return_value=self.catalog
        ), patch.object(EnvelopesAPI, "getCountryCode", return_value="xx"):
            envs = json.loads(view())["envelopes"]
        return [e["title"] for e in envs]

    def test_the_roles_the_id_and_the_groups_of_the_user_are_allowed(self):
        user = FakeUser(
            "gigel",
            ["RoleB", "Authenticated"],
            ["group-a", "AuthenticatedUsers"],
        )
        self.assertEqual(
            self.query(user),
            {
                "allowedRolesAndUsers": [
                    "RoleB",
                    "Authenticated",
                    "Anonymous",
                    "user:gigel",
                    "user:group-a",
                    "user:AuthenticatedUsers",
                ]
            },
        )

    def test_a_user_without_groups_has_its_roles_and_its_id(self):
        user = FakeUserWithoutGroups("Anonymous User", ["Anonymous"])
        self.assertEqual(
            self.query(user),
            {"allowedRolesAndUsers": ["Anonymous", "Anonymous", "user:Anonymous User"]},
        )

    def test_a_user_with_no_groups_has_no_group_entries(self):
        user = FakeUser("gigel", ["Authenticated"], [])
        self.assertEqual(
            self.query(user),
            {"allowedRolesAndUsers": ["Authenticated", "Anonymous", "user:gigel"]},
        )

    def test_cdr_and_bdr_limit_the_envelopes(self):
        user = FakeUser("gigel", ["Authenticated"], ["a-group"])
        expected = {
            "allowedRolesAndUsers": [
                "Authenticated",
                "Anonymous",
                "user:gigel",
                "user:a-group",
            ]
        }
        for deployment in ("CDR", "BDR"):
            self.assertEqual(self.query(user, deployment), expected, deployment)

    def test_the_other_deployments_do_not_limit_the_envelopes(self):
        user = FakeUser("gigel", ["Authenticated"], ["a-group"])
        for deployment in ("MDR", "", "other"):
            self.assertEqual(self.query(user, deployment), {}, deployment)

    def test_the_query_of_the_envelopes_has_the_allowed_roles_and_users(self):
        user = FakeUser("gigel", ["Authenticated"], ["a-group"])
        self.titles(user)
        self.assertEqual(
            self.catalog.queries[0]["allowedRolesAndUsers"],
            ["Authenticated", "Anonymous", "user:gigel", "user:a-group"],
        )

    def test_the_query_of_the_envelopes_is_not_limited_on_other_deployments(self):
        user = FakeUser("gigel", ["Authenticated"], ["a-group"])
        self.titles(user, "MDR")
        self.assertNotIn("allowedRolesAndUsers", self.catalog.queries[0])

    def test_the_query_of_the_envelopes_is_limited_on_bdr(self):
        user = FakeUser("gigel", ["Authenticated"], ["a-group"])
        self.titles(user, "BDR")
        self.assertIn("allowedRolesAndUsers", self.catalog.queries[0])

    def test_anonymous_gets_the_public_envelopes(self):
        user = FakeUserWithoutGroups("Anonymous User", ["Anonymous"])
        self.assertEqual(
            self.titles(user, fields="title"),
            [
                "Envelope public1",
                "Envelope public2",
            ],
        )

    def test_a_user_allowed_through_a_group_gets_the_restricted_envelopes(self):
        user = FakeUser("someone", ["Authenticated"], ["group-a"])
        self.assertEqual(
            self.titles(user, fields="title"),
            [
                "Envelope public1",
                "Envelope restricted1",
                "Envelope public2",
                "Envelope restricted2",
            ],
        )

    def test_a_user_in_another_group_does_not(self):
        user = FakeUser("someone", ["Authenticated"], ["group-b"])
        self.assertEqual(
            self.titles(user, fields="title"),
            ["Envelope public1", "Envelope public2"],
        )

    def test_a_user_allowed_through_its_own_id_or_a_role_gets_them(self):
        for user in (
            FakeUser("gigel", ["Authenticated"], []),
            FakeUser("someone", ["Authenticated", "RoleB"], []),
            FakeUser("admin", ["Manager"], []),
        ):
            self.assertEqual(
                len(self.titles(user, fields="title")), 4, user.getId()
            )

    def test_the_envelopes_keep_their_order(self):
        user = FakeUser("admin", ["Manager"], [])
        self.assertEqual(
            self.titles(user, fields="title"),
            ["Envelope " + b.id for b in self.brains],
        )

    def test_the_children_queries_are_not_limited(self):
        user = FakeUser("someone", ["Authenticated"], [])
        self.titles(user, fields="title")
        self.assertEqual(len(self.catalog.queries), 1)


class FakeMiddleware:
    recheck_interval = 300

    def __init__(self, paths=None, error=None):
        self.paths = {"paths": [], "prev_paths": [], "audit_paths": []}
        self.paths.update(paths or {})
        self.error = error
        self.asked = []
        self.checked = []

    def getUserCollectionPaths(self, ecas_user_id, userdata=None, recheck_interval=None):
        self.asked.append((ecas_user_id, userdata, recheck_interval))
        if self.error:
            raise self.error
        return self.paths

    def authorizedUser(self, ecas_user_id, path, userdata=None):
        # the same test as the one of the middleware
        self.checked.append(path)
        for kind, access in (
            ("paths", "RW"),
            ("prev_paths", "RO"),
            ("audit_paths", "AUDIT"),
        ):
            for allowed_path in self.paths[kind]:
                if allowed_path in path:
                    return access
        return False


class FakeEcas:
    def __init__(self, ecas_user_id="ecas-gigel"):
        self.ecas_user_id = ecas_user_id
        self.usernames = []

    def getEcasUserId(self, username):
        self.usernames.append(username)
        return self.ecas_user_id


class FakeEngine:
    def __init__(self, middleware, ecas):
        self.authMiddleware = middleware
        self.ecas = ecas

    def unrestrictedTraverse(self, path, default=None):
        return self.ecas if path == "/acl_users/eCas" else default


class RegistryMiddlewareTest(BaseUnitTest):
    """The access that the registry middleware gives, which BDR also asks."""

    def setUp(self):
        self.brains = [
            RestrictedBrain("a1", ["RoleB", "Manager"], rid=11),
            RestrictedBrain("a2", ["RoleC", "Manager"], rid=12),
            RestrictedBrain("a3", ["user:gigel"], rid=13),
            RestrictedBrain("a4", ["RoleD"], rid=14),
        ]
        self.catalog = SecurityCatalog(self.brains)
        self.user = FakeUser("gigel", ["Authenticated", "RoleB"], [])
        self.middleware = FakeMiddleware()
        self.ecas = FakeEcas()

    def titles(self, deployment="BDR", ecas=True, middleware=True):
        engine = FakeEngine(
            self.middleware if middleware else None, self.ecas if ecas else None
        )
        view = EnvelopesAPI(
            SimpleNamespace(ReportekEngine=engine),
            FakeRequest({"url": "/c", "fields": "title"}),
        )
        with patch.object(envelopes, "REPORTEK_DEPLOYMENT", deployment), patch.object(
            envelopes,
            "getSecurityManager",
            return_value=SimpleNamespace(getUser=lambda: self.user),
        ), patch.object(
            envelopes, "getToolByName", return_value=self.catalog
        ), patch.object(EnvelopesAPI, "getCountryCode", return_value="xx"):
            envs = json.loads(view())["envelopes"]
        return [e["title"][len("Envelope ") :] for e in envs]

    def test_a_user_without_paths_gets_what_the_roles_allow(self):
        self.assertEqual(self.titles(), ["a1", "a3"])
        self.assertEqual(len(self.middleware.asked), 1)
        self.assertEqual(self.middleware.checked, [])
        self.assertEqual(len(self.catalog.queries), 1)

    def test_the_registry_is_asked_for_the_ecas_id_of_the_user(self):
        self.titles()
        self.assertEqual(self.ecas.usernames, ["gigel"])
        ecas_user_id, userdata, recheck_interval = self.middleware.asked[0]
        self.assertEqual(ecas_user_id, "ecas-gigel")
        self.assertEqual(userdata, {"username": "gigel", "ecas_id": "ecas-gigel"})
        self.assertEqual(recheck_interval, 300)

    def test_the_paths_of_the_registry_add_their_envelopes(self):
        self.middleware.paths["paths"] = ["c/a2"]
        self.assertEqual(self.titles(), ["a1", "a2", "a3"])

    def test_every_kind_of_access_adds_the_envelopes(self):
        for kind in ("paths", "prev_paths", "audit_paths"):
            self.middleware = FakeMiddleware({kind: ["c/a4"]})
            self.assertEqual(self.titles(), ["a1", "a3", "a4"], kind)

    def test_the_envelopes_keep_their_order_of_the_catalog(self):
        self.middleware.paths["paths"] = ["c/a4", "c/a2"]
        self.assertEqual(self.titles(), ["a1", "a2", "a3", "a4"])

    def test_only_the_envelopes_that_the_roles_do_not_allow_are_asked(self):
        self.middleware.paths["paths"] = ["c/a2"]
        self.titles()
        self.assertEqual(self.middleware.checked, ["c/a2", "c/a4"])

    def test_the_path_has_no_leading_slash_as_in_the_permission_check(self):
        self.middleware.paths["paths"] = ["/c/a2"]
        self.assertEqual(self.titles(), ["a1", "a3"])

    def test_a_registry_that_fails_gives_what_the_roles_allow(self):
        self.middleware.error = OSError("registry is down")
        with patch.object(envelopes, "logger") as logger:
            self.assertEqual(self.titles(), ["a1", "a3"])
        logger.warning.assert_called_once()

    def test_without_the_ecas_plugin_the_roles_are_used(self):
        self.assertEqual(self.titles(ecas=False), ["a1", "a3"])
        self.assertEqual(self.middleware.asked, [])

    def test_without_the_middleware_the_roles_are_used(self):
        self.assertEqual(self.titles(middleware=False), ["a1", "a3"])

    def test_a_user_without_an_ecas_id_is_not_asked(self):
        self.ecas.ecas_user_id = None
        self.assertEqual(self.titles(), ["a1", "a3"])
        self.assertEqual(self.middleware.asked, [])

    def test_cdr_does_not_ask_the_registry(self):
        self.middleware.paths["paths"] = ["c/a2"]
        self.assertEqual(self.titles("CDR"), ["a1", "a3"])
        self.assertEqual(self.middleware.asked, [])

    def test_other_deployments_are_not_limited_nor_ask_the_registry(self):
        self.middleware.paths["paths"] = ["c/a2"]
        self.assertEqual(self.titles("MDR"), ["a1", "a2", "a3", "a4"])
        self.assertEqual(self.middleware.asked, [])
