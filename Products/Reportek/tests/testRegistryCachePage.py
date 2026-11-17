"""The Registry cache tab of the engine: it renders, and tells what it should."""

import os
from unittest.mock import patch

from AccessControl import SpecialUsers
from AccessControl.SecurityManagement import newSecurityManager, noSecurityManager
from Testing import ZopeTestCase

from Products.Reportek import RegistryCache
from Products.Reportek.RegistryCache import SharedCache
from Products.Reportek.tests.testRegistryCache import Clock, FakeValkey

from .common import BaseTest

ZopeTestCase.installProduct("Reportek")


class RegistryCachePageTest(BaseTest):
    def afterSetUp(self):
        BaseTest.afterSetUp(self)
        self.createStandardDependencies()
        newSecurityManager(None, SpecialUsers.system)
        self.addCleanup(noSecurityManager)

    def test_the_page_says_that_the_cache_is_off(self):
        with patch.dict(
            os.environ, {"SESSION_SECRET": "dummy", "REGISTRY_SHARED_CACHE": ""}
        ):
            html = self.engine.registry_cache()
        self.assertIn("Registry cache", html)
        self.assertIn("REGISTRY_SHARED_CACHE is not set", html)
        self.assertNotIn("Entries in Valkey", html)

    def test_the_page_shows_the_entries_and_the_valkey(self):
        valkey = FakeValkey(Clock())
        cache = SharedCache(valkey)
        with patch.dict(os.environ, {"SESSION_SECRET": "dummy"}):
            cache.fetch("paths", ["a"], 300, lambda: ({"paths": []}, True))
            with patch.object(RegistryCache, "shared_cache", cache):
                html = self.engine.registry_cache()
        self.assertIn("Entries in Valkey", html)
        self.assertIn("volatile-lru", html)
        self.assertIn("128.0 MB", html)
        self.assertIn("paths", html)
        # a dict method is not a value of the page ("keys" was one)
        self.assertNotIn("dict_", html)
        self.assertRegex(html, r"Keys in total[^<]*</th>\s*<td>1</td>")

    def test_the_page_renders_with_a_valkey_that_is_down(self):
        valkey = FakeValkey(Clock())
        valkey.error = ConnectionError("down")
        cache = SharedCache(valkey)
        with patch.dict(os.environ, {"SESSION_SECRET": "dummy"}), patch.object(
            RegistryCache, "shared_cache", cache
        ):
            html = self.engine.registry_cache()
        self.assertIn("no (<span>ConnectionError</span>)", html)

    def test_the_tab_is_in_the_menu(self):
        labels = [option["label"] for option in self.engine.manage_options]
        self.assertIn("Registry cache", labels)
