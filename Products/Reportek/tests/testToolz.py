# -*- coding: utf-8 -*-
from .common import BaseUnitTest
from Products.Reportek import constants
from Products.Reportek.Toolz import Toolz

import logging

logger = logging.getLogger("Reportek")
logger.manager.disable = logging.CRITICAL

DATAFLOWS = [
    {"PK_RA_ID": "1", "PK_SOURCE_ID": "20", "SOURCE_TITLE": "Source B"},
    {"PK_RA_ID": "2", "PK_SOURCE_ID": "10", "SOURCE_TITLE": "Source A"},
    {"PK_RA_ID": "3", "PK_SOURCE_ID": "20", "SOURCE_TITLE": "Source B"},
    {"PK_RA_ID": "4", "PK_SOURCE_ID": "30", "SOURCE_TITLE": "Source C"},
    {"PK_RA_ID": "5", "PK_SOURCE_ID": "10", "SOURCE_TITLE": "Source A"},
]


class DataflowsManagerStub:
    """Stands in for the ReportekEngine, the only thing
    dataflow_table_grouped needs from its context."""

    def __init__(self, dataflows):
        self.dataflows = dataflows

    def dataflow_table(self):
        return self.dataflows


class ToolzStub(Toolz):
    def __init__(self, dataflows):
        setattr(self, constants.ENGINE_ID, DataflowsManagerStub(dataflows))


class DataflowTableGroupedTestCase(BaseUnitTest):
    """Tests for the Toolz.dataflow_table_grouped method."""

    def test_dataflow_table_grouped(self):
        """Dataflows are grouped by source, the groups listed ascending."""
        groups, items = ToolzStub(DATAFLOWS).dataflow_table_grouped()
        self.assertEqual(groups, ["Source A", "Source B", "Source C"])
        self.assertEqual(
            {group: [item["PK_RA_ID"] for item in items[group]] for group in groups},
            {
                "Source A": ["2", "5"],
                "Source B": ["1", "3"],
                "Source C": ["4"],
            },
        )

    def test_dataflow_table_grouped_descending(self):
        """The groups follow the requested sort order."""
        groups, items = ToolzStub(DATAFLOWS).dataflow_table_grouped(desc=1)
        self.assertEqual(groups, ["Source C", "Source B", "Source A"])
        self.assertEqual(sorted(items.keys()), sorted(groups))

    def test_dataflow_table_grouped_on_other_key(self):
        """Dataflows can be grouped on another key than the default one."""
        groups, items = ToolzStub(DATAFLOWS).dataflow_table_grouped(key="PK_SOURCE_ID")
        self.assertEqual(groups, ["10", "20", "30"])
        self.assertEqual([item["PK_RA_ID"] for item in items["10"]], ["2", "5"])

    def test_dataflow_table_grouped_missing_source(self):
        """
        A dataflow without a source is grouped on its own instead of
        failing the whole listing.
        """
        dataflows = DATAFLOWS + [{"PK_RA_ID": "6", "SOURCE_TITLE": None}]
        groups, items = ToolzStub(dataflows).dataflow_table_grouped()
        self.assertEqual(groups, ["Source A", "Source B", "Source C", None])
        self.assertEqual([item["PK_RA_ID"] for item in items[None]], ["6"])

    def test_dataflow_table_grouped_groups_match_items(self):
        """
        Every listed group has a matching entry in the items dictionary,
        the two being rendered together by the templates.
        """
        for desc in (0, 1):
            groups, items = ToolzStub(DATAFLOWS).dataflow_table_grouped(desc=desc)
            self.assertEqual(list(items.keys()), groups)
            self.assertEqual(sum(len(items[group]) for group in groups), len(DATAFLOWS))
