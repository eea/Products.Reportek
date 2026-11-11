"""Tests for the Auditor/Client collections shown by ReportekEngine.get_ecr_content.

They cover which collections a user is offered through local roles, so that
changes to how the candidate collections are queried cannot show a user a
collection they hold no role on.
"""

import unittest
from unittest.mock import patch

from Products.Reportek.catalog import ReportekCatalog
from Products.Reportek.Collection import manage_addCollection
from Products.Reportek.constants import DEFAULT_CATALOG
from Products.Reportek.ReportekEngine import ReportekEngine

from .common import BaseTest, ConfigureReportek


def _add_collection(container, col_id, allow_collections=1):
    manage_addCollection(
        container.manage_addProduct["Reportek"],
        "Title %s" % col_id,
        "Desc",
        "2003",
        "2004",
        "",
        "http://rod.eionet.eu.int/spatial/2",
        "",
        ["http://rod.eionet.eu.int/obligations/8"],
        allow_collections=allow_collections,
        allow_envelopes=1,
        id=col_id,
    )
    return container[col_id]


def _grant(col, userid, roles):
    col.manage_setLocalRoles(userid, roles)
    col.reindexObject()


@unittest.skipUnless(
    hasattr(ReportekEngine, "_get_local_role_collection_brains"),
    "the local role collection lookups only exist on the BDR deployment",
)
class LocalRoleCollectionsTest(BaseTest, ConfigureReportek):
    def afterSetUp(self):
        super(LocalRoleCollectionsTest, self).afterSetUp()
        self.createStandardCatalog()
        self.catalog = getattr(self.app, DEFAULT_CATALOG)
        group = _add_collection(self.app, "grp")
        self.co1 = _add_collection(group, "co1")
        self.co2 = _add_collection(group, "co2")
        self.co3 = _add_collection(group, "co3")
        self.deep = _add_collection(self.co1, "deep")
        for col in (group, self.co1, self.co2, self.co3, self.deep):
            col.reindexObject()

    def _lookup(self, username):
        engine = self.engine
        brains = engine._get_local_role_collection_brains(username, self.catalog)
        return (
            sorted(c.getId() for c in engine._get_auditor_collections(username, brains)),
            sorted(c.getId() for c in engine._get_client_collections(username, brains)),
        )

    def test_user_gets_only_collections_with_their_own_roles(self):
        _grant(self.co1, "alice", ["ClientFG"])
        _grant(self.co2, "bob", ["ClientODS"])
        _grant(self.co3, "alice", ["Auditor"])
        self.assertEqual(self._lookup("alice"), (["co3"], ["co1"]))
        self.assertEqual(self._lookup("bob"), ([], ["co2"]))

    def test_user_does_not_get_collections_where_only_others_have_roles(self):
        _grant(self.co1, "alice", ["ClientFG"])
        _grant(self.co1, "bob", ["ClientODS"])
        _grant(self.co2, "bob", ["Auditor"])
        self.assertEqual(self._lookup("alice"), ([], ["co1"]))
        self.assertEqual(self._lookup("carol"), ([], []))

    def test_user_without_roles_gets_nothing(self):
        _grant(self.co1, "alice", ["ClientFG"])
        for username in ("nobody", "Anonymous User", "", None):
            self.assertEqual(self._lookup(username), ([], []), repr(username))

    def test_roles_outside_the_bdr_roles_are_ignored(self):
        _grant(self.co1, "alice", ["Reporter", "Owner"])
        self.assertEqual(self._lookup("alice"), ([], []))

    def test_only_top_level_company_collections_are_listed(self):
        _grant(self.deep, "alice", ["ClientFG"])
        _grant(self.co2, "alice", ["ClientFG"])
        self.assertEqual(self._lookup("alice"), ([], ["co2"]))

    def test_revoked_roles_are_no_longer_offered(self):
        _grant(self.co1, "alice", ["ClientFG"])
        self.assertEqual(self._lookup("alice"), ([], ["co1"]))
        self.co1.manage_delLocalRoles(["alice"])
        self.co1.reindexObject()
        self.assertEqual(self._lookup("alice"), ([], []))

    def test_candidates_are_limited_to_collections_listing_the_user(self):
        _grant(self.co1, "alice", ["ClientFG"])
        _grant(self.co2, "bob", ["ClientFG"])
        brains = self.engine._get_local_role_collection_brains("alice", self.catalog)
        self.assertEqual(sorted(b.getPath().rsplit("/", 1)[-1] for b in brains), ["co1"])

    def test_query_is_scoped_to_the_user_in_the_catalog(self):
        _grant(self.co1, "alice", ["ClientFG"])
        original = ReportekCatalog.searchResults
        with patch.object(
            ReportekCatalog, "searchResults", autospec=True, side_effect=original
        ) as search:
            self.engine._get_local_role_collection_brains("alice", self.catalog)
        calls = [c.kwargs for c in search.call_args_list]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["meta_type"], "Report Collection")
        self.assertEqual(calls[0].get("local_defined_users"), ["alice"])
        self.assertIn("ClientFG", calls[0]["local_unique_roles"])
        self.assertIn("Auditor", calls[0]["local_unique_roles"])
