# -*- coding: utf-8 -*-
import unittest

from mock import Mock, patch, PropertyMock
from zope.interface.verify import verifyObject

from plone.keyring.interfaces import IKeyManager
from Products.Reportek.RepUtils import ThreadSafeKeyManagerProxy


class TestThreadSafeKeyManagerProxy(unittest.TestCase):

    def _make_proxy_with_mock_manager(self, mock_manager=None):
        """Create a proxy and patch _get_real_manager to return mock_manager."""
        if mock_manager is None:
            mock_manager = Mock()
        proxy = ThreadSafeKeyManagerProxy()
        proxy._get_real_manager = Mock(return_value=mock_manager)
        return proxy, mock_manager

    # --- Interface compliance ---

    def test_implements_ikeymanager(self):
        proxy = ThreadSafeKeyManagerProxy()
        self.assertTrue(IKeyManager.implementedBy(ThreadSafeKeyManagerProxy))

    def test_provides_ikeymanager(self):
        proxy = ThreadSafeKeyManagerProxy()
        self.assertTrue(IKeyManager.providedBy(proxy))

    # --- Delegation tests ---

    def test_setitem_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.__setitem__ = Mock()
        proxy[u'_forms'] = 'new_ring'
        mgr.__setitem__.assert_called_once_with(u'_forms', 'new_ring')

    def test_getitem_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.__getitem__ = Mock(return_value='secret_value')
        result = proxy[u'_forms']
        mgr.__getitem__.assert_called_once_with(u'_forms')
        self.assertEqual(result, 'secret_value')

    def test_contains_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.__contains__ = Mock(return_value=True)
        result = u'_forms' in proxy
        mgr.__contains__.assert_called_once_with(u'_forms')
        self.assertTrue(result)

    def test_iter_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.__iter__ = Mock(return_value=iter([u'_forms', u'_system']))
        result = list(proxy)
        self.assertEqual(result, [u'_forms', u'_system'])

    def test_get_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.get = Mock(return_value='val')
        result = proxy.get(u'_forms', 'default')
        mgr.get.assert_called_once_with(u'_forms', 'default')
        self.assertEqual(result, 'val')

    def test_get_with_default(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.get = Mock(return_value=None)
        result = proxy.get(u'nonexistent', None)
        mgr.get.assert_called_once_with(u'nonexistent', None)
        self.assertIsNone(result)

    def test_keys_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.keys = Mock(return_value=[u'_forms', u'_system'])
        result = proxy.keys()
        mgr.keys.assert_called_once()
        self.assertEqual(result, [u'_forms', u'_system'])

    def test_values_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.values = Mock(return_value=['ring1', 'ring2'])
        result = proxy.values()
        mgr.values.assert_called_once()
        self.assertEqual(result, ['ring1', 'ring2'])

    def test_clear_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        proxy.clear(u'_system')
        mgr.clear.assert_called_once_with(u'_system')

    def test_clear_default_ring(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        proxy.clear()
        mgr.clear.assert_called_once_with(u'_system')

    def test_rotate_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        proxy.rotate(u'_forms')
        mgr.rotate.assert_called_once_with(u'_forms')

    def test_rotate_default_ring(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        proxy.rotate()
        mgr.rotate.assert_called_once_with(u'_system')

    def test_secret_delegates(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.secret = Mock(return_value='the_secret')
        result = proxy.secret(u'_forms')
        mgr.secret.assert_called_once_with(u'_forms')
        self.assertEqual(result, 'the_secret')

    def test_secret_default_ring(self):
        proxy, mgr = self._make_proxy_with_mock_manager()
        mgr.secret = Mock(return_value='sys_secret')
        result = proxy.secret()
        mgr.secret.assert_called_once_with(u'_system')
        self.assertEqual(result, 'sys_secret')

    # --- _get_real_manager resolution tests ---

    @patch('zope.globalrequest.getRequest', return_value=None)
    def test_no_request_raises_runtime_error(self, mock_get_request):
        proxy = ThreadSafeKeyManagerProxy()
        with self.assertRaises(RuntimeError) as cm:
            proxy._get_real_manager()
        self.assertIn('active request', str(cm.exception))

    @patch('plone.protect.utils.getRoot')
    @patch('zope.globalrequest.getRequest')
    def test_resolves_key_manager_from_request(self, mock_getRequest,
                                               mock_getRoot):
        mock_request = Mock()
        mock_getRequest.return_value = mock_request
        mock_root = Mock()
        mock_root.key_manager = Mock(name='real_km')
        mock_getRoot.return_value = mock_root
        proxy = ThreadSafeKeyManagerProxy()
        result = proxy._get_real_manager()
        mock_getRoot.assert_called_once_with(mock_request)
        self.assertEqual(result, mock_root.key_manager)

    @patch('plone.protect.utils.getRoot')
    @patch('zope.globalrequest.getRequest')
    def test_falls_back_to_underscore_key_manager(self, mock_getRequest,
                                                  mock_getRoot):
        mock_getRequest.return_value = Mock()
        mock_root = Mock(spec=[])  # no attributes by default
        mock_root._key_manager = Mock(name='fallback_km')
        # key_manager not present, _key_manager is
        mock_root.key_manager = None
        mock_getRoot.return_value = mock_root
        proxy = ThreadSafeKeyManagerProxy()
        result = proxy._get_real_manager()
        self.assertEqual(result, mock_root._key_manager)

    # --- PARENTS fallback tests ---

    @patch('plone.protect.utils.getRoot', return_value=None)
    @patch('zope.globalrequest.getRequest')
    def test_falls_back_to_parents_when_getroot_returns_none(
            self, mock_getRequest, mock_getRoot):
        mock_root = Mock()
        mock_root.key_manager = Mock(name='real_km')
        mock_request = Mock()
        mock_request.get = Mock(return_value=[mock_root])
        mock_getRequest.return_value = mock_request
        proxy = ThreadSafeKeyManagerProxy()
        result = proxy._get_real_manager()
        mock_request.get.assert_called_once_with('PARENTS', [])
        self.assertEqual(result, mock_root.key_manager)

    @patch('plone.protect.utils.getRoot', return_value=None)
    @patch('zope.globalrequest.getRequest')
    def test_parents_fallback_uses_last_parent(self, mock_getRequest,
                                               mock_getRoot):
        """PARENTS[-1] is the app root (last in traversal chain)."""
        child = Mock()
        app_root = Mock()
        app_root.key_manager = Mock(name='real_km')
        mock_request = Mock()
        mock_request.get = Mock(return_value=[child, app_root])
        mock_getRequest.return_value = mock_request
        proxy = ThreadSafeKeyManagerProxy()
        result = proxy._get_real_manager()
        self.assertEqual(result, app_root.key_manager)

    @patch('plone.protect.utils.getRoot', return_value=None)
    @patch('zope.globalrequest.getRequest')
    def test_returns_none_when_getroot_and_parents_both_empty(
            self, mock_getRequest, mock_getRoot):
        mock_request = Mock()
        mock_request.get = Mock(return_value=[])
        mock_getRequest.return_value = mock_request
        proxy = ThreadSafeKeyManagerProxy()
        result = proxy._get_real_manager()
        self.assertIsNone(result)

    # --- Each call gets a fresh manager (no caching) ---

    def test_each_call_resolves_manager_independently(self):
        proxy = ThreadSafeKeyManagerProxy()
        mgr1 = Mock()
        mgr1.secret = Mock(return_value='secret1')
        mgr2 = Mock()
        mgr2.secret = Mock(return_value='secret2')
        proxy._get_real_manager = Mock(side_effect=[mgr1, mgr2])
        self.assertEqual(proxy.secret(), 'secret1')
        self.assertEqual(proxy.secret(), 'secret2')
        self.assertEqual(proxy._get_real_manager.call_count, 2)

    # --- Proxy is stateless (no persistent state) ---

    def test_proxy_has_no_persistent_state(self):
        proxy = ThreadSafeKeyManagerProxy()
        self.assertFalse(hasattr(proxy, '_p_jar'))
        self.assertFalse(hasattr(proxy, '_p_oid'))
        self.assertFalse(hasattr(proxy, '_p_changed'))
