# flake8: noqa
from mock import Mock, call, patch
import time
import pickle

from Products.Reportek import ContentRegistryPingger
from Products.Reportek.config import REPORTEK_DEPLOYMENT, DEPLOYMENT_CDR
from common import BaseTest, ConfigureReportek
from utils import (
    mysleep,
    create_upload_file,
    simple_addEnvelope,
    add_hyperlink,
    add_document,
    add_feedback,
)
from Products.Reportek import constants, Converters
from AccessControl import getSecurityManager


class ContentRegistryPinggerTest(BaseTest, ConfigureReportek):
    def afterSetUp(self):
        super(ContentRegistryPinggerTest, self).afterSetUp()
        self.engine.cr_api_url = "http://none"
        self.pingger = self.engine.contentRegistryPingger
        self.assertTrue(bool(self.pingger))
        ContentRegistryPingger.requests.get = Mock()

    def test_ping_create(self):
        ok_message = """<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>"""
        uri = "http://some_uri"
        ContentRegistryPingger.requests.get.return_value = Mock(
            status_code=200, text=ok_message
        )
        self.pingger._content_registry_ping(uri, ping_argument="create")

        self.assertTrue(ContentRegistryPingger.requests.get.called)
        call_args_list = ContentRegistryPingger.requests.get.call_args_list
        self.assertIn(
            call(
                self.engine.cr_api_url, params={"uri": uri, "create": "true"}
            ),
            call_args_list,
        )

    def test_ping_harvest(self):
        ok_message = """<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>"""
        uri = "http://some_uri"
        ContentRegistryPingger.requests.get.return_value = Mock(
            status_code=200, text=ok_message
        )
        self.pingger._content_registry_ping(uri)

        self.assertTrue(ContentRegistryPingger.requests.get.called)
        call_args_list = ContentRegistryPingger.requests.get.call_args_list
        self.assertIn(
            call(self.engine.cr_api_url, params={"uri": uri}), call_args_list
        )

    def test_ping_delete(self):
        ok_message = """<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>"""
        uri = "http://some_uri"
        ContentRegistryPingger.requests.get.return_value = Mock(
            status_code=200, text=ok_message
        )
        self.pingger._content_registry_ping(uri, ping_argument="delete")

        self.assertTrue(ContentRegistryPingger.requests.get.called)
        call_args_list = ContentRegistryPingger.requests.get.call_args_list
        self.assertIn(
            call(
                self.engine.cr_api_url, params={"uri": uri, "delete": "true"}
            ),
            call_args_list,
        )

    def test_ping_many_sync(self):
        ok_message = """<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>"""
        uri1 = "http://some_uri1"
        uri2 = "http://some_uri2"
        self.pingger._content_registry_ping = Mock(
            return_value=(200, ok_message)
        )
        self.pingger.content_registry_ping(
            [uri1, uri2], ping_argument="create"
        )

        self.assertTrue(self.pingger._content_registry_ping.called)
        call_args_list = self.pingger._content_registry_ping.call_args_list
        self.assertIn(call(uri1, ping_argument="create"), call_args_list)
        self.assertIn(call(uri2, ping_argument="create"), call_args_list)


class InitCRTest(BaseTest, ConfigureReportek):
    def afterSetUp(self):
        super(InitCRTest, self).afterSetUp()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.assertTrue(
            hasattr(self.app, "collection"), "Collection did not get created"
        )
        self.assertNotEqual(self.app.collection, None)
        col = self.app.collection
        self.login()  # Login as test_user_1_
        user = getSecurityManager().getUser()
        self.app.REQUEST.AUTHENTICATED_USER = user
        with patch("Products.Reportek.RepUtils.generate_id") as gen_id_mock:
            gen_id_mock.side_effect = ["envId1", "envId2"]
            self.envelope = simple_addEnvelope(
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
            self.second_envelope = simple_addEnvelope(
                col.manage_addProduct["Reportek"],
                "a second envelope",
                "",
                "2005",
                "2009",
                "",
                "http://rod.eionet.eu.int/localities/2",
                REQUEST=None,
                previous_delivery="",
            )

        self.engine.cr_api_url = "http://none"
        self.pingger = self.engine.contentRegistryPingger
        self.assertTrue(bool(self.pingger))
        # add subobjects of type document, feedback, hyperlink
        content = "test content for our document"
        self.doc = add_document(
            self.envelope, create_upload_file(content, "foo.txt")
        )
        feedbacktext = "feedback text"
        setattr(
            self.root.getPhysicalRoot(),
            constants.CONVERTERS_ID,
            Converters.Converters(),
        )
        safe_html = Mock(convert=Mock(return_value=Mock(text=feedbacktext)))
        getattr(
            self.root.getPhysicalRoot(), constants.CONVERTERS_ID
        ).__getitem__ = Mock(return_value=safe_html)
        self.feed = add_feedback(self.envelope, feedbacktext)
        self.link = add_hyperlink(self.envelope, "hyper/link")

        self.engine.cr_api_url = "http://none"
        self.pingger = self.engine.contentRegistryPingger
        self.assertTrue(bool(self.pingger))
