import unittest

from AccessControl.ZopeGuards import guarded_getattr
from zope.publisher.browser import TestRequest
from ZPublisher.pubevents import PubStart

from Products.Reportek.session import (
    ZopeBeakerSessionWrapper,
    extract_beaker_session,
)


class MockBeakerSession(dict):
    def __init__(self, *args, **kwargs):
        super(MockBeakerSession, self).__init__(*args, **kwargs)
        self.id = "mock_id_123"
        self.invalidated = False

    def invalidate(self):
        self.invalidated = True


class TestZopeBeakerSessionWrapper(unittest.TestCase):
    def setUp(self):
        self.beaker = MockBeakerSession({"a": 1, "b": 2})
        self.wrapper = ZopeBeakerSessionWrapper(self.beaker)

    def test_get(self):
        self.assertEqual(self.wrapper.get("a"), 1)
        self.assertIsNone(self.wrapper.get("nonexistent"))
        self.assertEqual(self.wrapper.get("nonexistent", "default"), "default")

    def test_set(self):
        self.wrapper.set("c", 3)
        self.assertEqual(self.beaker["c"], 3)
        self.assertEqual(self.wrapper["c"], 3)

    def test_delete(self):
        self.wrapper.delete("a")
        self.assertNotIn("a", self.beaker)
        self.assertNotIn("a", self.wrapper)

    def test_has_key(self):
        self.assertTrue(self.wrapper.has_key("a"))
        self.assertFalse(self.wrapper.has_key("nonexistent"))

    def test_getId(self):
        self.assertEqual(self.wrapper.getId(), "mock_id_123")

    def test_invalidate(self):
        self.wrapper.invalidate()
        self.assertTrue(self.beaker.invalidated)

    def test_dictionary_methods(self):
        self.assertEqual(list(self.wrapper.keys()), ["a", "b"])
        self.assertEqual(list(self.wrapper.values()), [1, 2])
        self.assertEqual(list(self.wrapper.items()), [("a", 1), ("b", 2)])

        self.wrapper.update({"d": 4})
        self.assertEqual(self.beaker["d"], 4)

        self.wrapper.clear()
        self.assertEqual(len(self.beaker), 0)

    def test_magic_methods(self):
        self.wrapper["e"] = 5
        self.assertEqual(self.beaker["e"], 5)

        self.assertEqual(self.wrapper["e"], 5)

        self.assertTrue("e" in self.wrapper)

        del self.wrapper["e"]
        self.assertNotIn("e", self.beaker)

    def test_security_access(self):
        # We simulate RestrictedPython's guarded getattr to ensure methods are accessible
        self.assertTrue(guarded_getattr(self.wrapper, "set"))
        self.assertTrue(guarded_getattr(self.wrapper, "get"))
        self.assertTrue(guarded_getattr(self.wrapper, "delete"))
        self.assertTrue(guarded_getattr(self.wrapper, "keys"))
        self.assertTrue(guarded_getattr(self.wrapper, "invalidate"))

        # Ensure that private attributes are NOT accessible via guarded_getattr
        with self.assertRaises(Exception) as context:
            guarded_getattr(self.wrapper, "_beaker_session")

        # In RestrictedPython, accessing _ attributes throws an Unauthorized error
        self.assertEqual(type(context.exception).__name__, "Unauthorized")


class MockRequest:
    def __init__(self, environ):
        self.environ = environ


class TestExtractBeakerSession(unittest.TestCase):
    def test_extract_beaker_session(self):
        # Create a mock request and event
        request = MockRequest(
            environ={"beaker.session": MockBeakerSession({"foo": "bar"})}
        )
        event = PubStart(request)

        # Call the handler
        extract_beaker_session(event)

        # Verify the session is set and wrapped
        self.assertTrue(hasattr(request, "SESSION"))
        self.assertIsInstance(request.SESSION, ZopeBeakerSessionWrapper)
        self.assertEqual(request.SESSION.get("foo"), "bar")

    def test_extract_no_beaker_session(self):
        request = MockRequest(environ={})
        event = PubStart(request)

        extract_beaker_session(event)

        self.assertFalse(hasattr(request, "SESSION"))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(
        unittest.TestLoader().loadTestsFromTestCase(
            TestZopeBeakerSessionWrapper
        )
    )
    suite.addTest(
        unittest.TestLoader().loadTestsFromTestCase(TestExtractBeakerSession)
    )
    return suite
