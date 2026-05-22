# -*- coding: utf-8 -*-
"""Tests for Collection.get_children.

`get_children` sorts heterogeneous children deterministically by grouping
values into type ranks (numbers, dates, strings, None, other). These tests
pin that externally observable ordering behaviour.
"""

from common import BaseUnitTest

from Products.Reportek.Collection import (
    Collection,
    _is_numeric,
    _normalize_sort_value,
    _raw_sort_value,
    _tie_breaker,
)


class _Child(object):
    """Minimal stand-in for a catalog-aware child object."""

    def __init__(self, id, **attrs):
        self._id = id
        for key, value in attrs.items():
            setattr(self, key, value)

    def getId(self):
        return self._id


class _NoIdChild(object):
    pass


class _CollectionStub(object):
    get_children = Collection.get_children.__func__

    def __init__(self, objs):
        self._objs = objs

    def objectValues(self, m_types):
        return list(self._objs)


class _FakeDate(object):
    def __init__(self, iso):
        self._iso = iso

    def ISO8601(self):
        return self._iso


class IsNumericTest(BaseUnitTest):
    def test_int_and_float_are_numeric(self):
        self.assertTrue(_is_numeric(5))
        self.assertTrue(_is_numeric(5.0))
        self.assertTrue(_is_numeric(-2))

    def test_bool_is_not_numeric(self):
        self.assertFalse(_is_numeric(True))
        self.assertFalse(_is_numeric(False))

    def test_non_numbers_are_not_numeric(self):
        self.assertFalse(_is_numeric(None))
        self.assertFalse(_is_numeric("5"))


class NormalizeSortValueTest(BaseUnitTest):
    def test_none_ranks_last(self):
        self.assertEqual(_normalize_sort_value(None), (3, None))

    def test_numbers(self):
        self.assertEqual(_normalize_sort_value(7), (0, 7))

    def test_strings_are_lowercased(self):
        self.assertEqual(_normalize_sort_value("Banana"), (2, "banana"))

    def test_iso8601_dates(self):
        self.assertEqual(
            _normalize_sort_value(_FakeDate("2024-01-15")),
            (1, "2024-01-15"),
        )

    def test_isoformat_dates(self):
        from datetime import datetime

        dt = datetime(2024, 1, 15, 10, 30)
        self.assertEqual(_normalize_sort_value(dt), (1, dt.isoformat()))

    def test_other_values_fall_back_to_repr(self):
        self.assertEqual(_normalize_sort_value(True), (4, repr(True)))


class RawSortValueTest(BaseUnitTest):
    def test_callable_sort_on(self):
        child = _Child("a", title="x")
        self.assertEqual(
            _raw_sort_value(child, lambda ob: ob.title, None), "x"
        )

    def test_callable_sort_on_swallows_errors(self):
        def boom(ob):
            raise ValueError("nope")

        self.assertIsNone(_raw_sort_value(_Child("a"), boom, None))

    def test_attribute_via_getter(self):
        import operator

        child = _Child("a", title="hello")
        getter = operator.attrgetter("title")
        self.assertEqual(_raw_sort_value(child, "title", getter), "hello")

    def test_missing_attribute_returns_none(self):
        import operator

        getter = operator.attrgetter("missing")
        self.assertIsNone(_raw_sort_value(_Child("a"), "missing", getter))

    def test_bound_method_is_called(self):
        import operator

        child = _Child("envid")
        getter = operator.attrgetter("getId")
        self.assertEqual(_raw_sort_value(child, "getId", getter), "envid")


class TieBreakerTest(BaseUnitTest):
    def test_uses_get_id(self):
        self.assertEqual(_tie_breaker(_Child("the-id")), "the-id")

    def test_falls_back_when_no_get_id(self):
        ob = _NoIdChild()
        self.assertEqual(_tie_breaker(ob), "id-%s" % (id(ob),))


class GetChildrenTest(BaseUnitTest):
    def _ids(self, result):
        return [ob.getId() for ob in result]

    def test_ascending_numeric_sort_with_none_last(self):
        objs = [
            _Child("a", val=3),
            _Child("b", val=1),
            _Child("c", val=2),
            _Child("d", val=None),
        ]
        stub = _CollectionStub(objs)
        result = stub.get_children("Report Envelope", "val", desc=0)
        self.assertEqual(self._ids(result), ["b", "c", "a", "d"])

    def test_descending_is_reverse(self):
        objs = [
            _Child("a", val=3),
            _Child("b", val=1),
            _Child("c", val=2),
            _Child("d", val=None),
        ]
        stub = _CollectionStub(objs)
        result = stub.get_children("Report Envelope", "val", desc=1)
        self.assertEqual(self._ids(result), ["d", "a", "c", "b"])

    def test_case_insensitive_string_sort(self):
        objs = [_Child("a", name="Banana"), _Child("b", name="apple")]
        stub = _CollectionStub(objs)
        result = stub.get_children("Report Envelope", "name", desc=0)
        self.assertEqual(self._ids(result), ["b", "a"])

    def test_callable_sort_on(self):
        objs = [_Child("a", val=2), _Child("b", val=1)]
        stub = _CollectionStub(objs)
        result = stub.get_children(
            "Report Envelope", lambda ob: ob.val, desc=0
        )
        self.assertEqual(self._ids(result), ["b", "a"])

    def test_missing_attribute_sorts_as_none(self):
        objs = [_Child("a", val=5), _Child("b")]
        stub = _CollectionStub(objs)
        result = stub.get_children("Report Envelope", "val", desc=0)
        self.assertEqual(self._ids(result), ["a", "b"])

    def test_tie_break_by_id(self):
        objs = [_Child("z", val=1), _Child("a", val=1)]
        stub = _CollectionStub(objs)
        result = stub.get_children("Report Envelope", "val", desc=0)
        self.assertEqual(self._ids(result), ["a", "z"])

    def test_empty(self):
        stub = _CollectionStub([])
        self.assertEqual(stub.get_children("Report Envelope", "val"), [])
