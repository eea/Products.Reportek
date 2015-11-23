# -*- coding: utf-8 -*-

from mock import patch, Mock
import json
from Testing import ZopeTestCase
from Products.Reportek.RegistryManagement import FGASRegistryAPI


class FGASRegistryAPITest(ZopeTestCase.ZopeTestCase):
    userDetailInput = u"""
    [{"company_id": 1234,
      "name": "Blă Brul",
      "country": "RO",
      "domain": "FGAS",
      "collection_id": "fgas30001"},
     {"company_id": 12345,
      "name": "Blâ Brul",
      "country": "RO",
      "domain": "FGAS",
      "collection_id": null}
    ]
    """
    def setUp(self):
        self.api = FGASRegistryAPI(url='http://localhost:5000')

    @patch('requests.get')
    def test_getCollectionPaths(self, req_mock):
        rsp = Mock()
        req_mock.return_value = rsp
        rsp.status_code = 200
        rsp.text = self.userDetailInput
        rsp.json = Mock(return_value=json.loads(rsp.text))

        username = 'vasile'
        expectedPaths = [u'fgases/ro/fgas30001', u'fgases/ro/12345']

        paths = self.api.getCollectionPaths(username)
        self.assertEqual(req_mock.call_args[0][0], self.api.baseUrl + '/user/' + username + '/companies')
        self.assertEqual(paths, expectedPaths)
