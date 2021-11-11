from Testing import ZopeTestCase
from common import BaseTest
ZopeTestCase.installProduct('Reportek')

# from Products.Reportek.Collection import Collection


class CollectionTestCase(BaseTest):

    #    def testCreation(self):
    #        """ Check for the correct creation of a collection """
    #        self.i = Collection('collection', 'TestTitle',
    #        '2003', '2004', '','http://rod.eionet.eu.int/localities/1',
    #        'test locality',
    #        'Test description')
    #        assert self.i, 'Collection not created'

    def testAddCollection(self):
        # self.folder.addDTMLMethod('doc', file='foo')
        # title, descr,year, endyear, partofyear, country, locality,
        # dataflow_uris,allow_collections=0, allow_envelopes=0, id='',
        # REQUEST=None
        self.app.manage_addProduct['Reportek'].manage_addCollection(
            'TestTitle', 'Desc',
            '2003', '2004', '', 'http://rod.eionet.eu.int/localities/1',
            '', [], allow_collections=1, allow_envelopes=1, id='colle')
        self.assertTrue(hasattr(self.app, 'colle'),
                        'Collection did not get created')
        self.assertNotEqual(self.app.colle, None)
