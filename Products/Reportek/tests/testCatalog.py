import unittest
from utils import create_fake_root


class CatalogTest(unittest.TestCase):

    def setUp(self):
        from Products.ZCatalog.ZCatalog import ZCatalog
        self.root = create_fake_root()
        catalog = ZCatalog('Catalog', 'Default Catalog for Reportek')
        self.root._setObject('Catalog', catalog)

    def test_autocatalog_new_object(self):
        from Products.Reportek.EnvelopeInstance import EnvelopeInstance
        from mock import Mock

        process = Mock()
        envelope = EnvelopeInstance(process)
        envelope.id = 'new-envelope'
        self.root._setObject(envelope.id, envelope)

        cataloged_objects = self.root.Catalog()
        self.assertEqual(len(cataloged_objects), 1)
        self.assertEqual(cataloged_objects[0].getObject(), envelope)
