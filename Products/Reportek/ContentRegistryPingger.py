import logging
import pickle
import threading
import time

import requests
from BeautifulSoup import BeautifulSoup as bs
from config import DEPLOYMENT_CDR, REPORTEK_DEPLOYMENT

from Products.Reportek.rabbitmq import send_message

logger = logging.getLogger("Reportek")


class ContentRegistryPingger(object):
    PING_STORE = None

    def __init__(self, api_url, cr_rmq=False):
        self.api_url = api_url
        self.cr_rmq = cr_rmq

    def _log_ping(self, success, message, url, ping_argument=None):
        if not ping_argument or ping_argument == "create":
            action = "update/create"
        elif ping_argument == "delete":
            action = "delete"
        messageBody = self.content_registry_pretty_message(message)
        if success:
            logger.info(
                """Content Registry (%s) pingged OK for the %s of %s. """
                """Response was: %s"""
                % (self.api_url, action, url, messageBody)
            )
        else:
            logger.warning(
                """Content Registry (%s) ping unsuccessful for the %s """
                """of %s. Response was: %s"""
                % (self.api_url, action, url, messageBody)
            )

    def content_registry_ping(
        self, uris, ping_argument=None, envPathName=None, wk=None
    ):
        """Pings the Content Registry to harvest a new envelope almost
        immediately after the envelope is released or revoked
        with the name of the envelope's RDF output
        """

        def parse_uri(uri):
            """Use only http uris for CDR"""
            if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
                new_uri = uri.replace("https://", "http://")
                logger.info(
                    "Original uri: %s has been replaced with uri: %s"
                    % (uri, new_uri)
                )
                uri = new_uri
            return uri

        allOk = True
        ping_res = ""
        http_code = None
        if not ping_argument:
            ping_argument = "create"
        for uri in uris:
            uri = parse_uri(uri)
            success, response = self._content_registry_ping(
                uri, ping_argument=ping_argument
            )
            ping_res = getattr(response, "text", "")
            http_code = getattr(response, "status_code", None)
            self._log_ping(success, ping_res, uri, ping_argument)
            if wk:
                msgs = {
                    True: "CR Ping successful for the {} of {} (HTTP status: {})".format(
                        ping_argument, uri, http_code
                    ),  # noqa
                    False: "CR Ping failed for the {} of {} (HTTP status: {})".format(
                        ping_argument, uri, http_code
                    ),  # noqa
                }
                wk.addEvent(msgs.get(success))
            allOk = allOk and success

        return allOk, ping_res

    def content_registry_ping_async(
        self, uris, ping_argument=None, envPathName=None, wk=None
    ):
        """Delegate this to fire and forget thread
        don't keep the user (browser) waiting
        """

        pingger = threading.Thread(
            target=ContentRegistryPingger.content_registry_ping,
            name="contentRegistryPing",
            args=(self, uris),
            kwargs={
                "ping_argument": ping_argument,
                "envPathName": envPathName,
                "wk": wk,
            },
        )
        pingger.setDaemon(True)
        pingger.start()
        return

    def _content_registry_ping(self, uri, ping_argument=None):
        params = {"uri": uri}
        if ping_argument == "create":
            params["create"] = "true"
        elif ping_argument == "delete":
            params["delete"] = "true"
        if not getattr(self, "cr_rmq", None):
            resp = requests.get(self.api_url, params=params)
            if resp.status_code == 200:
                return (True, resp)
        else:
            options = {}
            options["create"] = ping_argument
            options["service_to_ping"] = self.api_url
            options["obj_url"] = uri
            resp = self.ping_RabbitMQ(options)
            if resp:
                return (True, "Queued")

        return (False, resp)

    @classmethod
    def content_registry_pretty_message(cls, message):
        messageBody = ""
        try:
            if "<html" in message:
                messageBody = bs(message).find("body").text
            elif "<?xml" in message:
                messageBody = bs(message).find("response").text
        except Exception:
            messageBody = message

        return messageBody

    def ping_RabbitMQ(self, options):
        """Ping the CR/SDS service via RabbitMQ"""
        msg = "{create}|{service_to_ping}|{obj_url}".format(**options)
        try:
            send_message(msg, queue="cr_queue")
            return True
        except Exception as err:
            logger.error("Sending '%s' in 'cr_queue' FAILED: %s", msg, err)
