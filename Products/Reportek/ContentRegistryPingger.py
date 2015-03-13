from BeautifulSoup import BeautifulSoup as bs
import logging
logger = logging.getLogger("Reportek")
import requests
import threading
import time
from config import *
from constants import PING_ENVELOPES_REDIS_KEY
import pickle

class ContentRegistryPingger(object):

    if REPORTEK_DEPLOYMENT == DEPLOYMENT_CDR:
        import redis
        PING_STORE = redis.Redis(db=REDIS_DATABASE)
    else:
        PING_STORE = None

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
            logger.warning("Content Registry (%s) ping unsuccessful for the %s of %s\nResponse was: %s"
                            % (self.api_url, action, url, messageBody))

    def content_registry_ping(self, uris, ping_argument=None, envPathName=None):
        """ Pings the Content Registry to harvest a new envelope almost immediately after the envelope is released or revoked
            with the name of the envelope's RDF output
        """
        allOk = True
        if not ping_argument:
            ping_argument = 'create'
        if envPathName and self.PING_STORE:
            ts = self._start_ping(envPathName, op=ping_argument)
        for uri in uris:
            success, message = self._content_registry_ping(uri, ping_argument=ping_argument)
            self._log_ping(success, message, uri, ping_argument)
            allOk = allOk and success
            if envPathName and self.PING_STORE and not self._check_ping(envPathName, ts):
                allOk = False
                break
        if envPathName and self.PING_STORE:
            self._stop_ping(envPathName, ts)
        return allOk

    def content_registry_ping_async(self, uris, ping_argument=None, envPathName=None):
        # delegate this to fire and forget thread - don't keep the user (browser) waiting

        pingger = threading.Thread(target=ContentRegistryPingger.content_registry_ping,
                         name='contentRegistryPing',
                         args=(self, uris),
                         kwargs={'ping_argument': ping_argument,
                                 'envPathName': envPathName})
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

    def _start_ping(self, envPathName, op='up'):
        """ `envPingStatus` string containing the path of the envelope to work on
        `op` is the operation that will the envelope wil be pingged for
        """
        # lock the store globaly?
        # FIXME we'll try without a lock for the begining
        #pingStoreLock.aquire()
        ts = time.time()
        val = {'op': op, 'ts': ts}
        val = pickle.dumps(val)
        # start no matter what. expect the other to stop when he sees dirty ts
        self.PING_STORE.hset(PING_ENVELOPES_REDIS_KEY, envPathName, val)
        return ts

    def _check_ping(self, envPathName, ts):
        envPingStatus = self.PING_STORE.hget(PING_ENVELOPES_REDIS_KEY, envPathName)
        envPingStatus = pickle.loads(envPingStatus)
        # also check if a later task already finished and reset the ts
        if envPingStatus['ts'] > ts or envPingStatus['ts'] == 0:
            # got dirty, somebody else started doing stuff on this envelope
            return False
        return True

    def _stop_ping(self, envPathName, ts):
        envPingStatus = self.PING_STORE.hget(PING_ENVELOPES_REDIS_KEY, envPathName)
        if envPingStatus:
            envPingStatus = pickle.loads(envPingStatus)
            # not us! don't reset
            if envPingStatus['ts'] != ts:
                return
            else:
                envPingStatus['op'] = None
                envPingStatus['ts'] = 0
        else:
            envPingStatus = {'op': None, 'ts': 0}
        envPingStatus = pickle.dumps(envPingStatus)
        self.PING_STORE.hset(PING_ENVELOPES_REDIS_KEY, envPathName, envPingStatus)
