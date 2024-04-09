# -*- coding: utf-8 -*-

import json

from common import BaseTest
from mock import Mock, patch

from Products.Reportek.Collection import Collection
from Products.Reportek.RegistryManagement import FGASRegistryAPI


class FGASRegistryAPITest(BaseTest):
    userDetailInput = """
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

    def afterSetUp(self):
        super(FGASRegistryAPITest, self).afterSetUp()
        api = FGASRegistryAPI("FGASRegistryAPI", "http://localhost:5000")
        self.root._setObject("api", api)
        # create the previous collection
        Collection.getCountryName = Mock(return_value="United Kingdom")
        fgases = Collection(id="fgases")
        gb = Collection(id="gb")
        fgases._setObject(gb.id, gb)
        fgas30001 = Collection(id="fgas30001")
        gb._setObject(fgas30001.id, fgas30001)
        self.root._setObject(fgases.id, fgases)

    @patch("requests.get")
    def test_getCollectionPaths(self, req_mock):
        rsp = Mock()
        req_mock.return_value = rsp
        rsp.status_code = 200
        rsp.text = self.userDetailInput
        rsp.json = Mock(return_value=json.loads(rsp.text))

        username = "vasile"
        expectedPaths = {
            "paths": ["fgases/ro/fgas30001", "fgases/ro/12345"],
            "prev_paths": ["fgases/gb/fgas30001"],
        }

        paths = self.root.api.getCollectionPaths(username)

        self.assertEqual(
            req_mock.call_args[0][0],
            self.root.api.baseUrl + "/user/" + username + "/companies",
        )
        self.assertEqual(paths, expectedPaths)
