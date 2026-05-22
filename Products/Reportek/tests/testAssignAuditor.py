# -*- coding: utf-8 -*-
"""Unit tests for EnvelopeCustomDataflows.assign_auditor and its helpers.

These exercise the orchestration of `assign_auditor` and the two helpers
extracted from it (`_recover_already_assigned`, `_find_matching_audit`)
without standing up a full Zope envelope: the real method functions are
bound onto a lightweight stub and the collaborators are mocked.
"""

import json

from common import BaseUnitTest
from mock import Mock, patch
from requests.exceptions import HTTPError

from Products.Reportek.EnvelopeCustomDataflows import (
    AUDIT_DATE_FORMAT,
    EnvelopeCustomDataflows,
)
from DateTime import DateTime

ALREADY_ASSIGNED = "Verification envelope already has an auditor assigned"


def _audit_data():
    return {
        "verification_envelope_url": "http://cdr/verif/1",
        "reporting_envelope_url": "http://cdr/report/1",
        "lead_auditor": "auditor@example.com",
        "auditor_uid": "uid-1",
    }


def _matching_audit(**overrides):
    audit = {
        "verification_envelope_url": "http://cdr/verif/1",
        "reporting_envelope_url": "http://cdr/report/1",
        "user": {"email": "auditor@example.com"},
        "end_date": None,
        "start_date": "2024-01-15 10:30:00",
    }
    audit.update(overrides)
    return audit


def _http_error(status_code=400, auditor=ALREADY_ASSIGNED):
    err = HTTPError()
    err.response = Mock()
    err.response.status_code = status_code
    err.response.json.return_value = {"errors": {"auditor": auditor}}
    return err


class _AuditStub(object):
    """Stub carrying the real method functions under test."""

    _find_matching_audit = (
        EnvelopeCustomDataflows._find_matching_audit.__func__
    )
    _recover_already_assigned = (
        EnvelopeCustomDataflows._recover_already_assigned.__func__
    )
    assign_auditor = EnvelopeCustomDataflows.assign_auditor.__func__


class FindMatchingAuditTest(BaseUnitTest):
    def setUp(self):
        self.stub = _AuditStub()

    def test_returns_matching_open_audit(self):
        audit = _matching_audit()
        result = self.stub._find_matching_audit([audit], _audit_data())
        self.assertIs(result, audit)

    def test_skips_closed_audit(self):
        audit = _matching_audit(end_date="2024-02-01 00:00:00")
        result = self.stub._find_matching_audit([audit], _audit_data())
        self.assertIsNone(result)

    def test_no_match_on_different_verification_url(self):
        audit = _matching_audit(verification_envelope_url="http://cdr/other")
        result = self.stub._find_matching_audit([audit], _audit_data())
        self.assertIsNone(result)

    def test_no_match_on_different_email(self):
        audit = _matching_audit(user={"email": "someone@example.com"})
        result = self.stub._find_matching_audit([audit], _audit_data())
        self.assertIsNone(result)

    def test_returns_first_match(self):
        first = _matching_audit()
        second = _matching_audit()
        result = self.stub._find_matching_audit(
            [first, second], _audit_data()
        )
        self.assertIs(result, first)

    def test_empty_audits(self):
        self.assertIsNone(self.stub._find_matching_audit([], _audit_data()))


class RecoverAlreadyAssignedTest(BaseUnitTest):
    def setUp(self):
        self.stub = _AuditStub()
        self.engine = Mock()

    def _details(self, audits):
        self.engine.FGASRegistryAPI.get_auditor_details.return_value = {
            "audited_companies": audits
        }

    def test_recovers_when_matching_audit_found(self):
        audit = _matching_audit()
        self._details([audit])
        res, start_date = self.stub._recover_already_assigned(
            self.engine, _audit_data(), _http_error()
        )
        self.assertEqual(res, {"success": True, "message": "Already assigned"})
        expected = DateTime(audit["start_date"]).strftime(AUDIT_DATE_FORMAT)
        self.assertEqual(start_date, expected)
        get_details = self.engine.FGASRegistryAPI.get_auditor_details
        get_details.assert_called_once_with("uid-1")

    def test_reraises_when_no_matching_audit(self):
        self._details([_matching_audit(end_date="2024-02-01 00:00:00")])
        err = _http_error()
        with self.assertRaises(HTTPError) as ctx:
            self.stub._recover_already_assigned(
                self.engine, _audit_data(), err
            )
        self.assertIs(ctx.exception, err)

    def test_reraises_on_non_400(self):
        err = _http_error(status_code=500)
        with self.assertRaises(HTTPError) as ctx:
            self.stub._recover_already_assigned(
                self.engine, _audit_data(), err
            )
        self.assertIs(ctx.exception, err)
        self.assertFalse(
            self.engine.FGASRegistryAPI.get_auditor_details.called
        )

    def test_reraises_when_marker_absent(self):
        err = _http_error(auditor="Some other auditor error")
        with self.assertRaises(HTTPError) as ctx:
            self.stub._recover_already_assigned(
                self.engine, _audit_data(), err
            )
        self.assertIs(ctx.exception, err)

    def test_handles_missing_auditor_details(self):
        self.engine.FGASRegistryAPI.get_auditor_details.return_value = None
        err = _http_error()
        with self.assertRaises(HTTPError) as ctx:
            self.stub._recover_already_assigned(
                self.engine, _audit_data(), err
            )
        self.assertIs(ctx.exception, err)


@patch("Products.Reportek.EnvelopeCustomDataflows.notify")
@patch("zope.interface.alsoProvides")
class AssignAuditorTest(BaseUnitTest):
    def _make_stub(self, settings=None, audit_data=None):
        stub = _AuditStub()
        stub.REQUEST = Mock()
        stub.is_fgas_verification = Mock(return_value=True)
        stub._load_verification_settings = Mock(
            return_value=settings if settings is not None else {}
        )
        stub._prepare_audit_data = Mock(
            return_value=audit_data or _audit_data()
        )
        stub._extract_audit_info = Mock(return_value={})
        self.engine = Mock()
        stub.getEngine = Mock(return_value=self.engine)
        return stub

    def test_raises_when_not_auditable(self, _also, _notify):
        stub = self._make_stub()
        stub.is_fgas_verification = Mock(return_value=False)
        with self.assertRaises(ValueError):
            stub.assign_auditor()

    def test_no_audit_when_verification_none(self, _also, _notify):
        stub = self._make_stub(
            settings={"verificationOptions": {"none": True}}
        )
        self.assertIsNone(stub.assign_auditor())
        self.assertFalse(self.engine.assign_for_audit.called)

    def test_successful_assignment(self, _also, notify):
        stub = self._make_stub()
        self.engine.assign_for_audit.return_value = json.dumps(
            {"success": True}
        )
        result = stub.assign_auditor()
        self.assertEqual(json.loads(result), {"success": True})
        self.assertTrue(stub.is_audit_assigned)
        self.assertIsNone(stub.audit_info["audit_end_date"])
        self.assertTrue(stub.audit_info["audit_start_date"])
        self.assertTrue(notify.called)

    def test_recovers_already_assigned(self, _also, notify):
        stub = self._make_stub()
        self.engine.assign_for_audit.side_effect = _http_error()
        self.engine.FGASRegistryAPI.get_auditor_details.return_value = {
            "audited_companies": [_matching_audit()]
        }
        result = stub.assign_auditor()
        self.assertEqual(json.loads(result)["success"], True)
        self.assertTrue(stub.is_audit_assigned)
        expected = DateTime("2024-01-15 10:30:00").strftime(AUDIT_DATE_FORMAT)
        self.assertEqual(stub.audit_info["audit_start_date"], expected)

    def test_non_recoverable_http_error_propagates(self, _also, _notify):
        stub = self._make_stub()
        self.engine.assign_for_audit.side_effect = _http_error(
            status_code=500
        )
        with self.assertRaises(HTTPError):
            stub.assign_auditor()
