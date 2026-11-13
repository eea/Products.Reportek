"""The search parameters that are None or empty are not used to search."""

import unittest
from unittest.mock import Mock, patch

from Products.Reportek.ReportekEngine import ReportekEngine, _drop_empty_values


class DropEmptyValuesTest(unittest.TestCase):
    def test_the_empty_values_are_removed(self):
        kwargs = {"a": None, "b": "", "c": "x", "d": 0, "e": [], "f": False}
        _drop_empty_values(kwargs)
        self.assertEqual(kwargs, {"c": "x", "d": 0, "e": [], "f": False})

    def test_nothing_to_remove(self):
        kwargs = {"a": "x", "b": ["y"]}
        _drop_empty_values(kwargs)
        self.assertEqual(kwargs, {"a": "x", "b": ["y"]})

    def test_all_the_values_are_empty(self):
        kwargs = {str(i): None if i % 2 else "" for i in range(50)}
        _drop_empty_values(kwargs)
        self.assertEqual(kwargs, {})

    def test_no_parameters(self):
        kwargs = {}
        _drop_empty_values(kwargs)
        self.assertEqual(kwargs, {})


class SearchResultsTest(unittest.TestCase):
    def test_the_catalog_gets_the_parameters_that_have_a_value(self):
        catalog = Mock()
        with patch(
            "Products.Reportek.ReportekEngine.getToolByName", return_value=catalog
        ):
            ReportekEngine.getSearchResults(
                Mock(), meta_type="Report Envelope", year="", title=None, count=0
            )
        catalog.searchResults.assert_called_once_with(
            meta_type="Report Envelope", count=0
        )


if __name__ == "__main__":
    unittest.main()
