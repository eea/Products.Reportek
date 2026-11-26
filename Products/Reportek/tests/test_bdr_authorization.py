"""Registry paths grant access to a collection and what is inside it."""

import unittest
from unittest.mock import patch

from Products.Reportek.BdrAuthorizationMiddleware import (
    BdrAuthorizationMiddleware,
    is_within,
)


class IsWithinTest(unittest.TestCase):
    def test_the_collection_and_what_is_inside(self):
        self.assertTrue(is_within("fgases/de/10002", "fgases/de/10002"))
        self.assertTrue(is_within("fgases/de/10002/envabc", "fgases/de/10002"))
        self.assertTrue(
            is_within("fgases/de/10002/envabc/data.xml", "fgases/de/10002")
        )

    def test_not_other_collections(self):
        self.assertFalse(is_within("fgases/de/100021", "fgases/de/10002"))
        self.assertFalse(is_within("fgases/de/100021/envabc", "fgases/de/10002"))
        self.assertFalse(is_within("fgases/cz/97012", "fgases/cz/9701"))

    def test_not_the_parent_nor_other_places(self):
        self.assertFalse(is_within("fgases/de", "fgases/de/10002"))
        self.assertFalse(is_within("ods/de/10002", "fgases/de/10002"))
        self.assertFalse(is_within("x/fgases/de/10002", "fgases/de/10002"))

    def test_leading_and_trailing_slashes(self):
        self.assertTrue(is_within("/fgases/de/10002/env", "fgases/de/10002/"))
        self.assertFalse(is_within("/fgases/de/100021", "/fgases/de/10002"))

    def test_missing_paths_cover_nothing(self):
        for granted in (None, "", "/"):
            self.assertFalse(is_within("fgases/de/10002", granted))
        self.assertFalse(is_within("", "fgases/de/10002"))


class AuthorizedUserTest(unittest.TestCase):
    def setUp(self):
        self.middleware = BdrAuthorizationMiddleware("http://middleware")
        paths = {
            "paths": ["fgases/de/10002"],
            # a path the registry data could not build is None
            "prev_paths": [None, "fgases/at/10002"],
            "audit_paths": ["fgases/cz/16229/env1"],
        }
        patcher = patch.object(
            BdrAuthorizationMiddleware, "getUserCollectionPaths", return_value=paths
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def authorized(self, path):
        return self.middleware.authorizedUser("reporter", path)

    def test_own_collection_is_rw(self):
        self.assertEqual(self.authorized("fgases/de/10002"), "RW")
        self.assertEqual(self.authorized("fgases/de/10002/env/data.xml"), "RW")

    def test_other_collection_is_not(self):
        for path in ("fgases/de/100021", "fgases/de/100023/env/data.xml"):
            self.assertFalse(self.authorized(path), path)

    def test_previous_country_is_ro(self):
        self.assertEqual(self.authorized("fgases/at/10002/env"), "RO")
        self.assertFalse(self.authorized("fgases/at/100026"))

    def test_audit_is_for_that_envelope_only(self):
        self.assertEqual(self.authorized("fgases/cz/16229/env1/data.xml"), "AUDIT")
        self.assertFalse(self.authorized("fgases/cz/16229/env10"))
        self.assertFalse(self.authorized("fgases/cz/16229"))

    def test_locked_collection(self):
        self.middleware.lockDownCollection("fgases/de/10002", "admin")
        self.assertFalse(self.authorized("fgases/de/10002"))
