from BeautifulSoup import BeautifulSoup as bs
import logging
logger = logging.getLogger("Reportek")
import requests
import threading

class ContentRegistryPingger(object):

    def __init__(self, api_url):
        self.api_url = api_url

    def _log_ping(self, success, message, url, ping_argument=None):
        if not ping_argument or ping_argument == 'create':
            action = 'update/create'
        elif ping_argument == 'delete':
            action = 'delete'
        messageBody = self.content_registry_pretty_message(message)
        if success:
            logger.info("Content Registry (%s) pingged OK for the %s of %s\nResponse was: %s"
                        % (self.api_url, action, url, messageBody))
        else:
            logger.warning("Content Registry (%s) ping unsuccesfull for the %s of %s\nResponse was: %s"
                            % (self.api_url, action, url, messageBody))

    def content_registry_ping(self, uris, ping_argument=None):
        """ Pings the Content Registry to harvest a new envelope almost immediately after the envelope is released or revoked
            with the name of the envelope's RDF output
        """
        allOk = True
        if not ping_argument:
            ping_argument = 'create'
        for uri in uris:
            success, message = self._content_registry_ping(uri, ping_argument=ping_argument)
            self._log_ping(success, message, uri, ping_argument)
            allOk = allOk and success
        return allOk

    def content_registry_ping_async(self, uris, ping_argument=None):
        # delegate this to fire and forget thread - don't keep the user (browser) waiting
        pingger = threading.Thread(target=ContentRegistryPingger.content_registry_ping,
                         name='contentRegistryPing',
                         args=(self, uris),
                         kwargs={'ping_argument': ping_argument})
        pingger.setDaemon(True)
        pingger.start()
        return

    def _content_registry_ping(self, uri, ping_argument=None):
        params = {'uri': uri}
        if ping_argument == 'create':
            params['create'] = 'true'
        elif ping_argument == 'delete':
            params['delete'] = 'true'
        resp = requests.get(self.api_url, params=params)
        if resp.status_code == 200:
            return (True, resp.text)
        return (False, resp.text)

    @classmethod
    def content_registry_pretty_message(cls, message):
        try:
            if '<html' in message:
                messageBody = bs(message).find('body').text
            elif '<?xml' in message:
                messageBody = bs(message).find('response').text
        except:
            messageBody = message

        return messageBody


