# -*- coding: utf-8 -*-

from mock import patch, Mock
from Testing import ZopeTestCase
from Products.Reportek.BdrAuthorizationMiddlewareApi import AuthMiddlewareApi


class AuthMiddlewareApiTest(ZopeTestCase.ZopeTestCase):
    userDetailInput = u"""
    [{"external_id": 1234,
      "name": "Blă Brul",
      "country": "RO",
      "domain": "FGAS",
      "collection_id": "fgas30001"},
     {"external_id": 12345,
      "name": "Blâ Brul",
      "country": "RO",
      "domain": "ODS",
      "collection_id": null}
    ]
    """
    def setUp(self):
        self.api = AuthMiddlewareApi(url='http://localhost:5000')

    @patch('requests.get')
    def test_getCollectionPaths(self, req_mock):
        rsp = Mock()
        req_mock.return_value = rsp
        rsp.status_code = 200
        rsp.text = self.userDetailInput

        username = 'vasile'
        expectedPaths = [u'fgases/ro/fgas30001', u'ods/ro/12345']

        paths = self.api.getCollectionPaths(username)
        self.assertEqual(req_mock.call_args[0][0], self.api.baseUrl + '/user/detail/' + username)
        self.assertEqual(paths, expectedPaths)
