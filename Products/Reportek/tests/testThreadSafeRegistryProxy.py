# -*- coding: utf-8 -*-
import unittest

from mock import Mock, patch

from plone.registry.interfaces import IRegistry
from Products.Reportek.RepUtils import ThreadSafeRegistryProxy


class TestThreadSafeRegistryProxy(unittest.TestCase):
    def _make_proxy(self, registry=None, fallback=None):
        """Proxy whose _get_real_registry returns `registry`."""
        if registry is None:
            registry = Mock()
        proxy = ThreadSafeRegistryProxy(fallback or Mock())
        proxy._get_real_registry = Mock(return_value=registry)
        return proxy, registry

    # --- Interface compliance ---

    def test_implements_iregistry(self):
        self.assertTrue(IRegistry.implementedBy(ThreadSafeRegistryProxy))

    def test_provides_iregistry(self):
        self.assertTrue(IRegistry.providedBy(ThreadSafeRegistryProxy(Mock())))

    # --- Delegation of the IRegistry contract ---

    def test_records_delegates(self):
        proxy, reg = self._make_proxy()
        reg.records = {"a.b": "record"}
        self.assertEqual(proxy.records, {"a.b": "record"})

    def test_getitem_delegates(self):
        proxy, reg = self._make_proxy()
        reg.__getitem__ = Mock(return_value="value")
        self.assertEqual(proxy["a.b"], "value")
        reg.__getitem__.assert_called_once_with("a.b")

    def test_setitem_delegates(self):
        proxy, reg = self._make_proxy()
        reg.__setitem__ = Mock()
        proxy["a.b"] = "value"
        reg.__setitem__.assert_called_once_with("a.b", "value")

    def test_contains_delegates(self):
        proxy, reg = self._make_proxy()
        reg.__contains__ = Mock(return_value=True)
        self.assertIn("a.b", proxy)
        reg.__contains__.assert_called_once_with("a.b")

    def test_get_delegates_with_default(self):
        proxy, reg = self._make_proxy()
        reg.get = Mock(return_value="fallback")
        self.assertEqual(proxy.get("a.b", "fallback"), "fallback")
        reg.get.assert_called_once_with("a.b", "fallback")

    def test_for_interface_forwards_defaults(self):
        proxy, reg = self._make_proxy()
        reg.forInterface = Mock(return_value="proxy-obj")
        iface = Mock()
        self.assertEqual(proxy.forInterface(iface), "proxy-obj")
        reg.forInterface.assert_called_once_with(
            iface, check=True, omit=(), prefix=None
        )

    def test_register_interface_forwards_defaults(self):
        proxy, reg = self._make_proxy()
        reg.registerInterface = Mock()
        iface = Mock()
        proxy.registerInterface(iface)
        reg.registerInterface.assert_called_once_with(iface, omit=(), prefix=None)

    def test_unknown_attribute_delegates(self):
        """plone.registry API beyond IRegistry still reaches the real object."""
        proxy, reg = self._make_proxy()
        reg.collectionOfInterface = Mock(return_value="collection")
        self.assertEqual(proxy.collectionOfInterface(), "collection")

    def test_private_attribute_is_not_delegated(self):
        """Guards against recursion on a partially constructed proxy."""
        proxy, _reg = self._make_proxy()
        with self.assertRaises(AttributeError):
            proxy._not_a_real_attribute

    # --- Resolution ---

    @patch("zope.globalrequest.getRequest")
    def test_resolves_via_request_parents(self, get_request):
        registry = Mock()
        published = Mock()
        published.portal_registry = registry
        request = {"PARENTS": [published]}
        get_request.return_value = request
        proxy = ThreadSafeRegistryProxy(Mock())
        self.assertIs(proxy._get_real_registry(), registry)

    @patch("zope.globalrequest.getRequest")
    def test_falls_back_when_no_request(self, get_request):
        """Startup and console scripts must keep working, not raise."""
        get_request.return_value = None
        fallback = Mock()
        proxy = ThreadSafeRegistryProxy(fallback)
        self.assertIs(proxy._get_real_registry(), fallback)

    @patch("zope.globalrequest.getRequest")
    def test_falls_back_when_request_has_no_parents(self, get_request):
        get_request.return_value = {"PARENTS": []}
        fallback = Mock()
        proxy = ThreadSafeRegistryProxy(fallback)
        self.assertIs(proxy._get_real_registry(), fallback)

    @patch("zope.globalrequest.getRequest")
    def test_falls_back_when_root_has_no_registry(self, get_request):
        published = Mock(spec=[])  # no portal_registry attribute
        get_request.return_value = {"PARENTS": [published]}
        fallback = Mock()
        proxy = ThreadSafeRegistryProxy(fallback)
        self.assertIs(proxy._get_real_registry(), fallback)

    @patch("zope.globalrequest.getRequest")
    def test_resolution_is_not_cached(self, get_request):
        """Each call resolves afresh, so a later request sees its own object."""
        first, second = Mock(), Mock()
        published = Mock()
        published.portal_registry = first
        get_request.return_value = {"PARENTS": [published]}
        proxy = ThreadSafeRegistryProxy(Mock())
        self.assertIs(proxy._get_real_registry(), first)
        published.portal_registry = second
        self.assertIs(proxy._get_real_registry(), second)

    # --- Statelessness ---

    def test_proxy_holds_no_persistent_state(self):
        proxy = ThreadSafeRegistryProxy(Mock())
        self.assertFalse(hasattr(proxy, "_p_jar"))
        self.assertFalse(hasattr(proxy, "_p_oid"))


def test_suite():
    return unittest.TestSuite([unittest.makeSuite(TestThreadSafeRegistryProxy)])


if __name__ == "__main__":
    unittest.main()
