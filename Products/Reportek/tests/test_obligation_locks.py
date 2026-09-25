# -*- coding: utf-8 -*-
"""Tests for obligations manually flagged as migrated to another platform"""

from AccessControl import SpecialUsers, Unauthorized, getSecurityManager
from AccessControl.SecurityManagement import (
    newSecurityManager,
    noSecurityManager,
)
import json

from DateTime import DateTime
from Testing import ZopeTestCase

from Products.Reportek.constants import DATAFLOW_MAPPINGS
from Products.Reportek.DataflowMappings import DataflowMappings
from Products.Reportek.DataflowMappingsRecord import DataflowMappingsRecord
from Products.Reportek.Envelope import manage_addEnvelopeForm

from .common import BaseTest

ZopeTestCase.installProduct("Reportek")

BASEL = "http://rod.eionet.europa.eu/obligations/8"
LCP = "http://rod.eionet.europa.eu/obligations/9"
TERMINATED = "http://rod.eionet.europa.eu/obligations/16"


class MigratedObligationsTestCase(BaseTest):
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

    def login_as_manager(self):
        """The management screens need a user allowed to render manage_*"""
        newSecurityManager(None, SpecialUsers.system)
        self.addCleanup(noSecurityManager)

    def post(self, **fields):
        """Post to the locks tab the way the forms do, token and all"""
        from plone.protect.authenticator import createToken

        self.app.REQUEST["REQUEST_METHOD"] = "POST"
        self.app.REQUEST.form.clear()
        self.app.REQUEST.form.update(fields)
        self.app.REQUEST.form["_authenticator"] = createToken()
        return self.engine.obligation_locks_table()

    def test_nothing_flagged_by_default(self):
        self.assertEqual(dict(self.engine.locks), {})
        self.assertEqual(self.engine.get_locks([BASEL]), {})
        self.assertEqual(self.col.active_locks(), {})

    def test_flag_and_unflag(self):
        self.engine.set_lock(
            BASEL,
            kind="migrated",
            target_url="https://new.example/obl/8",
            reason="Moved.",
        )
        record = self.engine.locks[BASEL]
        self.assertEqual(record["target_url"], "https://new.example/obl/8")
        self.assertEqual(record["reason"], "Moved.")
        self.assertEqual(record["set_by"], "gigel")
        self.assertTrue(record["set_on"])

        self.assertEqual(self.engine.unset_locks([BASEL]), 1)
        self.assertEqual(dict(self.engine.locks), {})

    def test_lookup_only_returns_requested_uris(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.engine.set_lock(LCP, kind="migrated")
        self.assertEqual(list(self.engine.get_locks([LCP])), [LCP])
        self.assertEqual(self.engine.get_locks([TERMINATED]), {})

    def test_collection_reports_its_migrated_obligations(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.assertEqual(list(self.col.active_locks()), [BASEL])

    def test_envelope_creation_is_refused(self):
        self.login()
        self.assertTrue(self.create_envelope(self.col))

        self.engine.set_lock(
            BASEL, kind="migrated", target_url="https://new.example/obl/8"
        )
        with self.assertRaises(ValueError) as caught:
            self.create_envelope(self.col)
        self.assertIn("closed to reporting", str(caught.exception))
        self.assertIn("https://new.example/obl/8", str(caught.exception))

    def test_envelope_creation_allowed_for_other_obligations(self):
        self.login()
        self.engine.set_lock(LCP, kind="migrated")
        self.assertTrue(self.create_envelope(self.col))

    def test_table_rows_report_workflow_and_mapping_records(self):
        self.app._setObject(DATAFLOW_MAPPINGS, DataflowMappings())
        mappings = self.app[DATAFLOW_MAPPINGS]
        mappings._setObject(
            "rec8", DataflowMappingsRecord("rec8", "Basel schemas", BASEL)
        )
        mappings["rec8"].reindexObject()
        # begin_end is mapped to all dataflows by createStandardDependencies
        self.wf.setProcessMappings("begin_end", "0", "1", p_dataflows=[BASEL])

        self.engine.set_lock(BASEL, kind="migrated")
        rows, catch_all = self.engine._get_lock_rows()

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["uri"], BASEL)
        self.assertEqual(row["title"], "Yearly report to the Basel Convention")
        self.assertFalse(row["terminated"])
        self.assertEqual(row["processes"], ["begin_end"])
        self.assertEqual([r["title"] for r in row["records"]], ["Basel schemas"])
        self.assertEqual(catch_all, [])

    def test_catch_all_processes_are_reported_apart(self):
        self.engine.set_lock(BASEL, kind="migrated")
        rows, catch_all = self.engine._get_lock_rows()
        self.assertEqual(rows[0]["processes"], [])
        self.assertEqual(catch_all, ["begin_end"])

    def test_choices_are_grouped_and_skip_flagged_obligations(self):
        self.engine.set_lock(BASEL, kind="migrated")
        grouped = self.engine._get_lock_choices()
        self.assertIn("LCP Directive", grouped)
        choices = {c["uri"]: c for group in grouped.values() for c in group}
        # already flagged, so no longer on offer
        self.assertNotIn(BASEL, choices)
        # terminated in ROD, still listed but flagged as such for the macro
        self.assertEqual(choices[TERMINATED]["terminated"], "1")
        self.assertEqual(choices[LCP]["terminated"], "0")
        self.assertEqual(choices[LCP]["oid"], "9")
        self.assertEqual(
            choices[LCP]["title"],
            "Summary  of emission  inventory from largecombustion plants (LCP)",
        )

    def test_table_renders(self):
        self.login_as_manager()
        self.engine.set_lock(
            BASEL,
            kind="migrated",
            target_url="https://new.example/obl/8",
            reason="Moved.",
        )
        self.app.REQUEST["REQUEST_METHOD"] = "GET"
        html = self.engine.obligation_locks_table()
        self.assertIn("Yearly report to the Basel Convention", html)
        self.assertIn("https://new.example/obl/8", html)
        self.assertIn("Moved.", html)
        # the catch-all process is reported apart, not per row
        self.assertIn("begin_end", html)
        # select2, so the obligation can be found by typing its number
        self.assertIn("static/reportek.js", html)
        # one form per kind, each in its own modal behind a button
        self.assertIn('data-target="#seasonal-modal"', html)
        self.assertIn('data-target="#migrated-modal"', html)
        self.assertIn('id="seasonal-modal"', html)
        self.assertIn('id="migrated-modal"', html)
        self.assertIn('id="seasonal-obligations"', html)
        # both pickers come out of one loop, so check either one's markup
        select = html.split('id="migrated-obligations"')[1].split("</select>")[0]
        head = html.split('id="migrated-obligations"')[0]
        head = head[head.rindex("<select") :]
        self.assertIn('name="dataflow_uris:list"', head)
        self.assertIn("multiple", head)
        # terminated obligations are offered, greyed out
        self.assertIn('class="terminated"', select)
        # the number is readable in the option, not just typeable
        self.assertIn("[16] UNFCCC (AE-2)", select)
        self.assertIn('<optgroup label="EEA AMP">', select)
        self.assertIn(TERMINATED, select)
        # already flagged ones are not on offer any more
        self.assertNotIn(BASEL, select)

    def test_table_is_sortable_and_pageable(self):
        self.login_as_manager()
        self.engine.set_lock(BASEL, kind="migrated")
        self.engine.set_lock(TERMINATED, kind="migrated")
        html = self.engine.obligation_locks_table()
        # DataTables needs a thead to hang the sorting and filter row off
        self.assertIn('id="locks-table"', html)
        self.assertIn("<thead>", html)
        self.assertIn("<tbody>", html)
        self.assertIn("static/datatables.min.js", html)
        self.assertIn("static/obligation_locks.js", html)
        # the ZMI's own jQuery is the one Bootstrap's modal is bound to, so
        # the page must not load a second copy over the top of it
        self.assertNotIn("static/jquery", html)
        # the ROD status is its own column, so it can be filtered on
        self.assertIn("ROD status", html)
        body = html.split("<tbody>")[1].split("</tbody>")[0]
        self.assertIn(">Terminated<", body)
        self.assertIn(">Active<", body)
        # so is the obligation number: it only lived in the href before, and
        # the table filters on cell text, not on markup
        self.assertIn(">8</td>", body)
        self.assertIn(">16</td>", body)

    def test_editing_a_lock_through_the_form(self):
        self.login_as_manager()
        self.engine.set_lock(
            BASEL,
            kind="seasonal",
            strength="hard",
            open_from=DateTime("2026/02/01"),
            open_until=DateTime("2026/04/30"),
            reporting_year=2025,
            reason="Old reason",
        )
        self.post(
            add_seasonal="Save changes",
            # the obligation comes from the dialog, not the picker
            edit_uri=BASEL,
            dataflow_uris=[],
            open_from="2027-02-01",
            open_until="2027-05-31",
            strength="soft",
            reporting_year="2026",
            year_basis="reportingdate",
            reason="New reason",
            exempt_paths="/test\n/sandbox",
        )

        record = self.engine.locks[BASEL]
        self.assertEqual(record["open_from"], DateTime("2027/02/01"))
        self.assertEqual(record["open_until"], DateTime("2027/05/31"))
        self.assertEqual(record["strength"], "soft")
        self.assertEqual(record["reporting_year"], 2026)
        self.assertEqual(record["year_basis"], "reportingdate")
        self.assertEqual(record["reason"], "New reason")
        self.assertEqual(list(record["exempt_paths"]), ["/test", "/sandbox"])
        # editing one lock must not add another
        self.assertEqual(len(self.engine.locks), 1)

    def test_editing_preserves_every_stored_field(self):
        """set_lock rebuilds the record, so anything the dialog drops is lost"""
        self.login_as_manager()
        self.post(
            add_seasonal="Set window",
            dataflow_uris=[BASEL],
            open_from="2026-02-01",
            open_until="2026-04-30",
            strength="soft",
            reporting_year="2025",
            year_basis="reportingdate",
            reason="To reporters",
            reason_manager="To managers",
            reason_anonymous="To the public",
            exempt_paths="/test",
        )
        before = dict(self.engine.locks[BASEL])

        # edit one field and nothing else may move
        self.post(
            add_seasonal="Save changes",
            edit_uri=BASEL,
            open_from="2026-02-01",
            open_until="2026-05-31",
            strength="soft",
            reporting_year="2025",
            year_basis="reportingdate",
            reason="To reporters",
            reason_manager="To managers",
            reason_anonymous="To the public",
            exempt_paths="/test",
        )
        after = dict(self.engine.locks[BASEL])

        moved = {
            key for key in set(before) | set(after) if before.get(key) != after.get(key)
        }
        # set_on and set_by record who last touched it, by design
        self.assertEqual(moved, {"open_until", "set_on"})
        self.assertEqual(after["open_until"], DateTime("2026/05/31"))
        for key in (
            "reason",
            "reason_manager",
            "reason_anonymous",
            "strength",
            "reporting_year",
            "year_basis",
        ):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(list(after["exempt_paths"]), ["/test"])

    def test_editing_never_creates_a_second_lock_from_the_picker(self):
        self.login_as_manager()
        self.engine.set_lock(BASEL, kind="migrated")
        self.post(
            add_migrated="Save changes",
            edit_uri=BASEL,
            # a stale picker value must be ignored while editing
            dataflow_uris=[LCP],
            target_url="https://elsewhere.example/",
            reason="",
        )
        self.assertEqual(list(self.engine.locks), [BASEL])
        self.assertEqual(
            self.engine.locks[BASEL]["target_url"], "https://elsewhere.example/"
        )

    def test_rows_carry_what_the_edit_dialog_needs(self):
        self.engine.set_lock(
            BASEL,
            kind="seasonal",
            strength="soft",
            open_from=DateTime("2026/02/01"),
            open_until=DateTime("2026/04/30"),
            reporting_year=2025,
            reason="Closed",
            exempt_paths=["/test"],
        )
        rows, _catch_all = self.engine._get_lock_rows()
        payload = json.loads(rows[0]["payload"])
        self.assertEqual(payload["uri"], BASEL)
        self.assertEqual(payload["label"], "[8] Yearly report to the Basel Convention")
        self.assertEqual(payload["kind"], "seasonal")
        self.assertEqual(payload["strength"], "soft")
        # dates reach the form in the format its boxes expect
        self.assertEqual(payload["open_from"], "2026-02-01")
        self.assertEqual(payload["open_until"], "2026-04-30")
        self.assertEqual(payload["reporting_year"], 2025)
        self.assertEqual(payload["exempt_paths"], ["/test"])

    def test_edit_buttons_point_at_the_matching_dialog(self):
        self.login_as_manager()
        self.engine.set_lock(BASEL, kind="migrated")
        self.engine.set_lock(LCP, kind="seasonal", open_from=DateTime())
        html = self.engine.obligation_locks_table()
        body = html.split("<tbody>")[1].split("</tbody>")[0]
        self.assertIn('data-target="#migrated-modal"', body)
        self.assertIn('data-target="#seasonal-modal"', body)
        self.assertIn("data-lock=", body)

    def test_a_post_without_a_token_is_refused(self):
        from zExceptions import Forbidden

        self.login_as_manager()
        self.app.REQUEST["REQUEST_METHOD"] = "POST"
        self.app.REQUEST.form.update(
            {"add_migrated": "Flag as migrated", "dataflow_uris": [BASEL]}
        )
        with self.assertRaises(Forbidden):
            self.engine.obligation_locks_table()
        self.assertEqual(dict(self.engine.locks), {})

    def test_every_form_carries_a_token(self):
        self.login_as_manager()
        html = self.engine.obligation_locks_table()
        # the remove form and both dialogs
        self.assertEqual(html.count('name="_authenticator"'), 3)

    def test_a_dangerous_platform_address_is_refused(self):
        """The url is rendered as a link reporters click, in their session"""
        self.login_as_manager()
        for bad in (
            "javascript:alert(document.domain)",
            "JavaScript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "reportnet.europa.eu",
        ):
            with self.subTest(url=bad):
                self.engine.unset_locks([BASEL])
                message = self.post(
                    add_migrated="Flag as migrated",
                    dataflow_uris=[BASEL],
                    target_url=bad,
                )
                self.assertEqual(dict(self.engine.locks), {})
                self.assertEqual(self.engine.safe_target_url(bad), "")

        self.post(
            add_migrated="Flag as migrated",
            dataflow_uris=[BASEL],
            target_url="https://reportnet.europa.eu/",
        )
        self.assertEqual(
            self.engine.locks[BASEL]["target_url"], "https://reportnet.europa.eu/"
        )

    def test_a_dangerous_address_cannot_be_stored_programmatically(self):
        """set_lock is the choke point, not just the form"""
        self.engine.set_lock(
            BASEL, kind="migrated", target_url="javascript:alert(1)"
        )
        self.assertEqual(self.engine.locks[BASEL]["target_url"], "")

    def test_obligation_id_falls_back_to_the_uri(self):
        gone = "http://rod.eionet.europa.eu/obligations/4242"
        self.engine.set_lock(gone, kind="migrated")
        rows, _catch_all = self.engine._get_lock_rows()
        [row] = [r for r in rows if r["uri"] == gone]
        # dataflow_lookup only offers PK_RA_ID "0" for obligations it no
        # longer knows, so the number comes off the uri instead
        self.assertEqual(row["title"], "Unknown/Deleted obligation")
        self.assertEqual(row["oid"], "4242")

    def test_flagging_through_the_form(self):
        self.login_as_manager()
        self.post(
            add_migrated="Flag as migrated",
            dataflow_uris=[BASEL, LCP],
            target_url="https://new.example/obl/8",
            reason="Moved.",
        )
        self.assertEqual(sorted(self.engine.locks), sorted([BASEL, LCP]))

        self.post(remove="Reopen selected", uris=[BASEL, LCP])
        self.assertEqual(dict(self.engine.locks), {})

    def test_add_envelope_form_explains_the_migration(self):
        self.login()
        self.engine.set_lock(
            BASEL,
            kind="migrated",
            target_url="https://new.example/obl/8",
            reason="Moved.",
        )
        html = manage_addEnvelopeForm.__of__(self.col)()
        self.assertIn("Moved.", html)
        self.assertNotIn("Reporting has moved to another platform", html)
        self.assertIn("Envelopes can no longer be created", html)
        self.assertIn("Yearly report to the Basel Convention", html)
        self.assertIn("https://new.example/obl/8", html)
        self.assertIn("Moved.", html)
        self.assertNotIn('action="manage_addEnvelope"', html)

    def test_the_refusal_pages_fall_back_to_the_default_wording(self):
        """Clearing the reason has to put the translated sentence back"""
        self.login()
        for kind, expected in (
            ("migrated", "Reporting has moved to another platform"),
            ("seasonal", "Reporting is closed"),
        ):
            with self.subTest(kind=kind):
                self.engine.set_lock(
                    BASEL,
                    kind=kind,
                    reason="",
                    open_from=DateTime() - 20,
                    open_until=DateTime() - 10,
                )
                envelope = manage_addEnvelopeForm.__of__(self.col)()
                referral = self.col.manage_addReferralForm()
                self.assertIn(expected, envelope)
                self.assertIn(expected, referral)

    def test_the_prefill_and_the_fallback_are_the_same_sentence(self):
        """Both come from the one macro, so they cannot drift apart"""
        import re

        self.login_as_manager()
        html = self.engine.obligation_locks_table()
        offered = [
            " ".join(m.split())
            for m in re.findall(
                r'<div class="lock-default-reason"[^>]*>(.*?)</div>', html, re.S
            )
        ]
        # three audiences in each of the two dialogs
        self.assertEqual(len(offered), 6)
        self.assertIn(
            "Reporting has moved to another platform. This envelope stays readable here.",
            offered,
        )
        self.assertIn(
            "Reporting is closed. This envelope stays readable here.", offered
        )
        self.assertIn("Closed to reporters; still open to you.", offered)
        self.assertIn(
            "Reporting for this obligation has moved to another platform.", offered
        )
        # the same sentences the templates fall back to when a reason is blank
        self.engine.set_lock(BASEL, kind="migrated", reason="")
        self.assertEqual(
            self.engine.lock_body(self.engine.locks[BASEL], "reporter"), ""
        )

    def test_leaving_the_messages_empty_stores_nothing(self):
        """Empty is what keeps the wording translated, so it must survive"""
        self.login_as_manager()
        self.post(
            add_migrated="Flag as migrated",
            dataflow_uris=[BASEL],
            reason="",
            reason_manager="",
            reason_anonymous="",
        )
        record = self.engine.locks[BASEL]
        self.assertEqual(record["reason"], "")
        self.assertEqual(record["reason_manager"], "")
        self.assertEqual(record["reason_anonymous"], "")
        # and the reader gets the template's translated sentence, the one
        # for whoever is reading: this renders as a manager
        self.assertIn("still open to you", manage_addEnvelopeForm.__of__(self.col)())

    def test_the_refusal_pages_address_whoever_is_reading(self):
        """A manager turned away reads their own message, not the reporters'"""
        self.engine.set_lock(
            BASEL,
            kind="migrated",
            reason="REPORTER TEXT",
            reason_manager="MANAGER TEXT",
        )
        self.login()
        self.assertIn("REPORTER TEXT", manage_addEnvelopeForm.__of__(self.col)())

        self.login_as_manager()
        html = manage_addEnvelopeForm.__of__(self.col)()
        self.assertIn("MANAGER TEXT", html)
        self.assertNotIn("REPORTER TEXT", html)

    def test_the_refusal_pages_prefer_the_reason(self):
        self.login()
        self.engine.set_lock(
            BASEL,
            kind="seasonal",
            reason="Back in February.",
            open_from=DateTime() - 20,
            open_until=DateTime() - 10,
        )
        for html in (
            manage_addEnvelopeForm.__of__(self.col)(),
            self.col.manage_addReferralForm(),
        ):
            self.assertIn("Back in February.", html)
            self.assertNotIn("Reporting is closed.", html)

    def test_add_referral_form_explains_the_migration(self):
        self.login()
        self.col.prop_allowed_referrals = 1
        self.engine.set_lock(
            BASEL,
            kind="migrated",
            target_url="https://new.example/obl/8",
            reason="Moved.",
        )
        html = self.col.manage_addReferralForm()
        self.assertIn("Moved.", html)
        self.assertIn("Referrals can no longer be created", html)
        self.assertIn("Yearly report to the Basel Convention", html)
        self.assertIn("https://new.example/obl/8", html)
        self.assertNotIn('action="manage_addReferral"', html)


class FrozenEnvelopeTestCase(BaseTest):
    """Envelopes for a migrated obligation are read only for reporters"""

    # every manual transition a reporter can reach, by name
    TRANSITIONS = (
        "startInstance",
        "assignWorkitem",
        "unassignWorkitem",
        "activateWorkitem",
        "inactivateWorkitem",
        "suspendWorkitem",
        "resumeWorkitem",
        "completeWorkitem",
        "forwardState",
        "forwardWorkitem",
        "changeWorkitem",
        "falloutWorkitem",
        "cancel_activity",
    )

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
        self.env = self.create_envelope(self.col)

    def as_reporter(self):
        """The test user has no management rights, so it stands in for one"""
        self.login()
        self.publish_as(getSecurityManager().getUser())

    def as_manager(self):
        newSecurityManager(None, SpecialUsers.system)
        self.addCleanup(noSecurityManager)
        self.publish_as(SpecialUsers.system)

    def publish_as(self, user):
        """Templates read the user off the request, not the security manager"""
        self.app.REQUEST.AUTHENTICATED_USER = user

    def test_not_frozen_while_nothing_is_flagged(self):
        self.as_reporter()
        self.assertFalse(self.env.is_frozen())
        self.assertEqual(self.env.active_locks(), {})

    def test_frozen_for_a_reporter_once_flagged(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_reporter()
        self.assertTrue(self.env.is_frozen())

    def test_not_frozen_for_a_manager(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_manager()
        self.assertFalse(self.env.is_frozen())

    def test_every_transition_refuses_a_reporter(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_reporter()
        workitem_id = self.env.getListOfWorkitems()[0].getId()
        for name in self.TRANSITIONS:
            with self.subTest(transition=name):
                with self.assertRaises(Unauthorized):
                    getattr(self.env, name)(workitem_id)

    def test_transitions_still_work_for_a_manager(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_manager()
        workitem_id = self.env.getListOfWorkitems()[0].getId()
        self.env.activateWorkitem(workitem_id)
        self.assertEqual(getattr(self.env, workitem_id).status, "active")

    def test_content_is_read_only_for_a_reporter(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_reporter()
        for name, args in (
            ("manage_addDocument", ()),
            ("manage_addHyperlink", ()),
            ("manage_addzipfile", ()),
            ("manage_addFeedback", ()),
            ("manage_deleteFeedback", ()),
            ("manage_delObjects", ()),
            ("manage_copyDelivery", ("",)),
        ):
            with self.subTest(action=name):
                with self.assertRaises(Unauthorized):
                    getattr(self.env, name)(*args)

    def test_reading_and_zipping_still_work_for_a_reporter(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_reporter()
        self.assertTrue(self.env.getListOfWorkitems())
        self.assertEqual(self.env.objectIds("Report Document"), [])
        self.assertFalse(self.env.canAddFiles())
        self.assertFalse(self.env.canChangeEnvelope())
        self.assertFalse(self.env.canAddFeedback())
        self.assertFalse(self.env.canEditFeedback())

    def test_automatic_applications_are_not_frozen(self):
        """Automatic QA runs as the system user, so it keeps its access"""
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_manager()
        self.assertFalse(self.env.is_frozen())
        self.assertTrue(self.env.canChangeEnvelope())

    def test_activity_operations_hide_the_workflow_links(self):
        # let the test user pull the Begin activity, so that the links the
        # frozen envelope has to hide are there to begin with
        self.wf.editActivitiesPullableOnRole("Owner", "begin_end", activities=["Begin"])
        self.as_reporter()
        self.assertIn("activateWorkitem", self.env.activity_operations())

        self.engine.set_lock(BASEL, kind="migrated")
        html = self.env.activity_operations()
        self.assertNotIn("activateWorkitem", html)
        self.assertNotIn("completeWorkitem", html)

    def test_overview_explains_the_migration(self):
        self.engine.set_lock(
            BASEL,
            kind="migrated",
            target_url="https://new.example/obl/8",
            reason="Moved.",
        )
        self.as_manager()
        html = self.env.overview()
        banner = html.split('id="obligation-lock"')[1].split("</div>")[0]
        self.assertIn("<strong", banner)
        self.assertIn("https://new.example/obl/8", banner)
        # a manager is told what a manager needs, not the reporters' text
        self.assertIn("still open to you", banner)
        self.assertNotIn("Moved.", banner)

    def test_each_audience_gets_its_own_message(self):
        self.engine.set_lock(
            BASEL,
            kind="migrated",
            reason="Deliver at Reportnet 3.",
            reason_manager="Finish the one in flight, then leave it.",
            reason_anonymous="This dataset is now published elsewhere.",
        )
        [record] = self.env.closed_locks().values()
        self.assertEqual(
            self.env.lock_body(record, "reporter"), "Deliver at Reportnet 3."
        )
        self.assertEqual(
            self.env.lock_body(record, "manager"),
            "Finish the one in flight, then leave it.",
        )
        self.assertEqual(
            self.env.lock_body(record, "anonymous"),
            "This dataset is now published elsewhere.",
        )

    def test_the_public_falls_back_to_the_reporters_message(self):
        self.engine.set_lock(BASEL, kind="migrated", reason="Deliver at Reportnet 3.")
        [record] = self.env.closed_locks().values()
        self.assertEqual(
            self.env.lock_body(record, "anonymous"), "Deliver at Reportnet 3."
        )

    def test_a_manager_never_inherits_the_reporters_message(self):
        """They are told different things, so falling back would mislead"""
        self.engine.set_lock(BASEL, kind="migrated", reason="Deliver at Reportnet 3.")
        [record] = self.env.closed_locks().values()
        self.assertEqual(self.env.lock_body(record, "manager"), "")

    def test_the_default_wording_shows_when_the_reason_is_cleared(self):
        self.engine.set_lock(BASEL, kind="migrated", reason="")
        self.as_manager()
        html = self.env.overview()
        self.assertIn("still open to you", html)
        [record] = self.env.closed_locks().values()
        self.assertEqual(self.env.lock_body(record, "reporter"), "")

    def test_overview_does_not_offer_the_manager_line_to_a_reporter(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_reporter()
        self.assertTrue(self.env.is_frozen())
        self.assertNotIn("activateWorkitem", self.env.activity_operations())


class SeasonalLockTestCase(BaseTest):
    """Windows, strengths and exemptions"""

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

    def as_reporter(self):
        self.login()

    def as_manager(self):
        newSecurityManager(None, SpecialUsers.system)
        self.addCleanup(noSecurityManager)

    def set_window(self, days_from, days_to, **fields):
        """Open the window relative to today, in days"""
        now = DateTime()
        self.engine.set_lock(
            BASEL,
            kind="seasonal",
            open_from=now + days_from,
            open_until=now + days_to,
            **fields,
        )

    # --- the window itself

    def test_open_window_locks_nothing(self):
        self.set_window(-10, 10)
        self.as_reporter()
        self.assertEqual(self.col.active_locks(), {})

    def test_closed_before_the_window_opens(self):
        self.set_window(10, 20)
        self.as_reporter()
        self.assertEqual(list(self.col.active_locks()), [BASEL])

    def test_closed_after_the_window_shuts(self):
        self.set_window(-20, -10)
        self.as_reporter()
        self.assertEqual(list(self.col.active_locks()), [BASEL])

    def test_state_reported_for_the_listing(self):
        now = DateTime()
        cases = {
            (-10, 10): "open",
            (10, 20): "scheduled",
            (-20, -10): "expired",
        }
        for (start, end), expected in cases.items():
            with self.subTest(state=expected):
                self.set_window(start, end)
                record = self.engine.locks[BASEL]
                self.assertEqual(self.engine._get_lock_state(record, now), expected)

    def test_migrated_has_no_window_and_is_always_closed(self):
        self.engine.set_lock(BASEL, kind="migrated")
        record = self.engine.locks[BASEL]
        self.assertTrue(self.engine.lock_is_closed(record))
        self.assertEqual(self.engine._get_lock_state(record, DateTime()), "closed")
        # the window fields a seasonal form would set are dropped
        self.assertIsNone(record["open_from"])
        self.assertEqual(record["strength"], "hard")

    # --- who gets through

    def test_the_manager_exemption_is_judged_where_the_work_happens(self):
        """Permissions are local, so the exemption follows the object.

        It used to be judged against the engine, which only sees site wide
        roles: a Manager role granted on one collection or envelope would
        have counted for nothing.
        """
        from unittest.mock import patch

        env = self.create_envelope(self.col)
        with patch.object(self.engine, "get_locks", return_value={}) as get_locks:
            self.col.active_locks()
            self.assertIs(get_locks.call_args.kwargs["context"], self.col)

            get_locks.reset_mock()
            env.active_locks()
            self.assertIs(get_locks.call_args.kwargs["context"], env)

    def test_the_context_falls_back_when_there_is_no_collection(self):
        self.set_window(-20, -10)
        self.login()
        # nothing to judge against but the engine itself, and no crash
        self.assertEqual(list(self.engine.get_locks([BASEL])), [BASEL])

    def test_a_manager_reports_outside_a_seasonal_window(self):
        self.set_window(-20, -10)
        self.as_manager()
        self.assertEqual(self.col.active_locks(), {})

    def test_a_manager_cannot_create_for_a_migrated_obligation(self):
        self.engine.set_lock(BASEL, kind="migrated")
        self.as_manager()
        self.assertEqual(list(self.col.active_locks()), [BASEL])
        # but may still act on an envelope already open
        self.assertEqual(self.col.active_locks(for_creation=False), {})

    def test_exempt_path_reports_through_a_closed_window(self):
        self.set_window(-20, -10, exempt_paths=["/collection"])
        self.as_reporter()
        self.assertEqual(self.col.active_locks(), {})

    def test_exempt_path_matches_whole_subtrees_only(self):
        self.set_window(-20, -10, exempt_paths=["/collec"])
        self.as_reporter()
        # a prefix that stops mid segment is not a parent path
        self.assertEqual(list(self.col.active_locks()), [BASEL])

    # --- soft locks

    def test_soft_lock_lets_a_collection_that_has_not_reported_through(self):
        self.set_window(-20, -10, strength="soft", reporting_year=2003)
        self.as_reporter()
        self.assertFalse(self.col.has_reported(2003))
        self.assertEqual(self.col.active_locks(), {})

    def test_soft_lock_closes_once_the_collection_has_reported(self):
        self.set_window(-20, -10, strength="soft", reporting_year=2003)
        self.report(self.col)
        self.as_reporter()
        self.assertTrue(self.col.has_reported(2003))
        self.assertEqual(list(self.col.active_locks()), [BASEL])

    def test_hard_lock_closes_whether_reported_or_not(self):
        self.set_window(-20, -10, strength="hard", reporting_year=2003)
        self.as_reporter()
        self.assertEqual(list(self.col.active_locks()), [BASEL])

    def test_an_unfinished_delivery_does_not_count_as_reported(self):
        env = self.create_envelope(self.col)
        env.released = 1
        env.reindexObject()
        self.assertFalse(self.col.has_reported(2003))

    def test_reported_by_delivery_date(self):
        self.report(self.col)
        year = DateTime().year()
        self.assertTrue(self.col.has_reported(year, year_basis="reportingdate"))
        self.assertFalse(self.col.has_reported(year - 5, year_basis="reportingdate"))

    def test_a_closed_window_freezes_an_envelope_already_open(self):
        """The point of a window: work in flight stops when it shuts"""
        env = self.create_envelope(self.col)
        self.as_reporter()
        self.assertFalse(env.is_frozen())

        self.set_window(-20, -10)
        self.assertTrue(env.is_frozen())
        workitem_id = env.getListOfWorkitems()[0].getId()
        with self.assertRaises(Unauthorized):
            env.activateWorkitem(workitem_id)
        with self.assertRaises(Unauthorized):
            env.manage_addDocument()

        # and it thaws again when the window reopens
        self.set_window(-10, 10)
        self.assertFalse(env.is_frozen())

    def test_referral_creation_is_refused_server_side(self):
        self.set_window(-20, -10)
        self.as_reporter()
        with self.assertRaises(Unauthorized) as caught:
            self.col.manage_addReferral(
                "Title",
                "",
                "http://example.org/",
                "2003",
                "2004",
                "",
                "http://rod.eionet.eu.int/spatial/2",
                "",
                [BASEL],
            )
        self.assertIn("closed to reporting", str(caught.exception))

    def test_referral_creation_allowed_while_the_window_is_open(self):
        self.set_window(-10, 10)
        self.as_reporter()
        self.col.manage_addReferral(
            "Title",
            "",
            "http://example.org/",
            "2003",
            "2004",
            "",
            "http://rod.eionet.eu.int/spatial/2",
            "",
            [BASEL],
        )
        self.assertTrue(self.col.objectIds("Repository Referral"))

    def test_the_closing_date_is_a_reporting_day(self):
        """Open until the 31st means the whole of the 31st"""
        self.engine.set_lock(
            BASEL,
            kind="seasonal",
            open_from=DateTime("2027/02/01"),
            open_until=DateTime("2027/05/31"),
        )
        record = self.engine.locks[BASEL]
        for moment, closed in (
            ("2027/01/31 23:59", True),
            ("2027/02/01 00:00", False),
            ("2027/05/31 00:00", False),
            ("2027/05/31 23:59", False),
            ("2027/06/01 00:00", True),
        ):
            with self.subTest(moment=moment):
                self.assertEqual(
                    self.engine.lock_is_closed(record, DateTime(moment)), closed
                )

    def test_a_window_with_no_dates_is_refused(self):
        from plone.protect.authenticator import createToken

        self.as_manager()
        self.app.REQUEST["REQUEST_METHOD"] = "POST"
        self.app.REQUEST.form.update(
            {
                "add_seasonal": "Set window",
                "dataflow_uris": [BASEL],
                "open_from": "",
                "open_until": "",
                "reason": "no dates at all",
                "_authenticator": createToken(),
            }
        )
        self.engine.obligation_locks_table()
        # silently creating a lock that never opens is the worst outcome
        self.assertEqual(dict(self.engine.locks), {})

    def test_a_root_exempt_path_is_dropped(self):
        self.set_window(-20, -10, exempt_paths=["/", "  ", "/test"])
        self.as_reporter()
        # "/" would have exempted the whole site
        self.assertEqual(list(self.col.active_locks()), [BASEL])

    def test_a_reader_the_lock_lets_through_is_told_nothing(self):
        env = self.create_envelope(self.col)
        self.set_window(-20, -10, exempt_paths=["/collection"])
        self.as_reporter()
        self.assertFalse(env.is_frozen())
        # the obligation is closed, but not for them: no banner, and above
        # all not the manager's wording
        self.assertTrue(env.closed_locks())
        self.assertIsNone(env.lock_notice())

    def test_a_frozen_reader_is_told_they_are_frozen(self):
        env = self.create_envelope(self.col)
        self.set_window(-20, -10)
        self.as_reporter()
        notice = env.lock_notice()
        self.assertTrue(notice["frozen"])
        self.assertEqual(list(notice["locks"]), [BASEL])

    def test_a_manager_is_told_why_they_still_have_access(self):
        env = self.create_envelope(self.col)
        self.set_window(-20, -10)
        self.as_manager()
        notice = env.lock_notice()
        self.assertFalse(notice["frozen"])
        self.assertEqual(list(notice["locks"]), [BASEL])

    def test_a_rejected_delivery_leaves_the_collection_free_to_retry(self):
        """The sequence a soft lock has to survive.

        A reporter delivers inside the amnesty, QA rejects it and the
        envelope never completes, so the collection still counts as not
        having reported: the replacement is allowed and can be finished.
        """
        self.set_window(-20, -10, strength="soft", reporting_year=2003)
        rejected = self.create_envelope(self.col)
        rejected.released = 1  # released but the workflow never completed
        rejected.reindexObject()
        self.as_reporter()

        self.assertFalse(self.col.has_reported(2003))
        # a replacement may be created, and the one in hand stays workable
        self.assertEqual(self.col.active_locks(), {})
        self.assertFalse(rejected.is_frozen())

    def report(self, col):
        """Complete a delivery the way has_reported() recognises one"""
        env = self.create_envelope(col)
        env.released = 1
        env.reportingdate = DateTime()
        env.status = "complete"
        env.reindexObject()
        # has_reported() memoises per request and creating the envelope
        # already asked the question. A real delivery is released in a
        # later request, so drop the memo rather than assert against it.
        self.app.REQUEST._reportek_has_reported = None
        return env


class ApplicationsOnLockedEnvelopesTestCase(BaseTest):
    """Applications run as the envelope owner and must not be frozen out.

    RepUtils.manage_as_owner switches to the owner, who on a reporter's
    envelope is a reporter: without a marker the guards would refuse the
    automatic work the lock is supposed to leave running.
    """

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
        self.env = self.create_envelope(self.col)
        self.engine.set_lock(BASEL, kind="migrated")
        # manage_as_owner reads the user off the request itself
        self.app.REQUEST.set("AUTHENTICATED_USER", getSecurityManager().getUser())

    def test_the_owner_marker_lets_a_guarded_method_through(self):
        from OFS.Folder import Folder

        self.env._setObject("scratch", Folder("scratch"))
        self.assertTrue(self.env.is_frozen())
        with self.assertRaises(Unauthorized):
            self.env.manage_delObjects(["scratch"])
        with self.assertRaises(Unauthorized):
            self.env.manage_addFeedback()
        self.assertIn("scratch", self.env.objectIds())

        self.app.REQUEST._reportek_as_owner = True
        self.addCleanup(setattr, self.app.REQUEST, "_reportek_as_owner", False)
        # still frozen, but the guard stands aside for application code
        self.assertTrue(self.env.is_frozen())
        self.env.manage_delObjects(["scratch"])
        self.assertNotIn("scratch", self.env.objectIds())

    def test_the_marker_is_cleared_again(self):
        from Products.Reportek import RepUtils

        seen = {}

        @RepUtils.manage_as_owner
        def probe(envelope):
            seen["inside"] = getattr(envelope.REQUEST, "_reportek_as_owner", False)

        probe(self.env)
        self.assertTrue(seen["inside"])
        self.assertFalse(getattr(self.app.REQUEST, "_reportek_as_owner", False))

    def test_the_marker_is_cleared_even_when_the_application_fails(self):
        from Products.Reportek import RepUtils

        @RepUtils.manage_as_owner
        def explode(envelope):
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            explode(self.env)
        # the old code left the owner's security manager in place here too
        self.assertFalse(getattr(self.app.REQUEST, "_reportek_as_owner", False))
        with self.assertRaises(Unauthorized):
            self.env.manage_addFeedback()

    def test_a_reporter_cannot_raise_the_marker_from_the_web(self):
        """The decorated helpers carry no docstring and no roles, so Zope
        refuses to publish them: the marker is unreachable from a URL."""
        from Products.Reportek.Envelope import Envelope

        for name in ("add_feedback", "delete_feedbacks"):
            with self.subTest(method=name):
                method = getattr(Envelope, name)
                self.assertFalse(getattr(method, "__doc__", None))
                self.assertFalse(hasattr(Envelope, name + "__roles__"))


class PublishedSignatureTestCase(BaseTest):
    """The guard must not hide a method's arguments from the publisher.

    ZPublisher decides what to pass a method by reading its arguments, so a
    *args wrapper leaves it calling activateWorkitem() with nothing and the
    reporter sees a TypeError. Calling the methods directly from Python, as
    the other tests do, cannot catch that.
    """

    @staticmethod
    def guarded_callables():
        """Everything refuse_when_frozen wraps, found rather than listed"""
        import Products.Reportek.Document as Document
        import Products.Reportek.Envelope as Envelope
        import Products.Reportek.Feedback as Feedback
        import Products.Reportek.Hyperlink as Hyperlink
        from Products.Reportek.EnvelopeInstance import EnvelopeInstance
        from Products.Reportek import RepUtils

        guard = RepUtils.refuse_when_frozen.__code__.co_filename
        holders = (
            ("Envelope", Envelope),
            ("Document", Document),
            ("Feedback", Feedback),
            ("Hyperlink", Hyperlink),
            ("Envelope", Envelope.Envelope),
            ("EnvelopeInstance", EnvelopeInstance),
            ("Document", Document.Document),
            ("ReportFeedback", Feedback.ReportFeedback),
        )
        found = {}
        for where, holder in holders:
            for name in dir(holder):
                try:
                    obj = getattr(holder, name)
                except Exception:
                    continue
                wrapped = getattr(obj, "__wrapped__", None)
                if wrapped is None or not callable(obj):
                    continue
                code = getattr(obj, "__code__", None)
                if code is not None and code.co_filename == guard:
                    found[(where, name)] = obj
        return found

    def test_arguments_survive_the_guard(self):
        """Found by inspection, so a newly guarded method is covered too"""
        from inspect import getfullargspec, signature

        guarded = self.guarded_callables()
        self.assertGreater(len(guarded), 15)
        for (where, name), obj in sorted(guarded.items()):
            with self.subTest(method="%s.%s" % (where, name)):
                self.assertEqual(
                    getfullargspec(obj).args,
                    list(signature(obj.__wrapped__).parameters),
                )

    def test_the_publisher_can_call_a_guarded_method(self):
        """The failing path itself: arguments mapped from a request"""
        from ZPublisher.mapply import mapply

        self.createStandardDependencies()
        col = self.addCollection(
            self.app,
            title="C",
            descr="",
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
        env = self.create_envelope(col)
        workitem_id = env.getListOfWorkitems()[0].getId()

        mapply(env.activateWorkitem, (), {"workitem_id": workitem_id})
        self.assertEqual(getattr(env, workitem_id).status, "active")


class NotPublishableTestCase(BaseTest):
    """The lock helpers are for templates, not for URLs.

    A docstring plus public roles is Zope's recipe for publishing something
    to anonymous, and these would hand out the exempt paths, every audience
    message, and in has_reported's case a catalog query on demand.
    """

    HELPERS = (
        ("Collection", "active_locks"),
        ("Collection", "has_reported"),
        ("EnvelopeInstance", "active_locks"),
        ("EnvelopeInstance", "closed_locks"),
        ("EnvelopeInstance", "lock_notice"),
        ("EnvelopeInstance", "lock_body"),
        ("EnvelopeInstance", "is_frozen"),
        ("ReportekEngine", "get_locks"),
        ("ReportekEngine", "get_closed_locks"),
    )

    @staticmethod
    def holder(name):
        from Products.Reportek.Collection import Collection
        from Products.Reportek.EnvelopeInstance import EnvelopeInstance
        from Products.Reportek.ReportekEngine import ReportekEngine

        return {
            "Collection": Collection,
            "EnvelopeInstance": EnvelopeInstance,
            "ReportekEngine": ReportekEngine,
        }[name]

    def test_the_publisher_refuses_them(self):
        from ZPublisher import zpublish_mark

        for where, name in self.HELPERS:
            with self.subTest(helper="%s.%s" % (where, name)):
                fn = getattr(self.holder(where), name)
                self.assertIs(zpublish_mark(fn, None), False)

    def test_templates_can_still_reach_them(self):
        """Marking them unpublishable must not close restricted TAL access"""
        for where, name in self.HELPERS:
            with self.subTest(helper="%s.%s" % (where, name)):
                holder = self.holder(where)
                self.assertIn(
                    getattr(holder, name + "__roles__", "MISSING"),
                    (None, "MISSING"),
                )

    def test_owner_helpers_keep_their_arguments(self):
        """manage_as_owner hid them the same way refuse_when_frozen did"""
        from inspect import getfullargspec

        from Products.Reportek.Envelope import Envelope

        self.assertEqual(getfullargspec(Envelope.add_feedback).args, ["self"])
        self.assertEqual(
            getfullargspec(Envelope.delete_feedbacks).args, ["self", "fb_ids"]
        )

    def test_owner_helpers_are_still_unpublishable(self):
        """Their safety rests on carrying no docstring: do not add @wraps"""
        from Products.Reportek.Envelope import Envelope

        for name in ("add_feedback", "delete_feedbacks"):
            with self.subTest(method=name):
                doc = getattr(Envelope, name).__doc__
                self.assertFalse((doc or "").strip())
