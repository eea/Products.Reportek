"""initialize() runs once, even when both Zope's Products scan and
five:registerPackage call it (an installed, not editable, package)."""

import unittest
from unittest.mock import Mock, patch

import Products.Reportek as package


class InitializeTest(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(package, "_initialized", False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_classes_are_registered_once(self):
        first, second = Mock(), Mock()
        package.initialize(first)
        registered = first.registerClass.call_count
        self.assertGreater(registered, 0)
        package.initialize(second)
        second.registerClass.assert_not_called()
        self.assertEqual(first.registerClass.call_count, registered)
