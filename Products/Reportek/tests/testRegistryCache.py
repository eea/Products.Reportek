"""The answers of the registry that the pods share through Valkey.

The answers decide what a user can access: they are kept as long as the memory
of a pod keeps them, they are signed, a failure is never stored and a Valkey
that does not work is a miss. Valkey, the clock and the answers are dummy.
"""

import os
import unittest
from unittest.mock import patch

import requests
from plone.memoize import ram

from Products.Reportek import RegistryCache
from Products.Reportek.BdrAuthorizationMiddleware import BdrAuthorizationMiddleware
from Products.Reportek.RegistryCache import MISS, SharedCache
from Products.Reportek.RegistryManagement import (
    BDRRegistryAPI,
    FGASRegistryAPI,
    LookupStats,
    RegistryUnavailable,
)

REGISTRY_GET = "Products.Reportek.RegistryManagement.requests.get"
SECRET = {"SESSION_SECRET": "dummy-secret"}


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeValkey:
    """The few commands that the cache uses, with expiry and errors."""

    def __init__(self, clock):
        self.clock = clock
        self.data = {}
        self.error = None
        self.latency = 0
        self.calls = []

    def _check(self, command):
        self.calls.append(command)
        if self.error:
            raise self.error

    def _alive(self, key):
        entry = self.data.get(key)
        if entry and (entry[1] is None or entry[1] > self.clock.now):
            return entry
        self.data.pop(key, None)
        return None

    def get(self, key):
        self._check("get")
        self.clock.now += self.latency
        entry = self._alive(key)
        return entry[0] if entry else None

    def set(self, key, value, nx=False, ex=None):
        self._check("set")
        if nx and self._alive(key):
            return None
        if isinstance(value, str):
            value = value.encode()
        self.data[key] = (value, self.clock.now + ex if ex else None)
        return True

    def delete(self, key):
        self._check("delete")
        self.data.pop(key, None)

    def eval(self, script, numkeys, key, token):
        self._check("eval")
        assert script == RegistryCache.RELEASE_LOCK
        entry = self._alive(key)
        if entry and entry[0] == token.encode():
            del self.data[key]
            return 1
        return 0


def answer(status_code=200, payload=None):
    from unittest.mock import Mock

    response = Mock()
    response.status_code = status_code
    response.json = Mock(return_value=payload)
    return response


class SharedCacheCase(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.valkey = FakeValkey(self.clock)
        env = patch.dict(os.environ, SECRET)
        env.start()
        self.addCleanup(env.stop)
        for name, replacement in (("time", self.clock), ("sleep", self.clock.sleep)):
            patcher = patch.object(RegistryCache, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.pod_a = SharedCache(self.valkey)
        self.pod_b = SharedCache(self.valkey)
        self.loads = []

    def load(self, value="answer", stored=True):
        def load():
            self.loads.append(value)
            return value, stored

        return load

    def fetch(self, pod=None, parts=("a", 1), ttl=300, **kwargs):
        return (pod or self.pod_a).fetch("paths", list(parts), ttl, self.load(**kwargs))


class FetchTest(SharedCacheCase):
    def test_a_pod_takes_the_answer_that_another_pod_got(self):
        self.assertEqual(self.fetch(self.pod_a), "answer")
        self.assertEqual(self.fetch(self.pod_b, value="other"), "answer")
        self.assertEqual(self.loads, ["answer"])

    def test_the_answers_are_json_values(self):
        value = {"paths": ["a/b"], "prev_paths": [None], "audit_paths": []}
        self.assertEqual(self.fetch(self.pod_a, value=value), value)
        self.assertEqual(self.fetch(self.pod_b), value)

    def test_another_user_or_window_is_another_answer(self):
        self.fetch(parts=("paths", "u1", 5))
        self.fetch(parts=("paths", "u2", 5), value="u2")
        self.fetch(parts=("paths", "u1", 6), value="next window")
        self.assertEqual(self.loads, ["answer", "u2", "next window"])
        self.assertEqual(self.fetch(parts=("paths", "u2", 5)), "u2")

    def test_the_key_does_not_hold_the_user(self):
        self.fetch(parts=("paths", "someone@example.org", 5))
        for key in self.valkey.data:
            self.assertNotIn("someone", key)
            self.assertTrue(key.startswith("reportek:regcache:v1:paths:"))

    def test_an_answer_expires_with_its_window(self):
        self.fetch(ttl=300)
        self.clock.now += 301
        self.assertEqual(self.fetch(value="new", ttl=300), "new")
        self.assertEqual(self.loads, ["answer", "new"])

    def test_an_entry_older_than_the_window_is_not_used_even_if_valkey_keeps_it(self):
        self.fetch(ttl=300)
        # Valkey did not expire it (a wrong TTL, a clock): the age says no
        for key, (value, _) in list(self.valkey.data.items()):
            self.valkey.data[key] = (value, None)
        self.clock.now += 301
        self.assertEqual(self.fetch(value="new", ttl=300), "new")

    def test_the_registry_that_does_not_answer_is_not_stored(self):
        def down():
            raise RegistryUnavailable("down")

        with self.assertRaises(RegistryUnavailable):
            self.pod_a.fetch("paths", ["a"], 300, down)
        self.assertEqual([k for k in self.valkey.data if not k.endswith(":lock")], [])
        # the lock is released, the next pod asks without waiting
        self.assertEqual(self.valkey.data, {})
        self.assertEqual(self.fetch(self.pod_b, parts=("a",)), "answer")

    def test_an_answer_that_is_not_the_one_of_the_registry_is_not_stored(self):
        self.assertEqual(self.fetch(stored=False), "answer")
        self.assertEqual(self.valkey.data, {})
        self.assertEqual(self.fetch(self.pod_b, value="again"), "again")

    def test_it_is_off_without_the_setting(self):
        with patch.dict(os.environ, SECRET, clear=True):
            cache = SharedCache()
            self.assertFalse(cache.enabled())
            self.assertEqual(cache.fetch("paths", ["a"], 300, self.load()), "answer")

    def test_it_is_off_without_a_secret_to_sign_with(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(SharedCache(self.valkey).enabled())
            self.assertEqual(
                SharedCache(self.valkey).fetch("paths", ["a"], 300, self.load()),
                "answer",
            )
        self.assertEqual(self.valkey.data, {})

    def test_it_is_on_with_the_setting_and_an_address(self):
        env = {**SECRET, "REGISTRY_SHARED_CACHE": "1", "REDIS_URL": "redis://x:1/0"}
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(SharedCache().enabled())
        env.pop("REDIS_URL")
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(SharedCache().enabled())


class TrustTest(SharedCacheCase):
    def stored_key(self):
        return next(k for k in self.valkey.data if not k.endswith(":lock"))

    def tamper(self, change):
        self.fetch()
        key = self.stored_key()
        value, ttl = self.valkey.data[key]
        self.valkey.data[key] = (change(value), ttl)

    def test_a_changed_entry_is_a_miss(self):
        self.tamper(lambda v: v[:-1] + bytes([v[-1] ^ 1]))
        self.assertEqual(self.fetch(value="from the registry"), "from the registry")

    def test_an_entry_of_another_key_is_a_miss(self):
        self.fetch(parts=("paths", "u1", 5))
        (key,) = [k for k in self.valkey.data if not k.endswith(":lock")]
        value, ttl = self.valkey.data[key]
        other = self.pod_a._key("paths", ["paths", "u2", 5])
        self.valkey.data[other] = (value, ttl)
        self.assertEqual(self.fetch(parts=("paths", "u2", 5), value="u2"), "u2")

    def test_an_entry_signed_with_another_secret_is_a_miss(self):
        self.fetch()
        with patch.dict(os.environ, {"SESSION_SECRET": "another"}):
            self.assertEqual(self.fetch(self.pod_b, value="mine"), "mine")

    def test_garbage_is_a_miss(self):
        for garbage in (b"", b"1", b"2" + b"x" * 80, b"1" + b"x" * 80, b"{}"):
            self.valkey.data.clear()
            self.fetch()
            self.valkey.data[self.stored_key()] = (garbage, None)
            self.assertEqual(self.fetch(value="fresh"), "fresh", garbage)


class OutageTest(SharedCacheCase):
    def test_a_valkey_that_fails_is_a_miss_and_the_registry_is_asked(self):
        self.valkey.error = ConnectionError("down")
        self.assertEqual(self.fetch(), "answer")
        self.assertEqual(self.loads, ["answer"])

    def test_valkey_is_left_alone_after_a_few_errors_and_tried_again_later(self):
        self.valkey.error = ConnectionError("down")
        for i in range(RegistryCache.BREAKER_ERRORS):
            self.fetch(parts=("u", i))
        calls = len(self.valkey.calls)
        for i in range(10):
            self.fetch(parts=("v", i))
        self.assertEqual(len(self.valkey.calls), calls)
        self.valkey.error = None
        self.clock.now += RegistryCache.BREAKER_SECONDS + 1
        self.fetch(parts=("w", 1))
        self.assertGreater(len(self.valkey.calls), calls)
        # it works again: the next pod finds the answer
        self.assertEqual(self.fetch(self.pod_b, parts=("w", 1), value="no"), "answer")

    def test_one_error_then_it_works_does_not_leave_valkey_alone(self):
        self.valkey.error = ConnectionError("blip")
        self.fetch(parts=("a", 1))
        self.valkey.error = None
        self.fetch(parts=("a", 2))
        self.assertEqual(self.fetch(self.pod_b, parts=("a", 2), value="no"), "answer")

    def test_a_failed_lookup_in_valkey_is_one_error_not_one_per_command(self):
        self.valkey.error = ConnectionError("down")
        self.fetch()
        self.assertEqual(self.valkey.calls, ["get"])

    def test_an_error_while_storing_does_not_fail_the_lookup(self):
        original = self.valkey.set
        calls = []

        def set_(key, value, nx=False, ex=None):
            calls.append(nx)
            if not nx:
                raise TimeoutError("slow")
            return original(key, value, nx=nx, ex=ex)

        self.valkey.set = set_
        self.assertEqual(self.fetch(), "answer")


class LockTest(SharedCacheCase):
    def test_a_pod_waits_for_the_answer_of_the_pod_that_asks_the_registry(self):
        key = self.pod_a._key("paths", ["a", 1])
        self.valkey.set(key + ":lock", "other pod", nx=True, ex=10)
        asked = []
        original_sleep = self.clock.sleep

        def sleep(seconds):
            original_sleep(seconds)
            if len(asked) == 0 and self.clock.now > 1000.2:
                asked.append(1)
                # the other pod stored its answer
                self.pod_b._set("paths", key, "from the other pod", 300, self.clock.now)

        with patch.object(RegistryCache, "sleep", sleep):
            self.assertEqual(self.fetch(self.pod_a), "from the other pod")
        self.assertEqual(self.loads, [])

    def test_a_pod_does_not_wait_for_ever_for_a_lock_that_is_not_released(self):
        key = self.pod_a._key("paths", ["a", 1])
        self.valkey.set(key + ":lock", "dead pod", nx=True, ex=10)
        start = self.clock.now
        self.assertEqual(self.fetch(self.pod_a), "answer")
        self.assertLessEqual(self.clock.now - start, RegistryCache.WAIT_SECONDS + 0.2)
        # the lock of the dead pod is not ours to release
        self.assertIn(key + ":lock", self.valkey.data)

    def test_the_lock_is_released_after_the_registry_answered(self):
        self.fetch()
        self.assertEqual([k for k in self.valkey.data if k.endswith(":lock")], [])


class HardeningTest(SharedCacheCase):
    def test_a_value_that_is_not_json_does_not_fail_the_lookup(self):
        self.assertEqual(self.fetch(value={1, 2}), {1, 2})
        self.assertEqual(self.valkey.data, {})

    def test_the_age_counts_from_the_moment_the_registry_was_asked(self):
        def slow_registry():
            self.clock.now += 200
            return "answer", True

        self.pod_a.fetch("paths", ["a"], 300, slow_registry)
        # the answer is 200 s old when it is stored: 101 s later it is 301 s old
        # (Valkey keeps the entry for 300 s from the store, the age says no)
        self.clock.now += 101
        self.assertEqual(self.fetch(self.pod_b, parts=("a",), value="new"), "new")

    def test_the_wait_for_another_pod_is_bounded_by_the_time_not_by_the_steps(self):
        key = self.pod_a._key("paths", ["a", 1])
        self.valkey.set(key + ":lock", "other pod", nx=True, ex=10)
        self.valkey.latency = 0.09  # slow, but not an error
        start = self.clock.now
        self.assertEqual(self.fetch(self.pod_a), "answer")
        elapsed = self.clock.now - start
        self.assertLess(elapsed, RegistryCache.WAIT_SECONDS + 0.5, elapsed)

    def test_a_lock_that_is_not_ours_is_not_released(self):
        key = self.pod_a._key("paths", ["a", 1])

        def registry_slower_than_the_lock():
            self.clock.now += RegistryCache.LOCK_SECONDS + 1
            # the lock expired, another pod holds it now
            self.valkey.set(key + ":lock", "another pod", nx=True, ex=10)
            return "answer", True

        self.pod_a.fetch("paths", ["a", 1], 300, registry_slower_than_the_lock)
        self.assertEqual(self.valkey.data[key + ":lock"][0], b"another pod")

    def test_it_says_if_valkey_has_the_answer(self):
        self.assertFalse(self.pod_a.has("paths", ["a", 1], 300))
        self.fetch()
        self.assertTrue(self.pod_b.has("paths", ["a", 1], 300))
        self.assertFalse(self.pod_b.has("paths", ["a", 2], 300))
        self.clock.now += 301
        self.assertFalse(self.pod_b.has("paths", ["a", 1], 300))

    def test_a_valkey_that_fails_has_no_answers(self):
        self.fetch()
        self.valkey.error = ConnectionError("down")
        self.assertFalse(self.pod_b.has("paths", ["a", 1], 300))
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(SharedCache(self.valkey).has("paths", ["a", 1], 300))


class RegistryLookupsTest(unittest.TestCase):
    """The lookups of the registry through the shared cache, two pods."""

    def setUp(self):
        ram.global_cache.invalidateAll()
        self.addCleanup(ram.global_cache.invalidateAll)
        env = patch.dict(os.environ, SECRET)
        env.start()
        self.addCleanup(env.stop)
        self.clock = Clock()
        self.valkey = FakeValkey(self.clock)
        patcher = patch.object(RegistryCache, "time", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        shared = SharedCache(self.valkey)
        patcher = patch.object(RegistryCache, "shared_cache", shared)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stats = LookupStats()
        shared.stats = self.stats
        self.middleware = BdrAuthorizationMiddleware("http://middleware")
        self.middleware.FGASRegistryAPI = FGASRegistryAPI(
            "FGAS", "http://registry", "token"
        )
        self.bdr = BDRRegistryAPI("BDR", "http://bdr")
        self.bdr.bdr_registry_token = "token"
        self.companies = [
            {
                "company_id": 1,
                "country": "RO",
                "domain": "FGAS",
                "collection_id": "fgas30001",
            }
        ]

    def paths(self, user="a"):
        return self.middleware.getUserCollectionPaths(
            "e1", userdata={"username": user, "ecas_id": "e1"}, recheck_interval=300
        )

    def another_pod(self):
        ram.global_cache.invalidateAll()

    @patch(REGISTRY_GET)
    def test_the_paths_are_asked_once_for_all_the_pods(self, get):
        get.return_value = answer(200, self.companies)
        first = self.paths()
        self.another_pod()
        self.assertEqual(self.paths(), first)
        self.assertTrue(first["paths"])
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_the_details_of_the_user_are_asked_once_for_all_the_pods(self, get):
        details = [{"has_reporting_folder": True, "reporting_folder": "ods/xx/c1"}]
        get.return_value = answer(200, details)
        self.assertEqual(self.bdr.get_user_details("a"), details)
        self.another_pod()
        self.assertEqual(self.bdr.get_user_details("a"), details)
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_another_user_is_asked(self, get):
        get.return_value = answer(200, self.companies)
        self.paths("a")
        self.another_pod()
        self.paths("b")
        self.assertEqual(get.call_count, 2)

    @patch(REGISTRY_GET)
    def test_a_registry_that_is_down_gives_no_access_and_nothing_is_stored(self, get):
        get.side_effect = requests.exceptions.ConnectTimeout("down")
        empty = {"paths": [], "prev_paths": [], "audit_paths": []}
        self.assertEqual(self.paths(), empty)
        self.assertEqual(self.bdr.get_user_details("a"), [])
        self.assertEqual([k for k in self.valkey.data if not k.endswith(":lock")], [])
        get.side_effect = None
        get.return_value = answer(200, self.companies)
        self.assertTrue(self.paths()["paths"])

    @patch(REGISTRY_GET)
    def test_an_answer_that_is_not_ok_is_not_shared(self, get):
        get.return_value = answer(401)
        self.assertEqual(self.bdr.get_user_details("a"), [])
        self.assertEqual(self.paths()["paths"], [])
        self.assertEqual([k for k in self.valkey.data if not k.endswith(":lock")], [])

    @patch(REGISTRY_GET)
    def test_a_valkey_that_is_down_leaves_the_lookups_as_they_were(self, get):
        self.valkey.error = ConnectionError("down")
        get.return_value = answer(200, self.companies)
        self.assertTrue(self.paths()["paths"])
        self.another_pod()
        self.assertTrue(self.paths()["paths"])
        self.assertEqual(get.call_count, 2)

    @patch(REGISTRY_GET)
    def test_the_counters_tell_what_valkey_and_the_registry_did(self, get):
        get.return_value = answer(200, self.companies)
        self.paths()
        self.another_pod()
        self.paths()
        stats = self.stats.snapshot()
        self.assertEqual(stats["paths (valkey)"]["lookup"], 2)
        self.assertEqual(stats["paths (valkey)"]["miss"], 1)
        # the miss of the registry is counted where the registry is asked
        self.assertEqual(get.call_count, 1)

    @patch(REGISTRY_GET)
    def test_nothing_is_prefetched_for_what_valkey_has(self, get):
        get.return_value = answer(200, self.companies)
        userdata = {"username": "a", "ecas_id": "e1"}
        self.assertIsNotNone(self.middleware.paths_request("e1", userdata=userdata))
        self.assertIsNotNone(self.bdr.user_details_request("a"))
        self.paths()
        self.bdr.get_user_details("a")
        self.another_pod()
        # this pod does not have them, Valkey does: no request is sent early
        self.assertIsNone(self.middleware.paths_request("e1", userdata=userdata))
        self.assertIsNone(self.bdr.user_details_request("a"))

    @patch(REGISTRY_GET)
    def test_a_valkey_that_fails_still_prefetches(self, get):
        self.valkey.error = ConnectionError("down")
        userdata = {"username": "a", "ecas_id": "e1"}
        self.assertIsNotNone(self.middleware.paths_request("e1", userdata=userdata))
        self.assertIsNotNone(self.bdr.user_details_request("a"))
