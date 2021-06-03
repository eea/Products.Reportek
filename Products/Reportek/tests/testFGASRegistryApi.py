# -*- coding: utf-8 -*-

import json

from mock import Mock, patch
from Products.Reportek.RegistryManagement import FGASRegistryAPI
from common import BaseTest


class FGASRegistryAPITest(BaseTest):
    userDetailInput = u"""
    [{"company_id": 1234,
      "name": "Blă Brul",
      "country": "RO",
      "domain": "FGAS",
      "collection_id": "fgas30001",
      "country_history": [
        "UK"
        ]
      },
     {"company_id": 12345,
      "name": "Blâ Brul",
      "country": "RO",
      "domain": "FGAS",
      "collection_id": null}
    ]
    """

    def setUp(self):
        self.api = FGASRegistryAPI('FGASRegistryAPI', 'http://localhost:5000')

    @patch('requests.get')
    def test_getCollectionPaths(self, req_mock):
        rsp = Mock()
        req_mock.return_value = rsp
        rsp.status_code = 200
        rsp.text = self.userDetailInput
        rsp.json = Mock(return_value=json.loads(rsp.text))

        username = 'vasile'
        expectedPaths = {
            'paths': [u'fgases/ro/fgas30001', u'fgases/ro/12345'],
            'prev_paths': [u'fgases/gb/fgas30001']
        }

        paths = self.api.getCollectionPaths(username)

        self.assertEqual(
            req_mock.call_args[0][0],
            self.api.baseUrl + '/user/' + username + '/companies')
        self.assertEqual(paths, expectedPaths)
