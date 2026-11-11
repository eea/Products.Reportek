"""Tests for the pages of the envelopes in the listing of a collection."""

import os
import re
from unittest.mock import patch

from AccessControl import getSecurityManager
from DateTime import DateTime
from ZPublisher import zpublish_mark

from Products.Reportek import config
from Products.Reportek.Collection import Collection
from Products.Reportek.Envelope import Envelope

from .common import BaseTest, BaseUnitTest
from .utils import create_envelope

BASEL = "http://rod.eionet.eu.int/obligations/8"


class StubWorkitem:
    __allow_access_to_unprotected_subobjects__ = 1
    activity_id = "Draft"


class FakeCollection:
    get_envelopes_listing_page_size = Collection.get_envelopes_listing_page_size
    get_envelopes_pager = Collection.get_envelopes_pager

    def __init__(self, request=None):
        self.REQUEST = request or {}


class EnvelopesPagerTest(BaseUnitTest):
    ENVELOPES = ["env%03d" % i for i in range(25)]

    def _pager(self, request=None, size=10, envelopes=None):
        envelopes = self.ENVELOPES if envelopes is None else envelopes
        with patch.object(config, "ENVELOPES_LISTING_PAGE_SIZE", size):
            return FakeCollection().get_envelopes_pager(envelopes, request or {})

    def test_the_first_page_is_listed_by_default(self):
        pager = self._pager()
        self.assertEqual(pager.object_list, self.ENVELOPES[:10])
        self.assertEqual(pager.paginator.count, 25)

    def test_pages_are_consecutive_and_complete(self):
        seen = []
        for page in ("1", "2", "3"):
            seen.extend(self._pager({"page": page}).object_list)
        self.assertEqual(seen, self.ENVELOPES)

    def test_the_last_page_has_the_rest(self):
        self.assertEqual(self._pager({"page": "3"}).object_list, self.ENVELOPES[20:])

    def test_pages_outside_of_the_range_show_the_last_page(self):
        last = self.ENVELOPES[20:]
        for page in ("4", "99", "0", "-1"):
            self.assertEqual(self._pager({"page": page}).object_list, last, page)

    def test_a_page_that_is_not_a_number_is_the_first_page(self):
        for page in ("abc", "", None, "1.5"):
            self.assertEqual(
                self._pager({"page": page}).object_list, self.ENVELOPES[:10], page
            )

    def test_show_all_lists_every_envelope(self):
        self.assertIsNone(self._pager({"show": "all"}))

    def test_other_values_of_show_are_paged(self):
        self.assertIsNotNone(self._pager({"show": "paged"}))
        self.assertIsNotNone(self._pager({"show": "x"}))

    def test_a_collection_with_few_envelopes_is_listed_whole(self):
        self.assertIsNone(self._pager(envelopes=self.ENVELOPES[:10]))
        self.assertIsNone(self._pager(envelopes=[]))

    def test_one_envelope_more_than_a_page_is_paged(self):
        pager = self._pager(envelopes=self.ENVELOPES[:11])
        self.assertEqual(pager.paginator.num_pages, 2)

    def test_a_page_size_of_zero_lists_everything(self):
        self.assertIsNone(self._pager(size=0))

    def test_every_deployment_is_paged(self):
        for deployment in ("BDR", "CDR", "MDR"):
            with patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", deployment):
                self.assertIsNotNone(self._pager(), deployment)

    def test_the_request_of_the_collection_is_used_by_default(self):
        collection = FakeCollection({"page": "2"})
        with patch.object(config, "ENVELOPES_LISTING_PAGE_SIZE", 10):
            pager = collection.get_envelopes_pager(self.ENVELOPES)
        self.assertEqual(pager.object_list, self.ENVELOPES[10:20])

    def test_the_page_size_is_the_setting(self):
        for deployment in ("BDR", "CDR"):
            with patch("Products.Reportek.Collection.REPORTEK_DEPLOYMENT", deployment):
                with patch.object(config, "ENVELOPES_LISTING_PAGE_SIZE", 40):
                    size = FakeCollection().get_envelopes_listing_page_size()
                self.assertEqual(size, 40, deployment)


class PublishingTest(BaseUnitTest):
    def test_the_helpers_cannot_be_called_from_the_web(self):
        for name in ("get_envelopes_pager", "get_envelopes_listing_page_size"):
            self.assertIs(zpublish_mark(getattr(Collection, name)), False, name)


class PageSizeSettingTest(BaseUnitTest):
    def _size(self, value):
        with patch.dict(os.environ, {"X_PAGE_SIZE": value}):
            return config._int_from_env("X_PAGE_SIZE", 100)

    def test_a_number_is_used(self):
        self.assertEqual(self._size("25"), 25)

    def test_the_default_is_used_when_it_is_not_a_number(self):
        for value in ("", "abc", "1.5"):
            self.assertEqual(self._size(value), 100, value)

    def test_the_default_is_used_when_it_is_not_set(self):
        self.assertEqual(config._int_from_env("NOT_SET_PAGE_SIZE", 100), 100)

    def test_the_default_page_size_is_100(self):
        self.assertEqual(config.ENVELOPES_LISTING_PAGE_SIZE, 100)

    def test_pages_are_at_least_as_big_as_the_smallest_listing_with_a_pager(self):
        self.assertEqual(config._listing_page_size(10), 25)
        self.assertEqual(config._listing_page_size(1), 25)
        self.assertEqual(config._listing_page_size(25), 25)
        self.assertEqual(config._listing_page_size(26), 26)

    def test_a_page_size_of_zero_or_less_turns_the_pages_off(self):
        self.assertEqual(config._listing_page_size(0), 0)
        self.assertEqual(config._listing_page_size(-5), 0)


class CollectionListingTest(BaseTest):
    """The listing of a collection with more envelopes than a page."""

    TOTAL = 30  # the pager is shown for more than 25 envelopes
    PAGE_SIZE = 10

    def afterSetUp(self):
        BaseTest.afterSetUp(self)
        self.createStandardDependencies()
        self.col = self.addCollection(
            self.app,
            title="Collection Title",
            descr="Desc",
            year="2003",
            endyear="2004",
            partofyear="",
            country="http://rod.eionet.eu.int/spatial/2",
            locality="",
            dataflow_uris=[BASEL],
            allow_collections=1,
            allow_envelopes=1,
            id="collection",
        )
        self.login()
        self.app.REQUEST.AUTHENTICATED_USER = getSecurityManager().getUser()
        now = DateTime()
        for i in range(self.TOTAL):
            envelope = create_envelope(self.col, "env%d" % i)
            envelope.reportingdate = now - i  # one day apart
        self.envelope_ids = list(self.col.objectIds("Report Envelope"))
        self.assertEqual(len(self.envelope_ids), self.TOTAL)

    def _render(self, deployment="BDR", size=PAGE_SIZE, **params):
        request = self.app.REQUEST
        for key in ("page", "show"):
            request.other.pop(key, None)
        for key, value in params.items():
            request.set(key, value)
        with patch("Products.Reportek.REPORTEK_DEPLOYMENT", deployment), patch.object(
            config, "ENVELOPES_LISTING_PAGE_SIZE", size
        ):
            return self.col.index_html()

    def _rows(self, html):
        listed = []
        for link in re.findall(r'<a href="([^"/?]+)/"', html):
            if link in self.envelope_ids:
                listed.append(link)
        return listed

    def test_all_the_envelopes_are_listed_when_they_fit_in_a_page(self):
        html = self._render(size=self.TOTAL)
        self.assertEqual(len(self._rows(html)), self.TOTAL)
        self.assertFalse("show=all" in html, "unexpected link to show all")
        self.assertFalse("show=paged" in html, "unexpected link to the pages")

    def test_the_pager_is_only_at_the_bottom_of_the_listing(self):
        html = self._render()
        self.assertEqual(html.count("show=all"), 1)
        self.assertEqual(html.count('class="paginator"'), 1)
        self.assertGreater(html.index('class="paginator"'), html.index("</table>"))

    def test_the_first_page_is_listed_with_the_pager(self):
        html = self._render()
        self.assertEqual(len(self._rows(html)), self.PAGE_SIZE)
        self.assertTrue("show=all" in html, "no link to show all")
        self.assertTrue("page=2" in html, "no link to page 2")

    def test_the_pages_have_every_envelope_once_in_the_order_of_show_all(self):
        everything = self._rows(self._render(show="all"))
        self.assertEqual(sorted(everything), sorted(self.envelope_ids))
        paged = []
        for page in ("1", "2", "3"):
            paged.extend(self._rows(self._render(page=page)))
        self.assertEqual(len(paged), self.TOTAL)
        self.assertEqual(paged, everything)

    def test_show_all_lists_every_envelope_and_links_back_to_the_pages(self):
        html = self._render(show="all")
        self.assertEqual(len(self._rows(html)), self.TOTAL)
        self.assertTrue("show=paged" in html, "no link back to the pages")
        self.assertFalse("show=all" in html, "unexpected link to show all")

    def test_a_page_outside_of_the_range_shows_the_last_page(self):
        self.assertEqual(
            self._rows(self._render(page="99")), self._rows(self._render(page="3"))
        )
        self.assertEqual(len(self._rows(self._render(page="3"))), self.PAGE_SIZE)

    def test_a_page_that_is_not_a_number_shows_the_first_page(self):
        self.assertEqual(
            self._rows(self._render(page="abc")), self._rows(self._render(page="1"))
        )

    def test_the_cdr_is_listed_in_pages_too(self):
        with patch.object(
            Envelope, "getListOfWorkitems", return_value=[StubWorkitem()]
        ):
            first = self._rows(self._render(deployment="CDR"))
            second = self._rows(self._render(deployment="CDR", page="2"))
            everything = self._rows(self._render(deployment="CDR", show="all"))
            html = self._render(deployment="CDR")
        self.assertEqual(len(first), self.PAGE_SIZE)
        self.assertEqual(first + second, everything[: 2 * self.PAGE_SIZE])
        self.assertEqual(len(everything), self.TOTAL)
        self.assertTrue("show=all" in html, "no link to show all")
        self.assertTrue("page=2" in html, "no link to page 2")

    def test_a_page_size_of_zero_lists_every_envelope(self):
        html = self._render(size=0)
        self.assertEqual(len(self._rows(html)), self.TOTAL)
        self.assertFalse("show=all" in html, "unexpected link to show all")
