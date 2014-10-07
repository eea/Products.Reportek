from mock import Mock, call
import time
import pickle

from Products.Reportek import ContentRegistryPingger
from common import BaseTest, ConfigureReportek
from utils import mysleep, MockRedis
from Products.Reportek.constants import PING_ENVELOPES_KEY


class ContentRegistryPinggerTest(BaseTest, ConfigureReportek):

    def afterSetUp(self):
        super(ContentRegistryPinggerTest, self).afterSetUp()
        self.engine.cr_api_url = 'http://none'
        self.pingger = self.engine.contentRegistryPingger
        self.assertTrue(bool(self.pingger))
        ContentRegistryPingger.requests.get = Mock()
        self.pingger.PING_STORE = MockRedis()

    def test_ping_create(self):
        ok_message = '''<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>'''
        uri = 'http://some_uri'
        ContentRegistryPingger.requests.get.return_value = Mock(status_code=200, text=ok_message)
        self.pingger._content_registry_ping(uri, ping_argument='create')

        self.assertTrue(ContentRegistryPingger.requests.get.called)
        call_args_list = ContentRegistryPingger.requests.get.call_args_list
        self.assertIn(call(self.engine.cr_api_url, params={'uri': uri, 'create': 'true'}),
                      call_args_list)

    def test_ping_harvest(self):
        ok_message = '''<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>'''
        uri = 'http://some_uri'
        ContentRegistryPingger.requests.get.return_value = Mock(status_code=200, text=ok_message)
        self.pingger._content_registry_ping(uri)

        self.assertTrue(ContentRegistryPingger.requests.get.called)
        call_args_list = ContentRegistryPingger.requests.get.call_args_list
        self.assertIn(call(self.engine.cr_api_url, params={'uri': uri}),
                      call_args_list)

    def test_ping_delete(self):
        ok_message = '''<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>'''
        uri = 'http://some_uri'
        ContentRegistryPingger.requests.get.return_value = Mock(status_code=200, text=ok_message)
        self.pingger._content_registry_ping(uri, ping_argument='delete')

        self.assertTrue(ContentRegistryPingger.requests.get.called)
        call_args_list = ContentRegistryPingger.requests.get.call_args_list
        self.assertIn(call(self.engine.cr_api_url, params={'uri': uri, 'delete': 'true'}),
                      call_args_list)

    def test_ping_many_sync(self):
        ok_message = '''<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>'''
        uri1 = 'http://some_uri1'
        uri2 = 'http://some_uri2'
        self.pingger._content_registry_ping = Mock(return_value=(200, ok_message))
        self.pingger.content_registry_ping([uri1, uri2], ping_argument='create')

        self.assertTrue(self.pingger._content_registry_ping.called)
        call_args_list = self.pingger._content_registry_ping.call_args_list
        self.assertIn(call(uri1, ping_argument='create'), call_args_list)
        self.assertIn(call(uri2, ping_argument='create'), call_args_list)

    def test_ping_many_async(self):
        ok_message = '''<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>'''
        envName = 'http://'
        uri1 = 'http://some_uri1'
        uri2 = 'http://some_uri2'
        self.pingger._content_registry_ping = Mock(return_value=(200, ok_message))
        self.pingger.content_registry_ping_async([uri1, uri2], ping_argument='create',
                                                 envPathName=envName)
        mysleep(0.05)

        self.assertTrue(self.pingger._content_registry_ping.called)
        call_args_list = self.pingger._content_registry_ping.call_args_list
        self.assertIn(call(uri1, ping_argument='create'), call_args_list)
        self.assertIn(call(uri2, ping_argument='create'), call_args_list)
        envStats = self.pingger.PING_STORE.hget(PING_ENVELOPES_KEY, envName)
        envStats = pickle.loads(envStats)
        # check that the finished thread cleaned after itself
        self.assertEqual(envStats['op'], None)
        self.assertEqual(envStats['ts'], 0)

    def test_ping_many_async_overlap(self):
        ok_message = '''<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>'''
        envName = 'http://'
        uri1 = 'http://some_uri1'
        uri2 = 'http://some_uri2'
        def collide(uri, ping_argument=None):
            # stick a collision here
            if uri == uri1:
                val = {'op': 'delete', 'ts': time.time()}
                val = pickle.dumps(val)
                self.pingger.PING_STORE.hset(PING_ENVELOPES_KEY, envName, val)
            return 200, ok_message

        self.pingger._content_registry_ping = Mock(return_value=(200, ok_message), side_effect=collide)
        self.pingger.content_registry_ping_async([uri1, uri2], ping_argument='create',
                                                 envPathName=envName)
        mysleep(0.05)

        self.assertTrue(self.pingger._content_registry_ping.called)
        call_args_list = self.pingger._content_registry_ping.call_args_list
        self.assertIn(call(uri1, ping_argument='create'), call_args_list)
        self.assertNotIn(call(uri2, ping_argument='create'), call_args_list)
        envStats = self.pingger.PING_STORE.hget(PING_ENVELOPES_KEY, envName)
        envStats = pickle.loads(envStats)
        # check that the interrupted thread did not chenged status
        self.assertEqual(envStats['op'], 'delete')
        # the 'interrupting thread' behalves as it did not finish
        self.assertNotEqual(envStats['ts'], 0)

    def test_ping_many_async_overlap_finished(self):
        ok_message = '''<?xml version="1.0"?>
        <response>
            <message>URL added to the urgent harvest queue: http://cdrtest.eionet.europa.eu/ro/colu0vgwa/colu0vgdq/envu0vgka/rdf</message>
            <flerror>0</flerror>
        </response>'''
        envName = 'http://'
        uri1 = 'http://some_uri1'
        uri2 = 'http://some_uri2'
        def collide(uri, ping_argument=None):
            # stick a collision here
            if uri == uri1:
                val = {'op': None, 'ts': 0}
                val = pickle.dumps(val)
                self.pingger.PING_STORE.hset(PING_ENVELOPES_KEY, envName, val)
            return 200, ok_message

        self.pingger._content_registry_ping = Mock(return_value=(200, ok_message), side_effect=collide)
        self.pingger.content_registry_ping_async([uri1, uri2], ping_argument='create',
                                                 envPathName=envName)
        mysleep(0.05)

        self.assertTrue(self.pingger._content_registry_ping.called)
        call_args_list = self.pingger._content_registry_ping.call_args_list
        self.assertIn(call(uri1, ping_argument='create'), call_args_list)
        self.assertNotIn(call(uri2, ping_argument='create'), call_args_list)
        envStats = self.pingger.PING_STORE.hget(PING_ENVELOPES_KEY, envName)
        envStats = pickle.loads(envStats)
        # check that the interrupted thread did not chenged status
        self.assertEqual(envStats['op'], None)
        # the 'interrupting thread' behalves as it did finish
        self.assertEqual(envStats['ts'], 0)
