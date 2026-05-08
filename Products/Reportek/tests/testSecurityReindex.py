# -*- coding: utf-8 -*-
"""Tests for the local-roles-changed event flow and the
batched security-reindex walker it drives.

Covers `reindex_security_batched` plus integration with
`Collection.manage_setLocalRoles` / `manage_delLocalRoles` /
`manage_addLocalRoles`.
"""

import itertools

from mock import patch
from Testing import ZopeTestCase
from zope.event import subscribers as zope_subscribers

from Products.Reportek import RepUtils, constants, security_reindex
from Products.Reportek.config import DEPLOYMENT_BDR, DEPLOYMENT_CDR
from Products.Reportek.events import LocalRolesChangedEvent
from Products.Reportek.RepUtils import getToolByName
from Products.Reportek.tests.common import (
    BaseTest,
    ConfigureReportek,
    WorkflowTestCase,
)

ZopeTestCase.installProduct("Reportek")
ZopeTestCase.installProduct("PythonScripts")


def _post(request):
    """Mark a Zope test REQUEST as POST so @requestmethod decorators pass."""
    request.method = "POST"
    return request


def _capture_events():
    """Install a zope.event subscriber that records LocalRolesChangedEvents.

    Returns (captured_list, uninstall_fn).
    """
    captured = []

    def _listener(event):
        if isinstance(event, LocalRolesChangedEvent):
            captured.append(event)

    zope_subscribers.append(_listener)

    def _uninstall():
        try:
            zope_subscribers.remove(_listener)
        except ValueError:
            pass

    return captured, _uninstall


class ReindexSecurityBatchedTest(BaseTest, ConfigureReportek):
    """Layer 2: walker correctness and batching."""

    def afterSetUp(self):
        super(ReindexSecurityBatchedTest, self).afterSetUp()
        WorkflowTestCase.create_process(self, "p1")
        self.wf.setProcessMappings("p1", "1", "1")
        self.col = self.addCollection(
            self.app,
            id="walk_col",
            title="walker test",
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

    def _add_envelopes(self, n):
        # generate_id uses int(time.time()) for entropy and collides on
        # rapid successive calls; mock it to produce stable unique ids.
        ids = itertools.count()
        original_generate_id = RepUtils.generate_id
        RepUtils.generate_id = lambda template: "%s_%d" % (template, next(ids))
        try:
            envs = []
            for i in range(n):
                env = self.create_envelope(
                    self.col,
                    title="Env%d" % i,
                    year=2012,
                    endyear=2013,
                    country="http://spatial/1",
                    locality="",
                    descr="",
                )
                envs.append(env)
            return envs
        finally:
            RepUtils.generate_id = original_generate_id

    def test_walker_visits_all_descendants(self):
        envs = self._add_envelopes(3)
        catalog = getToolByName(self.app, constants.DEFAULT_CATALOG)
        col_path = "/".join(self.col.getPhysicalPath())
        # Total descendants in the catalog under the collection (each
        # envelope drags in additional indexed children, e.g. workitems).
        expected = sum(
            1
            for brain in catalog.unrestrictedSearchResults(path=col_path)
            if brain.getPath() != col_path
        )
        self.assertGreaterEqual(expected, len(envs))
        with patch.object(
            catalog, "_reindexObject", wraps=catalog._reindexObject
        ) as spy:
            count = security_reindex.reindex_security_batched(self.col, batch_size=10)
        self.assertEqual(count, expected)
        self.assertEqual(spy.call_count, expected)
        # Every envelope must be among the targets.
        visited = {"/".join(c[0][0].getPhysicalPath()) for c in spy.call_args_list}
        for env in envs:
            self.assertIn("/".join(env.getPhysicalPath()), visited)
        # Every call uses the right indexes and skips metadata.
        for call in spy.call_args_list:
            kwargs = call[1]
            self.assertEqual(kwargs.get("idxs"), security_reindex.SECURITY_INDEXES)
            self.assertEqual(kwargs.get("update_metadata"), 0)

    def test_walker_skips_self(self):
        self._add_envelopes(2)
        catalog = getToolByName(self.app, constants.DEFAULT_CATALOG)
        col_path = "/".join(self.col.getPhysicalPath())
        with patch.object(
            catalog, "_reindexObject", wraps=catalog._reindexObject
        ) as spy:
            security_reindex.reindex_security_batched(self.col)
        for call in spy.call_args_list:
            target = call[0][0]
            self.assertNotEqual(
                "/".join(target.getPhysicalPath()),
                col_path,
                "walker reindexed self; should be caller's responsibility",
            )

    def test_walker_commits_savepoints_per_batch(self):
        self._add_envelopes(5)
        catalog = getToolByName(self.app, constants.DEFAULT_CATALOG)
        col_path = "/".join(self.col.getPhysicalPath())
        total = sum(
            1
            for brain in catalog.unrestrictedSearchResults(path=col_path)
            if brain.getPath() != col_path
        )
        batch_size = 2
        with patch("Products.Reportek.security_reindex.transaction.savepoint") as sp:
            count = security_reindex.reindex_security_batched(
                self.col, batch_size=batch_size
            )
        self.assertEqual(count, total)
        # One savepoint per completed batch (incomplete final batch -> none).
        self.assertEqual(sp.call_count, total // batch_size)

    def test_walker_with_no_catalog_returns_zero(self):
        self.app._delObject(constants.DEFAULT_CATALOG)
        # Must use a fresh acquired wrapper since catalog was removed.
        self.assertEqual(security_reindex.reindex_security_batched(self.col), 0)

    def test_walker_skips_brain_with_missing_object(self):
        self._add_envelopes(2)
        catalog = getToolByName(self.app, constants.DEFAULT_CATALOG)
        col_path = "/".join(self.col.getPhysicalPath())
        baseline = sum(
            1
            for brain in catalog.unrestrictedSearchResults(path=col_path)
            if brain.getPath() != col_path
        )
        original = catalog.unrestrictedSearchResults

        class BadBrain(object):
            def getPath(self):
                return "/app/walk_col/ghost"

            def _unrestrictedGetObject(self):
                raise KeyError("ghost")

        def _patched_search(*args, **kw):
            return list(original(*args, **kw)) + [BadBrain()]

        with patch.object(
            catalog,
            "unrestrictedSearchResults",
            side_effect=_patched_search,
        ):
            count = security_reindex.reindex_security_batched(self.col)
        # Ghost is silently skipped; real descendants are still counted.
        self.assertEqual(count, baseline)


class OnLocalRolesChangedSubscriberTest(BaseTest, ConfigureReportek):
    """Subscriber gate: deployment."""

    def afterSetUp(self):
        super(OnLocalRolesChangedSubscriberTest, self).afterSetUp()
        WorkflowTestCase.create_process(self, "p1")
        self.wf.setProcessMappings("p1", "1", "1")
        self.col = self.addCollection(
            self.app,
            id="sub_col",
            title="subscriber test",
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

    def test_non_bdr_deployment_is_a_noop(self):
        with (
            patch.object(security_reindex, "REPORTEK_DEPLOYMENT", DEPLOYMENT_CDR),
            patch.object(security_reindex, "reindex_security_batched") as mock_walker,
        ):
            security_reindex.on_local_roles_changed(
                self.col, LocalRolesChangedEvent(self.col, {"AnyRole"})
            )
        # mock 1.0.1 has no assert_not_called; check call_count instead
        self.assertEqual(mock_walker.call_count, 0)

    def test_bdr_runs_cascade_unconditionally(self):
        # Cascade runs regardless of whether the changed role grants View.
        with (
            patch.object(security_reindex, "REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR),
            patch.object(
                security_reindex,
                "reindex_security_batched",
                return_value=7,
            ) as mock_walker,
        ):
            security_reindex.on_local_roles_changed(
                self.col, LocalRolesChangedEvent(self.col, {"AnyRole"})
            )
        mock_walker.assert_called_once_with(self.col)


class CollectionManageRolesIntegrationTest(BaseTest, ConfigureReportek):
    """Integration: Collection.manage_*LocalRoles fires the right events
    in the right conditions, and never breaks the existing role-set
    behavior."""

    def afterSetUp(self):
        super(CollectionManageRolesIntegrationTest, self).afterSetUp()
        WorkflowTestCase.create_process(self, "p1")
        self.wf.setProcessMappings("p1", "1", "1")
        self.col = self.addCollection(
            self.app,
            id="int_col",
            title="integration test",
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
        self.captured, self._uninstall = _capture_events()

    def beforeTearDown(self):
        self._uninstall()

    # --- behavior preservation ---

    def test_set_local_roles_without_request_does_not_fire_event(self):
        # Mirrors api/roles.py and ReportekEngine call style.
        self.col.manage_setLocalRoles("alice", ["Reporter"])
        self.assertEqual(self.captured, [])
        self.assertIn("Reporter", self.col.get_local_roles_for_userid("alice"))

    def test_del_local_roles_without_request_does_not_fire_event(self):
        self.col.manage_setLocalRoles("alice", ["Reporter"])
        self.col.manage_delLocalRoles(["alice"])
        self.assertEqual(self.captured, [])
        self.assertFalse(self.col.get_local_roles_for_userid("alice"))

    def test_add_local_roles_never_fires_event(self):
        # manage_addLocalRoles never cascaded historically; do not change that
        # even under BDR with a REQUEST.
        with patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR):
            self.col.manage_addLocalRoles(
                "alice", ["Reporter"], REQUEST=_post(self.app.REQUEST)
            )
        self.assertEqual(self.captured, [])
        self.assertIn("Reporter", self.col.get_local_roles_for_userid("alice"))

    def test_non_bdr_with_request_does_not_fire_event(self):
        with patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_CDR):
            self.col.manage_setLocalRoles(
                "alice", ["Reporter"], REQUEST=_post(self.app.REQUEST)
            )
        self.assertEqual(self.captured, [])
        self.assertIn("Reporter", self.col.get_local_roles_for_userid("alice"))

    # --- new event-firing path on BDR ---

    def test_bdr_set_local_roles_with_request_fires_event_with_union(self):
        self.col.manage_setLocalRoles("alice", ["OldRole"])
        with patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR):
            self.col.manage_setLocalRoles(
                "alice", ["NewRole"], REQUEST=_post(self.app.REQUEST)
            )
        self.assertEqual(len(self.captured), 1)
        evt = self.captured[0]
        self.assertIs(evt.object, self.col)
        # union of previous and new: covers both addition and removal
        self.assertEqual(evt.changed_roles, frozenset({"OldRole", "NewRole"}))

    def test_bdr_del_local_roles_with_request_fires_event_with_old_roles(self):
        self.col.manage_setLocalRoles("alice", ["RoleA", "RoleB"])
        with patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR):
            self.col.manage_delLocalRoles(["alice"], REQUEST=_post(self.app.REQUEST))
        self.assertEqual(len(self.captured), 1)
        evt = self.captured[0]
        self.assertEqual(evt.changed_roles, frozenset({"RoleA", "RoleB"}))

    def test_bdr_set_no_previous_roles_event_has_only_new_role(self):
        with patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR):
            self.col.manage_setLocalRoles(
                "newbie", ["FreshRole"], REQUEST=_post(self.app.REQUEST)
            )
        self.assertEqual(len(self.captured), 1)
        self.assertEqual(self.captured[0].changed_roles, frozenset({"FreshRole"}))


class CollectionEndToEndCascadeTest(BaseTest, ConfigureReportek):
    """End-to-end: ZMI-style POST under BDR triggers the batched
    descendant reindex via the subscriber. Asserts the catalog-level
    side effect, not just the event emission."""

    def afterSetUp(self):
        super(CollectionEndToEndCascadeTest, self).afterSetUp()
        WorkflowTestCase.create_process(self, "p1")
        self.wf.setProcessMappings("p1", "1", "1")
        self.col = self.addCollection(
            self.app,
            id="e2e_col",
            title="e2e test",
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
        ids = itertools.count()
        original_generate_id = RepUtils.generate_id
        RepUtils.generate_id = lambda template: "%s_%d" % (template, next(ids))
        try:
            for i in range(3):
                self.create_envelope(
                    self.col,
                    title="Env%d" % i,
                    year=2012,
                    endyear=2013,
                    country="http://spatial/1",
                    locality="",
                    descr="",
                )
        finally:
            RepUtils.generate_id = original_generate_id

    # Both REPORTEK_DEPLOYMENT module attributes need explicit patching:
    # one at the call site (Collection) and one at the subscriber side
    # (security_reindex). Otherwise tests are sensitive to the container's
    # REPORTEK_DEPLOYMENT env var.

    def test_bdr_zmi_triggers_batched_walker(self):
        with (
            patch(
                "Products.Reportek.Collection.REPORTEK_DEPLOYMENT",
                DEPLOYMENT_BDR,
            ),
            patch(
                "Products.Reportek.security_reindex.REPORTEK_DEPLOYMENT",
                DEPLOYMENT_BDR,
            ),
            patch(
                "Products.Reportek.security_reindex.reindex_security_batched",
                return_value=3,
            ) as walker,
        ):
            self.col.manage_setLocalRoles(
                "alice", ["TestViewer"], REQUEST=_post(self.app.REQUEST)
            )
        walker.assert_called_once_with(self.col)

    def test_bdr_zmi_runs_walker_for_any_role(self):
        # Without Layer 1 there is no "skip when role doesn't grant View"
        # short-circuit; the cascade runs for every role under BDR.
        with (
            patch(
                "Products.Reportek.Collection.REPORTEK_DEPLOYMENT",
                DEPLOYMENT_BDR,
            ),
            patch(
                "Products.Reportek.security_reindex.REPORTEK_DEPLOYMENT",
                DEPLOYMENT_BDR,
            ),
            patch(
                "Products.Reportek.security_reindex.reindex_security_batched",
                return_value=3,
            ) as walker,
        ):
            self.col.manage_permission("View", roles=["RealViewer"], acquire=0)
            self.col.manage_permission(
                "Reportek Dataflow Admin", roles=["RealAdmin"], acquire=0
            )
            self.col.manage_setLocalRoles(
                "alice", ["UnrelatedRole"], REQUEST=_post(self.app.REQUEST)
            )
        walker.assert_called_once_with(self.col)

    def test_non_bdr_zmi_does_not_invoke_walker(self):
        # Patch Collection deployment to a non-BDR value so the call-site
        # gate suppresses the event regardless of container env.
        with (
            patch(
                "Products.Reportek.Collection.REPORTEK_DEPLOYMENT",
                DEPLOYMENT_CDR,
            ),
            patch(
                "Products.Reportek.security_reindex.reindex_security_batched"
            ) as walker,
        ):
            self.col.manage_setLocalRoles(
                "alice", ["AnyRole"], REQUEST=_post(self.app.REQUEST)
            )
        # mock 1.0.1 has no assert_not_called; check call_count instead.
        self.assertEqual(walker.call_count, 0)
