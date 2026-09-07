# -*- coding: utf-8 -*-
from .common import BaseTest, BaseUnitTest
from Products.Reportek import RepUtils

import logging

logger = logging.getLogger("Reportek")
logger.manager.disable = logging.CRITICAL
# logger.disable()

BASIC_TEMPLATE = """value:$value"""
TEMPLATE = """str:$str, num:$num, unicode:$unicode"""


class RepUtilsTestCase(BaseTest):
    def test_parse_template(self):
        """
        Test the parse_template function from RepUtils module.
        Basic test.
        """
        result = RepUtils.parse_template(
            TEMPLATE,
            dict={
                "str": "European Environment Agency",
                "num": 12.23333,
                "unicode": "Det Europæiske Miljøagentur",
            },
        )
        self.assertEqual(
            result,
            """str:European Environment Agency, num:12.23333, """
            """unicode:Det Europæiske Miljøagentur""",
        )

    def test_parse_template_empty(self):
        """
        Test the parse_template function from RepUtils module with an empty
        dictionary
        """
        self.assertRaises(Exception, RepUtils.parse_template, BASIC_TEMPLATE, dict={})

    def test_parse_template_msword(self):
        """
        Tests the parse_template function from RepUtils module.
        Test MSWord characters that are somewhat risky in HTML documents.
        """
        result = RepUtils.parse_template(
            BASIC_TEMPLATE, dict={"value": ",ƒ…^†“”‘’‰•Ÿæ©–"}
        )
        self.assertEqual(result, "value:,ƒ…^†“”‘’‰•Ÿæ©–")


DATAFLOWS = [
    {"PK_RA_ID": "1", "SOURCE_TITLE": "Source B"},
    {"PK_RA_ID": "2", "SOURCE_TITLE": "Source A"},
    {"PK_RA_ID": "3", "SOURCE_TITLE": "Source B"},
    {"PK_RA_ID": "4", "SOURCE_TITLE": "Source C"},
    {"PK_RA_ID": "5", "SOURCE_TITLE": "Source A"},
]


class RepUtilsSortTestCase(BaseUnitTest):
    """Tests for the sorting helpers in the RepUtils module."""

    def titles(self, p_obj_list):
        return [item["SOURCE_TITLE"] for item in p_obj_list]

    def test_sort_list_by_attr(self):
        """Items are ordered ascending on the given attribute."""
        result = RepUtils.utSortListByAttr(DATAFLOWS, "SOURCE_TITLE")
        self.assertEqual(
            self.titles(result),
            ["Source A", "Source A", "Source B", "Source B", "Source C"],
        )

    def test_sort_list_by_attr_descending(self):
        """A sort order reverses the result."""
        result = RepUtils.utSortListByAttr(DATAFLOWS, "SOURCE_TITLE", 1)
        self.assertEqual(
            self.titles(result),
            ["Source C", "Source B", "Source B", "Source A", "Source A"],
        )

    def test_sort_list_by_attr_duplicate_values(self):
        """
        Items sharing an attribute value are sorted without comparing the
        items themselves, which are dictionaries and not orderable, and
        keep their original relative order.
        """
        result = RepUtils.utSortListByAttr(DATAFLOWS, "SOURCE_TITLE")
        self.assertEqual(
            [item["PK_RA_ID"] for item in result], ["2", "5", "1", "3", "4"]
        )

    def test_sort_list_by_attr_missing_value(self):
        """Items with no value are grouped at the end instead of raising."""
        l_dataflows = [
            {"SOURCE_TITLE": "Source B"},
            {"SOURCE_TITLE": None},
            {"SOURCE_TITLE": "Source A"},
        ]
        self.assertEqual(
            self.titles(RepUtils.utSortListByAttr(l_dataflows, "SOURCE_TITLE")),
            ["Source A", "Source B", None],
        )
        self.assertEqual(
            self.titles(RepUtils.utSortListByAttr(l_dataflows, "SOURCE_TITLE", 1)),
            [None, "Source B", "Source A"],
        )

    def test_sort_list_by_attr_mixed_types(self):
        """Values of mixed types are compared as strings instead of raising."""
        l_dataflows = [
            {"SOURCE_TITLE": "Source B"},
            {"SOURCE_TITLE": 8},
            {"SOURCE_TITLE": "Source A"},
        ]
        self.assertEqual(
            self.titles(RepUtils.utSortListByAttr(l_dataflows, "SOURCE_TITLE")),
            [8, "Source A", "Source B"],
        )

    def test_sort_list_by_attr_unknown_attribute(self):
        """An item missing the attribute is still reported as a KeyError."""
        self.assertRaises(
            KeyError,
            RepUtils.utSortListByAttr,
            [{"TITLE": "Some obligation"}],
            "SOURCE_TITLE",
        )

    def test_sort_key(self):
        """Missing values sort last without being compared to another type."""
        self.assertEqual(
            sorted(["Source B", None, "Source A"], key=RepUtils.utSortKey),
            ["Source A", "Source B", None],
        )
