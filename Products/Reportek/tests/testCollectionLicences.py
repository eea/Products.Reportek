# -*- coding: utf-8 -*-
"""
Tests for Collection licence-related methods.

IMPORTANT: Mock data structure (based on actual FGASRegistry API)
------------------------------------------------------------------
get_company_licences returns dict:
  {
      "licences": [
          {
              "substance": "HCFC-142b (virgin)",
              "s_orig_country_name": "SG",
              "company_id": 984,
              "organization_country_name": "FR",
              "year": 2025,
              "use_kind": "permanent export",
              "use_desc": "feedstock",
              "type": "export",
              "quantity": 160000
          }
      ]
  }

get_aggregated_multi_year_licences returns list:
  [
      # Multi-year licence (has extra fields):
      {
          "long_licence_number": "NUMBER66459",
          "substance": "HCFC-142b",
          "has_certex_data": True,
          "s_orig_country_name": "",
          "licence_type": "EFDS",
          "company_id": 984,
          "organization_country_name": "FR",
          "is_multi_year_licence": True,
          "year": 2025,
          "use_kind": "export",
          "use_desc": "feedstock",
          "type": "export",
          "quantity": 20000.0
      },
      # Single-year licence
      # (no long_licence_number, has_certex_data, licence_type):
      {
          "substance": "HCFC-142b (virgin)",
          "s_orig_country_name": "SG",
          "company_id": 984,
          "organization_country_name": "FR",
          "is_multi_year_licence": False,
          "year": 2025,
          "use_kind": "permanent export",
          "use_desc": "feedstock",
          "type": "export",
          "quantity": 160000
      }
  ]

BDR adds these fields to the response:
  - "result": "Ok" | "Fail" (based on HTTP status)
  - "message": error message | "" | None
"""

import json

from unittest.mock import Mock, patch

from Products.Reportek import DEPLOYMENT_BDR
from Products.Reportek.Collection import Collection
from Products.Reportek.tests.common import BaseTest


class CollectionLicencesTest(BaseTest):
    """Test cases for Collection licence methods"""

    def afterSetUp(self):
        super(CollectionLicencesTest, self).afterSetUp()

        # Create a mock registry
        mock_registry = Mock()
        mock_registry.registry_name = "FGAS Registry"

        # Use the engine already created by BaseTest and mock get_registry
        self.engine.get_registry = Mock(return_value=mock_registry)
        self.engine.er_ods_obligations = ["http://rod.eionet.europa.eu/obligations/869"]

        # Create a collection and add it to root
        test_col = Collection(id="test_col")
        self.root._setObject(test_col.id, test_col)

        # Set attributes on the wrapped object in the container
        self.root.test_col.company_id = "984"
        self.root.test_col.dataflow_uris = [
            "http://rod.eionet.europa.eu/obligations/868"
        ]

        self.mock_registry = mock_registry

    def _setup_request_mock(self, body_data, year=None):
        """Helper to set up REQUEST mock with body and year"""
        # Create a dict for the mock to return
        request_data = {"BODY": body_data, "year": year}

        # Mock REQUEST.get to handle multiple arguments
        def mock_get(key, default=None, **kwargs):
            return request_data.get(key, default)

        self.root.test_col.REQUEST.get = mock_get

        # Create and set mock RESPONSE object
        mock_response = Mock()
        mock_response.setHeader = Mock()
        self.root.test_col.REQUEST.RESPONSE = mock_response

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_multi_year_licences_success(self, req_codes_mock):
        """Test aggregated_multi_year_licences with successful response"""
        req_codes_mock.ok = 200

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "long_licence_number": "NUMBER67247",
                "substance": "HCFC-142b",
                "has_certex_data": True,
                "s_orig_country_name": "",
                "licence_type": "EFDS",
                "company_id": 984,
                "organization_country_name": "FR",
                "is_multi_year_licence": True,
                "year": 2025,
                "use_kind": "export",
                "use_desc": "feedstock",
                "type": "export",
                "quantity": 24323.0,
            },
            {
                "substance": "HCFC-142b (virgin)",
                "s_orig_country_name": "SG",
                "company_id": 984,
                "organization_country_name": "FR",
                "is_multi_year_licence": False,
                "year": 2025,
                "use_kind": "permanent export",
                "use_desc": "feedstock",
                "type": "export",
                "quantity": 20343,
            },
        ]

        self.mock_registry.get_aggregated_multi_year_licences = Mock(
            return_value=mock_response
        )

        # Set up request with body
        self._setup_request_mock(json.dumps({"filter": "test"}), year="2025")

        result = self.root.test_col.aggregated_multi_year_licences()
        result_data = json.loads(result)

        # Verify result structure
        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["message"], "")
        self.assertEqual(len(result_data["licences"]), 2)

        # Verify the registry method was called correctly
        self.mock_registry.get_aggregated_multi_year_licences.assert_called_once()  # noqa
        call_args = self.mock_registry.get_aggregated_multi_year_licences.call_args
        self.assertEqual(call_args[0][0], "984")  # company_id
        self.assertEqual(call_args[1]["domain"], "FGAS")
        self.assertEqual(call_args[1]["year"], "2025")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_multi_year_licences_ods_domain(self, req_codes_mock):
        """Test aggregated_multi_year_licences detects ODS domain"""
        req_codes_mock.ok = 200

        # Set ODS obligation
        self.root.test_col.dataflow_uris = [
            "http://rod.eionet.europa.eu/obligations/869"
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        self.mock_registry.get_aggregated_multi_year_licences = Mock(
            return_value=mock_response
        )

        self._setup_request_mock(json.dumps({}), year="2025")

        self.root.test_col.aggregated_multi_year_licences()

        # Verify ODS domain was used
        call_args = self.mock_registry.get_aggregated_multi_year_licences.call_args
        self.assertEqual(call_args[1]["domain"], "ODS")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_multi_year_licences_all_years(self, req_codes_mock):
        """Test aggregated_multi_year_licences with all_years parameter"""
        req_codes_mock.ok = 200

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        self.mock_registry.get_aggregated_multi_year_licences = Mock(
            return_value=mock_response
        )

        self._setup_request_mock(json.dumps({}), year=None)

        self.root.test_col.aggregated_multi_year_licences(all_years=True)

        # Verify empty year was used
        call_args = self.mock_registry.get_aggregated_multi_year_licences.call_args
        self.assertEqual(call_args[1]["year"], "")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    @patch("Products.Reportek.Collection.DateTime")
    def test_aggregated_multi_year_licences_default_year(self, dt_mock, req_codes_mock):
        """Test aggregated_multi_year_licences defaults to previous year"""
        req_codes_mock.ok = 200

        # Mock DateTime to return 2026
        mock_dt = Mock()
        mock_dt.year.return_value = 2026
        dt_mock.return_value = mock_dt

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        self.mock_registry.get_aggregated_multi_year_licences = Mock(
            return_value=mock_response
        )

        self._setup_request_mock(json.dumps({}), year=None)

        self.root.test_col.aggregated_multi_year_licences()

        # Verify previous year (2025) was used
        call_args = self.mock_registry.get_aggregated_multi_year_licences.call_args
        self.assertEqual(call_args[1]["year"], "2025")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_multi_year_licences_year_in_body(self, req_codes_mock):
        """Test aggregated_multi_year_licences with year in request body"""
        req_codes_mock.ok = 200

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        self.mock_registry.get_aggregated_multi_year_licences = Mock(
            return_value=mock_response
        )

        self._setup_request_mock(json.dumps({"year": 2024}), year=None)

        self.root.test_col.aggregated_multi_year_licences()

        # Verify year from body was used and removed from data
        call_args = self.mock_registry.get_aggregated_multi_year_licences.call_args
        self.assertEqual(call_args[1]["year"], "2024")
        # Verify year was removed from data parameter
        data_param = json.loads(call_args[1]["data"])
        self.assertNotIn("year", data_param)

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_multi_year_licences_failed_response(self, req_codes_mock):
        """Test aggregated_multi_year_licences with failed response"""
        req_codes_mock.ok = 200

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        self.mock_registry.get_aggregated_multi_year_licences = Mock(
            return_value=mock_response
        )

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_multi_year_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Fail")
        self.assertEqual(result_data["message"], "Internal Server Error")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_multi_year_licences_no_registry(self):
        """Test aggregated_multi_year_licences with no registry"""
        self.engine.get_registry = Mock(return_value=None)

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_multi_year_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_multi_year_licences_no_company_id(self):
        """Test aggregated_multi_year_licences with no company_id"""
        self.root.test_col.company_id = None

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_multi_year_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_multi_year_licences_wrong_registry(self):
        """Test aggregated_multi_year_licences with non-FGAS registry"""
        self.mock_registry.registry_name = "ODS Registry"

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_multi_year_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_multi_year_licences_malformed_body(self):
        """Test aggregated_multi_year_licences with malformed JSON raises
        ValueError"""
        self._setup_request_mock("not a json", year="2025")

        with self.assertRaises(ValueError):
            self.root.test_col.aggregated_multi_year_licences()

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_multi_year_licences_non_dict_body(self):
        """Test aggregated_multi_year_licences with non-dict JSON body"""
        self._setup_request_mock(json.dumps([1, 2, 3]), year="2025")

        result = self.root.test_col.aggregated_multi_year_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Fail")
        self.assertEqual(result_data["message"], "Malformed body")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", "CDR")
    def test_aggregated_multi_year_licences_non_bdr_deployment(self):
        """Test aggregated_multi_year_licences in non-BDR deployment"""
        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_multi_year_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_multi_year_licences_none_response(self, req_codes_mock):
        """Test aggregated_multi_year_licences with None response from ecr."""
        req_codes_mock.ok = 200

        self.mock_registry.get_aggregated_multi_year_licences = Mock(return_value=None)

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_multi_year_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Fail")
        self.assertEqual(result_data["message"], None)
        self.assertEqual(result_data["licences"], [])

    # Tests for aggregated_licences method

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_licences_success(self, req_codes_mock):
        """Test aggregated_licences with successful response"""
        req_codes_mock.ok = 200

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "licences": [
                {
                    "substance": "HBFC-31 B1",
                    "s_orig_country_name": "",
                    "company_id": 1049,
                    "organization_country_name": "DE",
                    "year": 2025,
                    "use_kind": None,
                    "use_desc": "feedstock",
                    "type": "import",
                    "quantity": 0.0,
                },
                {
                    "substance": "HCFC-142b (virgin)",
                    "s_orig_country_name": "US",
                    "company_id": 984,
                    "organization_country_name": "FR",
                    "year": 2025,
                    "use_kind": "permanent export",
                    "use_desc": "feedstock",
                    "type": "export",
                    "quantity": 12345,
                },
            ]
        }

        self.mock_registry.get_company_licences = Mock(return_value=mock_response)

        # Set up request with body
        self._setup_request_mock(json.dumps({"filter": "test"}), year="2025")

        result = self.root.test_col.aggregated_licences()
        result_data = json.loads(result)

        # Verify result structure
        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["message"], "")
        self.assertEqual(len(result_data["licences"]), 2)

        # Verify the registry method was called correctly
        self.mock_registry.get_company_licences.assert_called_once()
        call_args = self.mock_registry.get_company_licences.call_args
        self.assertEqual(call_args[0][0], "984")  # company_id
        self.assertEqual(call_args[1]["domain"], "FGAS")
        self.assertEqual(call_args[1]["year"], "2025")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_licences_ods_domain(self, req_codes_mock):
        """Test aggregated_licences detects ODS domain"""
        req_codes_mock.ok = 200

        # Set ODS obligation
        self.root.test_col.dataflow_uris = [
            "http://rod.eionet.europa.eu/obligations/869"
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        # get_company_licences returns dict with "licences" key
        mock_response.json.return_value = {"licences": []}
        self.mock_registry.get_company_licences = Mock(return_value=mock_response)

        self._setup_request_mock(json.dumps({}), year="2025")

        self.root.test_col.aggregated_licences()

        # Verify ODS domain was used
        call_args = self.mock_registry.get_company_licences.call_args

        self.assertEqual(call_args[1]["domain"], "ODS")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_licences_all_years(self, req_codes_mock):
        """Test aggregated_licences with all_years parameter"""
        req_codes_mock.ok = 200

        mock_response = Mock()
        mock_response.status_code = 200
        # get_company_licences returns dict with "licences" key
        mock_response.json.return_value = {"licences": []}
        self.mock_registry.get_company_licences = Mock(return_value=mock_response)

        self._setup_request_mock(json.dumps({}), year=None)

        self.root.test_col.aggregated_licences(all_years=True)

        # Verify empty year was used
        call_args = self.mock_registry.get_company_licences.call_args
        self.assertEqual(call_args[1]["year"], "")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    @patch("Products.Reportek.Collection.DateTime")
    def test_aggregated_licences_default_year(self, dt_mock, req_codes_mock):
        """Test aggregated_licences defaults to previous year"""
        req_codes_mock.ok = 200

        # Mock DateTime to return 2026
        mock_dt = Mock()
        mock_dt.year.return_value = 2026
        dt_mock.return_value = mock_dt

        mock_response = Mock()
        mock_response.status_code = 200
        # get_company_licences returns dict with "licences" key
        mock_response.json.return_value = {"licences": []}
        self.mock_registry.get_company_licences = Mock(return_value=mock_response)

        self._setup_request_mock(json.dumps({}), year=None)

        self.root.test_col.aggregated_licences()

        # Verify previous year (2025) was used
        call_args = self.mock_registry.get_company_licences.call_args
        self.assertEqual(call_args[1]["year"], "2025")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_licences_year_in_body(self, req_codes_mock):
        """Test aggregated_licences with year in request body"""
        req_codes_mock.ok = 200

        mock_response = Mock()
        mock_response.status_code = 200
        # get_company_licences returns dict with "licences" key
        mock_response.json.return_value = {"licences": []}
        self.mock_registry.get_company_licences = Mock(return_value=mock_response)

        self._setup_request_mock(json.dumps({"year": 2024}), year=None)

        self.root.test_col.aggregated_licences()

        # Verify year from body was used and removed from data
        call_args = self.mock_registry.get_company_licences.call_args
        self.assertEqual(call_args[1]["year"], "2024")
        # Verify year was removed from data parameter
        data_param = json.loads(call_args[1]["data"])
        self.assertNotIn("year", data_param)

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_licences_failed_response(self, req_codes_mock):
        """Test aggregated_licences with failed response"""
        req_codes_mock.ok = 200

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        self.mock_registry.get_company_licences = Mock(return_value=mock_response)

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Fail")
        self.assertEqual(result_data["message"], "Internal Server Error")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_licences_no_registry(self):
        """Test aggregated_licences with no registry"""
        self.engine.get_registry = Mock(return_value=None)

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_licences_no_company_id(self):
        """Test aggregated_licences with no company_id"""
        self.root.test_col.company_id = None

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_licences_wrong_registry(self):
        """Test aggregated_licences with non-FGAS registry"""
        self.mock_registry.registry_name = "ODS Registry"

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_licences_malformed_body(self):
        """Test aggregated_licences with malformed JSON raises ValueError"""
        self._setup_request_mock("not a json", year="2025")

        with self.assertRaises(ValueError):
            self.root.test_col.aggregated_licences()

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    def test_aggregated_licences_non_dict_body(self):
        """Test aggregated_licences with non-dict JSON body"""
        self._setup_request_mock(json.dumps([1, 2, 3]), year="2025")

        result = self.root.test_col.aggregated_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Fail")
        self.assertEqual(result_data["message"], "Malformed body")

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", "CDR")
    def test_aggregated_licences_non_bdr_deployment(self):
        """Test aggregated_licences in non-BDR deployment"""
        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Ok")
        self.assertEqual(result_data["licences"], [])

    @patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR)
    @patch("requests.codes")
    def test_aggregated_licences_none_response(self, req_codes_mock):
        """Test aggregated_licences with None response from registry"""
        req_codes_mock.ok = 200

        self.mock_registry.get_company_licences = Mock(return_value=None)

        self._setup_request_mock(json.dumps({}), year="2025")

        result = self.root.test_col.aggregated_licences()
        result_data = json.loads(result)

        self.assertEqual(result_data["result"], "Fail")
        self.assertEqual(result_data["message"], None)
        self.assertEqual(result_data["licences"], [])
