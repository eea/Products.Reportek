"""Tests for the windowed catalog sorts of the engine listings.

The recent uploads, recent released and global worklist pages only show one
batch of rows, so the catalog is asked to sort just up to the end of the batch.
The number of rows must stay the same, and the pages must not skip or repeat
rows, also when several rows share the same date.
"""

import unittest
from unittest.mock import Mock, patch

from DateTime import DateTime
from ZTUtils import Batch

from Products.Reportek.ReportekEngine import (
    OUTSIDE_WINDOW,
    WINDOW_MAX_ROWS,
    ReportekEngine,
    SortedWindow,
    windowed_search,
)

from .common import BaseTest, BaseUnitTest, ConfigureReportek
from .utils import create_envelope


class FakeBrain:
    def __init__(self, rid, key):
        self.rid = rid
        self.key = key

    def getRID(self):
        return self.rid

    def getObject(self):
        return "object-%03d" % self.rid


class FakeResults(list):
    def __init__(self, rows, actual_result_count):
        super().__init__(rows)
        self.actual_result_count = actual_result_count


class FakeIndex:
    def __init__(self, brains):
        self.keys = {b.rid: b.key for b in brains}

    def documentToKeyMap(self):
        return self.keys


class FakeCatalog:
    """Sorts like the catalog but, as it does, orders the rows sharing a sort
    value differently depending on the limit."""

    def __init__(self, keys):
        self.brains = [FakeBrain(rid, key) for rid, key in enumerate(keys)]
        self._catalog = Mock()
        self._catalog.getIndex.return_value = FakeIndex(self.brains)
        self.queries = []

    def searchResults(self, **query):
        self.queries.append(query)
        reverse = query.get("sort_order") in ("reverse", "descending")
        limit = query.get("sort_limit")
        ties_reversed = limit is not None and limit % 2 == 0
        rows = sorted(self.brains, key=lambda b: b.rid, reverse=ties_reversed)
        rows = sorted(rows, key=lambda b: b.key, reverse=reverse)
        if limit is None:
            return list(rows)
        return FakeResults(rows[:limit], len(rows))

    def expected(self, reverse):
        """The rows ordered by date, and the record id for equal dates."""
        rows = sorted(self.brains, key=lambda b: b.rid)
        return sorted(rows, key=lambda b: b.key, reverse=reverse)


# 100 rows in groups of 1 to 7 rows sharing a date, so that groups end up
# straddling the end of many windows
TIED_KEYS = []
for _group, _size in enumerate([1, 3, 7, 2, 5, 4, 1, 6] * 5):
    TIED_KEYS.extend([_group] * _size)
TIED_KEYS = TIED_KEYS[:130]


class SortedWindowTest(BaseUnitTest):
    def test_length_is_the_number_of_matches_not_of_the_window(self):
        window = SortedWindow(list(range(10)), 250)
        self.assertEqual(len(window), 250)

    def test_rows_are_read_from_the_window(self):
        window = SortedWindow(list(range(10)), 250)
        self.assertEqual(window[3], 3)
        self.assertEqual(window[2:5], [2, 3, 4])
        self.assertEqual(window[-250], 0)

    def test_rows_after_the_window_are_placeholders(self):
        window = SortedWindow([0, 1, 2], 10)
        self.assertIs(window[3], OUTSIDE_WINDOW)
        self.assertIs(window[9], OUTSIDE_WINDOW)
        self.assertIs(window[-1], OUTSIDE_WINDOW)
        self.assertEqual(window[1:5], [1, 2, OUTSIDE_WINDOW, OUTSIDE_WINDOW])

    def test_there_are_no_rows_after_the_last_match(self):
        window = SortedWindow([0, 1, 2], 10)
        for index in (10, 11, -11):
            with self.assertRaises(IndexError):
                window[index]

    def test_a_row_outside_the_window_cannot_be_used(self):
        row = SortedWindow([], 5)[0]
        with self.assertRaises(AttributeError):
            row.getPath()


class WindowedSearchTest(BaseUnitTest):
    def test_windows_are_the_start_of_the_same_order_for_any_ties(self):
        catalog = FakeCatalog(TIED_KEYS)
        for sort_order in ("reverse", "ascending"):
            expected = catalog.expected(sort_order == "reverse")
            for window_size in range(1, 60):
                window = windowed_search(
                    catalog,
                    window_size,
                    meta_type="x",
                    sort_on="reportingdate",
                    sort_order=sort_order,
                )
                self.assertEqual(len(window), len(TIED_KEYS))
                got = [b.rid for b in window[0:window_size]]
                self.assertEqual(
                    got,
                    [b.rid for b in expected[:window_size]],
                    (sort_order, window_size),
                )

    def test_pages_do_not_skip_or_repeat_rows(self):
        catalog = FakeCatalog(TIED_KEYS)
        for sort_order in ("reverse", "ascending"):
            for size, orphan in ((10, 1), (25, 1), (20, 5), (7, 0)):
                seen = []
                for start in range(0, len(TIED_KEYS), size):
                    window = windowed_search(
                        catalog,
                        start + size + orphan + 1,
                        sort_on="reportingdate",
                        sort_order=sort_order,
                    )
                    seen.extend(
                        b.rid for b in Batch(window, size, start, orphan=orphan)
                    )
                    if start + size + orphan + 1 >= len(TIED_KEYS):
                        break
                self.assertEqual(
                    seen,
                    [b.rid for b in catalog.expected(sort_order == "reverse")],
                    (sort_order, size, orphan),
                )

    def test_batches_report_the_same_pages_as_over_the_full_order(self):
        catalog = FakeCatalog(TIED_KEYS)
        for sort_order in ("reverse", "ascending"):
            expected = catalog.expected(sort_order == "reverse")
            full = SortedWindow(expected, len(expected))
            for size, orphan in ((10, 1), (25, 1), (20, 5), (7, 0)):
                for start in range(0, len(TIED_KEYS) + size, size):
                    window = windowed_search(
                        catalog,
                        start + size + orphan + 1,
                        sort_on="reportingdate",
                        sort_order=sort_order,
                    )
                    got = Batch(window, size, start, orphan=orphan)
                    want = Batch(full, size, start, orphan=orphan)
                    where = (sort_order, size, orphan, start)
                    self.assertEqual(got.length, want.length, where)
                    self.assertEqual(got.end, want.end, where)
                    self.assertEqual(
                        got.previous.first if got.previous else None,
                        want.previous.first if want.previous else None,
                        where,
                    )
                    self.assertEqual(
                        got.next.length if got.next else None,
                        want.next.length if want.next else None,
                        where,
                    )
                    self.assertEqual([b.rid for b in got], [b.rid for b in want], where)

    def test_rows_stay_in_date_order(self):
        catalog = FakeCatalog(TIED_KEYS)
        window = windowed_search(
            catalog, 40, sort_on="reportingdate", sort_order="reverse"
        )
        keys = [b.key for b in window[0:40]]
        self.assertEqual(keys, sorted(keys, reverse=True))

    def test_everything_is_fetched_when_the_window_is_bigger_than_the_results(self):
        catalog = FakeCatalog([1, 1, 2])
        window = windowed_search(catalog, 25, sort_on="reportingdate")
        self.assertEqual(len(window), 3)
        self.assertEqual([b.rid for b in window[0:25]], [0, 1, 2])

    def test_only_a_part_of_the_results_is_sorted(self):
        catalog = FakeCatalog(TIED_KEYS)
        windowed_search(catalog, 10, sort_on="reportingdate")
        self.assertLess(catalog.queries[0]["sort_limit"], len(TIED_KEYS))


class GetBatchSearchResultsTest(BaseUnitTest):
    def _search(self, *args, **query):
        catalog = FakeCatalog(TIED_KEYS)
        with patch(
            "Products.Reportek.ReportekEngine.getToolByName", return_value=catalog
        ):
            result = ReportekEngine.getBatchSearchResults(Mock(), *args, **query)
        return result, catalog

    def test_reportingdate_sort_is_limited_to_the_batch(self):
        result, catalog = self._search(
            50, 25, 1, meta_type="Report Envelope", sort_on="reportingdate"
        )
        self.assertIsInstance(result, SortedWindow)
        self.assertEqual(len(result), len(TIED_KEYS))
        self.assertGreaterEqual(catalog.queries[0]["sort_limit"], 77)
        self.assertEqual(
            [b.rid for b in result[50:77]],
            [b.rid for b in catalog.expected(False)[50:77]],
        )

    def test_deep_pages_keep_the_full_sort(self):
        result, catalog = self._search(WINDOW_MAX_ROWS, 25, 1, sort_on="reportingdate")
        self.assertNotIn("sort_limit", catalog.queries[0])
        self.assertNotIsInstance(result, SortedWindow)

    def test_the_deepest_windowed_page_is_limited(self):
        result, catalog = self._search(
            WINDOW_MAX_ROWS - 25 - 1 - 1, 25, 1, sort_on="reportingdate"
        )
        self.assertIsInstance(result, SortedWindow)

    def test_start_below_zero_does_not_shrink_the_window(self):
        result, _ = self._search(-10, 25, 1, sort_on="reportingdate")
        self.assertEqual(len(list(result[0:27])), 27)

    def test_start_can_be_a_string_from_the_request(self):
        result, _ = self._search("25", 25, 1, sort_on="reportingdate")
        self.assertEqual(len(list(result[25:52])), 27)

    def test_other_sorts_are_not_limited(self):
        for sort_on in ("released", "country", "years", None, ""):
            result, catalog = self._search(0, 25, 1, sort_on=sort_on)
            self.assertNotIn("sort_limit", catalog.queries[0], sort_on)
            self.assertNotIsInstance(result, SortedWindow)
            self.assertEqual(len(result), len(TIED_KEYS))

    def test_empty_values_are_dropped_like_in_getSearchResults(self):
        _, catalog = self._search(
            0, 25, 1, sort_on="reportingdate", released="", country=None
        )
        self.assertNotIn("released", catalog.queries[0])
        self.assertNotIn("country", catalog.queries[0])


class GetNotCompletedWorkitemsTest(BaseUnitTest):
    def _page(self, page, sortby="reportingdate", how="desc", total=137):
        keys = [i // 3 for i in range(total)]  # rows sharing a date
        catalog = FakeCatalog(keys)
        with patch(
            "Products.Reportek.ReportekEngine.getToolByName", return_value=catalog
        ):
            result = ReportekEngine.getNotCompletedWorkitems(
                Mock(), sortby, how, {"page": page}
            )
        return result, catalog

    def _expected_objects(self, catalog, page, per_page=20, orphans=5):
        rows = catalog.expected(True)
        bottom = (page - 1) * per_page
        top = bottom + per_page
        if top + orphans >= len(rows):
            top = len(rows)
        return [b.getObject() for b in rows[bottom:top]]

    def test_pages_have_the_rows_of_the_full_order(self):
        for page in range(1, 8):
            result, catalog = self._page(str(page))
            self.assertEqual(
                result.object_list, self._expected_objects(catalog, page), page
            )
            self.assertEqual(result.paginator.num_pages, 7)

    def test_reportingdate_sort_is_limited_to_the_page(self):
        _, catalog = self._page("2")
        self.assertIn("sort_limit", catalog.queries[0])
        self.assertLess(catalog.queries[0]["sort_limit"], 137)

    def test_other_sorts_are_not_limited(self):
        _, catalog = self._page("2", sortby="actor")
        self.assertNotIn("sort_limit", catalog.queries[0])

    def test_deep_pages_keep_the_full_sort(self):
        page = WINDOW_MAX_ROWS // 20 + 1
        _, catalog = self._page(str(page), total=WINDOW_MAX_ROWS + 500)
        self.assertNotIn("sort_limit", catalog.queries[0])

    def test_pages_outside_of_the_range_show_the_last_page(self):
        last, _ = self._page("7")
        for page in ("99", "0", "-3"):
            result, _ = self._page(page)
            self.assertEqual(result.object_list, last.object_list, page)

    def test_a_page_that_is_not_a_number_is_the_first_page(self):
        result, catalog = self._page("abc")
        self.assertEqual(result.number, 1)
        self.assertEqual(result.object_list, self._expected_objects(catalog, 1))

    def test_the_last_page_includes_the_orphans(self):
        result, _ = self._page("6", total=104)
        self.assertEqual(len(result.object_list), 24)  # 20 rows and 4 orphans


class BatchSearchResultsCatalogTest(BaseTest, ConfigureReportek):
    """The real catalog, with envelopes sharing a date, must give the same
    pages as the full sort."""

    TOTAL = 47

    def afterSetUp(self):
        super(BatchSearchResultsCatalogTest, self).afterSetUp()
        self.createStandardCatalog()
        self.createStandardDependencies()
        self.createStandardCollection()
        base = DateTime("2020/01/01 10:00")
        for i in range(self.TOTAL):
            env = create_envelope(self.app.collection, "env%02d" % i)
            # groups of three envelopes share a date
            env.reportingdate = base + (i // 3) / 1440.0
            env.released = i % 2
            env.reindexObject()
        self.keys = self.catalog_index("reportingdate").documentToKeyMap()

    def catalog_index(self, name):
        return self.app.Catalog._catalog.getIndex(name)

    def _rids_and_dates(self, rows):
        return [(b.getPath(), self.keys.get(b.getRID())) for b in rows]

    def test_pages_hold_the_same_rows_as_the_full_sort(self):
        for order in ("reverse", "ascending"):
            query = dict(
                meta_type="Report Envelope", sort_on="reportingdate", sort_order=order
            )
            full = list(self.engine.getSearchResults(**query))
            self.assertEqual(len(full), self.TOTAL)
            for start in range(0, self.TOTAL, 10):
                window = self.engine.getBatchSearchResults(start, 10, 1, **query)
                self.assertEqual(len(window), self.TOTAL)
                page = list(Batch(window, 10, start, orphan=1))
                expected = list(Batch(full, 10, start, orphan=1))
                # same rows in the same date order; rows sharing a date can be
                # in another order
                self.assertEqual(
                    [self.keys.get(b.getRID()) for b in page],
                    [self.keys.get(b.getRID()) for b in expected],
                    (order, start),
                )

    def test_pages_do_not_skip_or_repeat_envelopes(self):
        for order in ("reverse", "ascending"):
            query = dict(
                meta_type="Report Envelope", sort_on="reportingdate", sort_order=order
            )
            seen = []
            for start in range(0, self.TOTAL, 10):
                window = self.engine.getBatchSearchResults(start, 10, 1, **query)
                seen.extend(b.getPath() for b in Batch(window, 10, start, orphan=1))
                if start + 12 >= self.TOTAL:
                    break
            self.assertEqual(len(seen), self.TOTAL, order)
            self.assertEqual(len(set(seen)), self.TOTAL, order)

    def test_batches_report_the_same_next_and_previous_pages(self):
        query = dict(
            meta_type="Report Envelope", sort_on="reportingdate", sort_order="reverse"
        )
        full = Batch(self.engine.getSearchResults(**query), 10, 20, orphan=1)
        window = Batch(
            self.engine.getBatchSearchResults(20, 10, 1, **query), 10, 20, orphan=1
        )
        self.assertEqual(window.next.first, full.next.first)
        self.assertEqual(window.previous.first, full.previous.first)
        self.assertEqual(window.end, full.end)

    def test_every_batch_has_the_same_next_page_length_as_the_full_sort(self):
        for order in ("reverse", "ascending"):
            query = dict(
                meta_type="Report Envelope", sort_on="reportingdate", sort_order=order
            )
            full = self.engine.getSearchResults(**query)
            for start in range(0, self.TOTAL + 10, 10):
                window = self.engine.getBatchSearchResults(start, 10, 1, **query)
                got = Batch(window, 10, start, orphan=1)
                want = Batch(full, 10, start, orphan=1)
                self.assertEqual(got.length, want.length, (order, start))
                self.assertEqual(
                    got.next.length if got.next else None,
                    want.next.length if want.next else None,
                    (order, start),
                )

    def test_filtered_results_keep_their_count(self):
        query = dict(
            meta_type="Report Envelope",
            sort_on="reportingdate",
            sort_order="reverse",
            released=1,
        )
        full = self.engine.getSearchResults(**query)
        window = self.engine.getBatchSearchResults(0, 10, 1, **query)
        self.assertEqual(len(window), len(full))
        self.assertEqual(
            [self.keys.get(b.getRID()) for b in window[0:11]],
            [self.keys.get(b.getRID()) for b in list(full)[0:11]],
        )


if __name__ == "__main__":
    unittest.main()
