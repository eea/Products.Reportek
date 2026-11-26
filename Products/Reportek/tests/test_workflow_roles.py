"""Users acting on workflow steps directly: the actor recorded is always the
user, and their roles are checked against the step's pull and push roles as
ReportekEngine.workflow_role_check says (off, log, enforce)."""

from unittest.mock import Mock, patch
import base64
import json

from Acquisition import aq_base

from AccessControl.SecurityManagement import newSecurityManager
from ZPublisher.mapply import mapply

from AccessControl import getSecurityManager
from zExceptions import Unauthorized

from Products.Reportek import constants, permissions
from Products.Reportek.RemoteRabbitMQQAApplication import (
    RemoteRabbitMQQAApplication,
)
from Products.Reportek.constants import (
    WORKFLOW_ROLE_CHECK_ENFORCE,
    WORKFLOW_ROLE_CHECK_LOG,
    WORKFLOW_ROLE_CHECK_OFF,
)

from .common import BaseTest
from .utils import simple_addEnvelope

LOGGER = "Products.Reportek.EnvelopeInstance.logger"
USER, PASSWORD = "wf_user", "wf_password"  # betterleaks:allow (test fixture)


class WorkflowTestBase(BaseTest):
    def afterSetUp(self):
        super().afterSetUp()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.engine = getattr(self.app, constants.ENGINE_ID)

    def mode(self, mode):
        self.engine.workflow_role_check = mode

    def assertRefusedByTheCheck(self, name, verdict="refused", **query):
        with patch(LOGGER) as logger:
            with self.assertRaises(Unauthorized, msg=name):
                self.publish_action(name, **query)
        self.assertEqual(logger.log.call_args[0][3], verdict, name)

    def create_envelope(self):
        col = self.app.collection
        self.login()  # test_user_1_
        self.app.REQUEST.AUTHENTICATED_USER = getSecurityManager().getUser()
        simple_addEnvelope(
            col.manage_addProduct["Reportek"],
            "",
            "",
            "2003",
            "2004",
            "",
            "http://rod.eionet.eu.int/localities/1",
            REQUEST=None,
            previous_delivery="",
        )
        [self.env] = col.objectValues("Report Envelope")

    def set_step_roles(self, pull=(), push=()):
        """Configure the workflow engine: which roles may pull / push the
        activity of self.wi, and no others."""
        openflow = self.env.getOpenFlowEngine()
        process = self.env.getInstanceProcessId()
        activity = self.wi.activity_id
        for roles, get, edit in (
            (
                pull,
                openflow.getActivitiesPullableOnRole,
                openflow.editActivitiesPullableOnRole,
            ),
            (
                push,
                openflow.getActivitiesPushableOnRole,
                openflow.editActivitiesPushableOnRole,
            ),
        ):
            configured = get()
            for role in set(configured) | set(roles):
                activities = [
                    a
                    for a in configured.get(role, {}).get(process, [])
                    if a != activity
                ]
                if role in roles:
                    activities.append(activity)
                edit(role, process, activities)


class WorkflowRolesTest(WorkflowTestBase):
    def afterSetUp(self):
        super().afterSetUp()
        self.create_envelope()
        [self.wi] = self.env.objectValues("Workitem")
        self.set_step_roles(pull=["Reporter"])
        self.request = self.app.REQUEST
        self.request.environ["HTTP_ACCEPT"] = constants.CONTENT_TYPE_JSON

    def direct(self, name, **form):
        """As when the request publishes the envelope's method ``name``."""
        self.request.set("PUBLISHED", getattr(self.env, name))
        self.request.form.update(form)
        return getattr(self.env, name)

    def activate(self, **form):
        method = self.direct("activateWorkitem", **form)
        return method(self.wi.id, actor=form.get("actor"), REQUEST=self.request)

    # --- the check ------------------------------------------------------

    def test_log_mode_reports_but_lets_the_user_act(self):
        self.mode(WORKFLOW_ROLE_CHECK_LOG)
        with patch(LOGGER) as logger:
            self.activate()
        self.assertEqual(self.wi.status, "active")
        level, message = logger.log.call_args[0][:2]
        self.assertEqual(logger.log.call_args[0][3], "refused")
        self.assertIn("Workflow role check", message)

    def test_enforce_refuses_a_user_without_the_step_roles(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        with patch(LOGGER):
            with self.assertRaises(Unauthorized):
                self.activate()
        self.assertEqual(self.wi.status, "inactive")

    def test_enforce_lets_a_user_with_a_step_role(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.setRoles(["Reporter"])
        with patch(LOGGER):
            self.activate()
        self.assertEqual(self.wi.status, "active")

    def test_push_roles_count_too(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.set_step_roles(push=["Client"])
        self.setRoles(["Client"])
        with patch(LOGGER):
            self.activate()
        self.assertEqual(self.wi.status, "active")

    def test_the_current_configuration_counts_not_the_workitem_copy(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.set_step_roles(pull=["Client"])
        self.wi.pull_roles = ["Reporter"]  # taken when the step was created
        self.setRoles(["Reporter"])
        with patch(LOGGER):
            with self.assertRaises(Unauthorized):
                self.activate()
        self.setRoles(["Client"])
        with patch(LOGGER):
            self.activate()
        self.assertEqual(self.wi.status, "active")

    def test_managers_always_may(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.setRoles(["Manager"])
        with patch(LOGGER):
            self.activate()
        self.assertEqual(self.wi.status, "active")

    def test_steps_without_roles_stay_open(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.set_step_roles()
        with patch(LOGGER) as logger:
            self.activate()
        self.assertEqual(self.wi.status, "active")
        self.assertEqual(logger.log.call_args[0][3], "allowed (step without roles)")

    def test_off_checks_nothing(self):
        self.mode(WORKFLOW_ROLE_CHECK_OFF)
        with patch(LOGGER) as logger:
            self.activate()
        self.assertEqual(self.wi.status, "active")
        logger.log.assert_not_called()

    def test_code_calls_are_not_checked(self):
        # an application or remote service acting, not the user directly
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.request.set("PUBLISHED", self.env.triggerApplication)
        with patch(LOGGER) as logger:
            self.env.activateWorkitem(self.wi.id, "openflow_engine")
            self.env.completeWorkitem(
                self.wi.id, actor="openflow_engine", REQUEST=self.request
            )
        self.assertEqual(self.wi.status, "complete")
        logger.log.assert_not_called()

    def test_complete_and_inactivate_are_checked(self):
        self.mode(WORKFLOW_ROLE_CHECK_LOG)
        self.env.activateWorkitem(self.wi.id, "openflow_engine")
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        for name in ("inactivateWorkitem", "completeWorkitem"):
            method = self.direct(name)
            with patch(LOGGER):
                with self.assertRaises(Unauthorized, msg=name):
                    method(self.wi.id, REQUEST=self.request)
        self.assertEqual(self.wi.status, "active")

    # --- the actor --------------------------------------------------------

    def test_activate_ignores_an_actor_in_the_request(self):
        self.mode(WORKFLOW_ROLE_CHECK_OFF)
        self.activate(actor="someone_else")
        self.assertEqual(self.wi.actor, "test_user_1_")
        self.assertEqual(self.wi.activation_log[-1]["actor"], "test_user_1_")

    def test_complete_ignores_an_actor_in_the_request(self):
        self.mode(WORKFLOW_ROLE_CHECK_OFF)
        self.activate()
        method = self.direct("completeWorkitem", actor="someone_else")
        method(self.wi.id, actor="someone_else", REQUEST=self.request)
        self.assertEqual(self.wi.completion_log[-1]["actor"], "test_user_1_")

    def test_code_names_the_actor(self):
        self.mode(WORKFLOW_ROLE_CHECK_OFF)
        self.env.activateWorkitem(self.wi.id, "openflow_engine")
        self.request.set("PUBLISHED", self.env.triggerApplication)
        # a form value must not win over what the code says
        self.request.form["actor"] = "someone_else"
        self.env.completeWorkitem(
            self.wi.id, actor="openflow_engine", REQUEST=self.request
        )
        self.assertEqual(self.wi.completion_log[-1]["actor"], "openflow_engine")

    def test_actor_set_by_code_on_the_request(self):
        self.mode(WORKFLOW_ROLE_CHECK_OFF)
        self.env.activateWorkitem(self.wi.id, "openflow_engine")
        self.request.set("PUBLISHED", self.env.triggerApplication)
        self.request.form["actor"] = "someone_else"
        self.request.set("actor", "openflow_engine")
        self.env.completeWorkitem(self.wi.id, REQUEST=self.request)
        self.assertEqual(self.wi.completion_log[-1]["actor"], "openflow_engine")

    def test_without_a_request_the_engine_acts(self):
        self.mode(WORKFLOW_ROLE_CHECK_OFF)
        self.env.activateWorkitem(self.wi.id, "openflow_engine")
        self.env.completeWorkitem(self.wi.id)
        self.assertEqual(self.wi.completion_log[-1]["actor"], "openflow_engine")


class WorkflowRoleCheckSettingTest(WorkflowTestBase):
    def afterSetUp(self):
        super().afterSetUp()
        self.engine._manage_properties = Mock(return_value="page")

    def save(self, value):
        # the other fields the properties form always sends
        self.engine.REQUEST.set("rdf_export_envs_age", "")
        self.engine.REQUEST.set("workflow_role_check", value)
        self.engine.REQUEST.environ["REQUEST_METHOD"] = "POST"
        self.engine.REQUEST["REQUEST_METHOD"] = "POST"
        self.engine.manage_properties()

    def test_default_is_log_only(self):
        self.assertEqual(self.engine.workflow_role_check, WORKFLOW_ROLE_CHECK_LOG)

    def test_saved_from_the_properties_page(self):
        self.save("enforce")
        self.assertEqual(self.engine.workflow_role_check, "enforce")
        self.save("nonsense")
        self.assertEqual(self.engine.workflow_role_check, "enforce")


class PublishedTestBase(WorkflowTestBase):
    """Through the publisher's own traversal and argument mapping: the method
    is what the request publishes, as when a user follows a link."""

    def afterSetUp(self):
        super().afterSetUp()
        self.create_envelope()
        [self.wi] = self.env.objectValues("Workitem")
        self.set_step_roles(pull=["Reporter"])
        # a user who may use the workflow here but holds no step role
        self.env.manage_permission(
            permissions.use_openflow, ["Member", "Manager"], acquire=1
        )
        self.app.__ac_roles__ = tuple(set(self.app.__ac_roles__) | {"Reporter"})
        self.set_user_roles(["Member"])

    def set_user_roles(self, roles):
        acl_users = self.app.acl_users
        if USER in acl_users.getUserNames():
            acl_users.userFolderEditUser(USER, PASSWORD, roles, [])
        else:
            acl_users.userFolderAddUser(USER, PASSWORD, roles, [])

    def publish_action(self, name, **query):
        request = self.app.REQUEST
        request.environ["HTTP_ACCEPT"] = constants.CONTENT_TYPE_JSON
        request.form.update(query, workitem_id=self.wi.id)
        request._auth = (
            "Basic " + base64.b64encode(("%s:%s" % (USER, PASSWORD)).encode()).decode()
        )
        # as the publisher does: traversal starts from the application
        request["PARENTS"] = [self.app]
        published = request.traverse("/%s/%s" % (self.env.absolute_url(1), name))
        newSecurityManager(request, request["AUTHENTICATED_USER"])
        return mapply(published, (), request)


class WorkflowRolesPublishedTest(PublishedTestBase):
    def test_published_method_is_seen_as_direct(self):
        self.mode(WORKFLOW_ROLE_CHECK_LOG)
        with patch(LOGGER) as logger:
            self.publish_action("activateWorkitem", actor="mallory")
        self.assertEqual(self.wi.status, "active")
        self.assertEqual(self.wi.actor, USER)
        self.assertEqual(logger.log.call_args[0][3], "refused")

    def test_published_activate_is_refused_when_enforced(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        with patch(LOGGER) as logger:
            with self.assertRaises(Unauthorized):
                self.publish_action("activateWorkitem")
        # refused by the role check, not by the publisher
        self.assertEqual(logger.log.call_args[0][3], "refused")
        self.assertEqual(self.wi.status, "inactive")

    def test_published_activate_with_the_step_role(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.set_user_roles(["Member", "Reporter"])
        with patch(LOGGER):
            self.publish_action("activateWorkitem")
        self.assertEqual(self.wi.status, "active")

    def test_the_assigned_user_may_deactivate(self):
        # as the operations menu offers it: the step is theirs, roles or not
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.env.activateWorkitem(self.wi.id, USER)
        self.assertEqual(self.wi.actor, USER)
        with patch(LOGGER) as logger:
            self.publish_action("inactivateWorkitem")
        self.assertEqual(self.wi.status, "inactive")
        self.assertEqual(logger.log.call_args[0][3], "allowed (assigned to them)")

    def test_others_may_not_deactivate(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.env.activateWorkitem(self.wi.id, "someone_else")
        self.assertRefusedByTheCheck("inactivateWorkitem")
        self.assertEqual(self.wi.status, "active")

    # --- the other ways of moving a step ---------------------------------

    def test_dummy_activity_cannot_complete_a_step(self):
        # the way around enforce mode the audit found
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.assertRefusedByTheCheck("manageDummyActivity")
        self.assertEqual(self.wi.status, "inactive")
        self.assertEqual(len(self.env.objectIds("Workitem")), 1)

    def test_step_runners_follow_the_step_roles(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.assertRefusedByTheCheck("startAutomaticApplication")
        self.assertEqual(self.wi.status, "inactive")
        self.set_user_roles(["Member", "Reporter"])
        with patch(LOGGER):
            self.publish_action("manageDummyActivity")
        self.assertEqual(self.wi.status, "complete")

    def test_administrative_actions_are_for_managers(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        # even holding the step role
        self.set_user_roles(["Member", "Reporter"])
        for name, query in (
            ("falloutWorkitem", {}),
            ("forwardWorkitem", {}),
            ("suspendWorkitem", {}),
            ("resumeWorkitem", {}),
            ("assignWorkitem", {"actor": "someone"}),
            ("unassignWorkitem", {}),
        ):
            self.assertRefusedByTheCheck(name, "refused (managers only)", **query)
        self.assertEqual(self.wi.status, "inactive")
        with patch(LOGGER) as logger:
            with self.assertRaises(Unauthorized):
                self.publish_action("startInstance")
        self.assertEqual(logger.log.call_args[0][3], "refused (managers only)")

    def test_managers_may_use_the_administrative_actions(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.set_user_roles(["Manager"])
        with patch(LOGGER):
            self.publish_action("falloutWorkitem")
        self.assertEqual(self.wi.status, "fallout")

    def test_log_mode_only_reports_administrative_actions(self):
        self.mode(WORKFLOW_ROLE_CHECK_LOG)
        with patch(LOGGER) as logger:
            self.publish_action("falloutWorkitem")
        self.assertEqual(self.wi.status, "fallout")
        self.assertEqual(logger.log.call_args[0][3], "refused (managers only)")


class QAServiceAccountTest(PublishedTestBase):
    """QA results come as the body of a request to one of several URLs; the
    RabbitMQ QA application checks the account wherever it reads them."""

    def afterSetUp(self):
        super().afterSetUp()
        self.app._setObject(
            "qa_app",
            RemoteRabbitMQQAApplication(
                "qa_app", "", "", "", "", "", "token", "the_app"
            ),
        )
        self.app.manage_permission(
            permissions.use_openflow, ["Member", "Manager"], acquire=1
        )
        self.wi.status = "active"
        self.env.wf_status = "hybrid"
        self.handle_result = Mock()

    def deliver(self, name="forwardState", body=None, **query):
        if body is None:
            body = {"uuid": str(self.wi.UUID), "jobId": "the-job"}
        self.app.REQUEST.other["BODY"] = json.dumps(body)
        metadata = {
            "requests": {"published": True},
            "jobs_summary": {},
            "number_of_jobs": 2,
        }
        app_class = RemoteRabbitMQQAApplication
        with patch.object(
            aq_base(self.env).__class__, "getApplicationUrl", return_value="/qa_app"
        ), patch.object(
            app_class, "get_act_metadata", return_value=metadata
        ), patch.object(
            app_class, "update_act_metadata"
        ), patch.object(
            app_class, "handle_result", self.handle_result
        ):
            return self.publish_action(name, **query)

    def assertVerdict(self, logger, verdict):
        calls = [c[0] for c in logger.log.call_args_list if "QA service" in c[0][1]]
        self.assertEqual([c[3] for c in calls], [verdict])

    def test_other_accounts_are_refused_when_enforced(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.engine.qa_service_accounts = ("qa_consumer",)
        with patch(LOGGER) as logger:
            with self.assertRaises(Unauthorized):
                self.deliver()
        self.assertVerdict(logger, "refused (not a QA service account)")
        self.handle_result.assert_not_called()

    def test_every_url_reading_results_is_checked(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        for name, query in (
            ("forwardState", {}),
            ("triggerApplication", {"p_workitem_id": self.wi.id}),
            ("qa_app/callApplication", {}),
        ):
            with patch(LOGGER) as logger:
                with self.assertRaises(Unauthorized, msg=name):
                    self.deliver(name, **query)
            self.assertVerdict(logger, "refused (not a QA service account)")
        self.handle_result.assert_not_called()

    def test_trigger_application_payload_is_not_published(self):
        self.set_user_roles(["Manager"])
        with self.assertRaises(Unauthorized):
            self.deliver("triggerApplicationPayload", p_workitem_id=self.wi.id)
        self.handle_result.assert_not_called()

    def test_the_qa_service_account_delivers(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.engine.qa_service_accounts = ("qa_consumer", USER)
        with patch(LOGGER) as logger:
            self.deliver()
        self.assertVerdict(logger, "allowed (QA service account)")
        self.handle_result.assert_called_once()

    def test_managers_may_deliver(self):
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        self.set_user_roles(["Manager"])
        with patch(LOGGER) as logger:
            self.deliver()
        self.assertVerdict(logger, "allowed (manager)")
        self.handle_result.assert_called_once()

    def test_log_mode_only_reports(self):
        self.mode(WORKFLOW_ROLE_CHECK_LOG)
        with patch(LOGGER) as logger:
            self.deliver()
        self.assertVerdict(logger, "refused (not a QA service account)")
        self.handle_result.assert_called_once()

    def test_requests_without_results_are_not_checked(self):
        # moving the envelope along, or another JSON body
        self.mode(WORKFLOW_ROLE_CHECK_ENFORCE)
        for body in ({}, {"other": "data"}):
            with patch(LOGGER) as logger:
                self.deliver(body=body)
            checks = [c for c in logger.log.call_args_list if "QA service" in c[0][1]]
            self.assertEqual(checks, [], body)
        self.handle_result.assert_not_called()

    def test_the_workitem_uuid_is_not_readable(self):
        from AccessControl.ZopeGuards import guarded_getattr

        with self.assertRaises(Unauthorized):
            self.publish_action("%s/UUID" % self.wi.getId())
        newSecurityManager(
            None, self.app.acl_users.getUser(USER).__of__(self.app.acl_users)
        )
        with self.assertRaises(Unauthorized):
            guarded_getattr(self.wi, "UUID")
        # code still compares it, as for the QA service's results
        self.assertTrue(str(self.wi.UUID))


class QAServiceAccountsSettingTest(WorkflowTestBase):
    def afterSetUp(self):
        super().afterSetUp()
        self.engine._manage_properties = Mock(return_value="page")

    def save(self, **form):
        request = self.engine.REQUEST
        request.set("rdf_export_envs_age", "")
        request["REQUEST_METHOD"] = "POST"
        request.form.update(form)
        for key, value in form.items():
            request.set(key, value)
        self.engine.manage_properties()

    def test_empty_by_default(self):
        self.assertEqual(tuple(self.engine.qa_service_accounts), ())

    def test_saved_from_the_properties_page(self):
        self.save(qa_service_accounts=["qa_consumer", " ", " other "])
        self.assertEqual(self.engine.qa_service_accounts, ("qa_consumer", "other"))
        # a form without the field leaves it alone
        self.engine.REQUEST.form.pop("qa_service_accounts")
        self.save(workflow_role_check="log")
        self.assertEqual(self.engine.qa_service_accounts, ("qa_consumer", "other"))
