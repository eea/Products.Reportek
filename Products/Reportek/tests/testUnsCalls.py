import unittest
from mock import Mock, patch, MagicMock
from Products.Reportek.constants import DF_URL_PREFIX


mock_dataflow = {
    'terminated': '0',
    'PK_RA_ID': '572',
    'SOURCE_TITLE': 'EEA AMP',
    'details_url': DF_URL_PREFIX + '572',
    'TITLE': 'Corine Land Cover 2006',
    'uri': DF_URL_PREFIX + '572',
    'LAST_UPDATE': '2008-03-05',
    'PK_SOURCE_ID': '499',
}

mock_localities = {
    'ie': {'iso': 'IE', 'name': 'Ireland',
           'uri': 'http://rod.eionet.eu.int/spatial/20'},
    'es': {'iso': 'ES', 'name': 'Spain',
           'uri': 'http://rod.eionet.eu.int/spatial/35'},
}


class UNSCallsTest(unittest.TestCase):

    def setUp(self):
        from Products.Reportek.ReportekEngine import ReportekEngine
        xmlrpc_patch = patch('Products.Reportek.ReportekEngine.xmlrpclib')
        self._patches = [xmlrpc_patch]
        self.xmlrpc_server = Mock()
        xmlrpc_patch.start().ServerProxy.return_value = self.xmlrpc_server
        xmlrpc_patch.start().Server.return_value = self.xmlrpc_server
        ReportekEngine.uns_notifications_enabled = MagicMock(return_value=True)
        self.engine = ReportekEngine()
        self.engine.UNS_server = 'http://uns.example.com'
        self.engine.UNS_channel_id = '132547698'
        self.engine.UNS_username = 'mr-testy'
        self.engine.UNS_username = 'his-test-pw'
        self.set_request_user('someone')

    def set_request_user(self, user_id):
        mock_user = Mock()
        mock_user.getUserName.return_value = user_id
        self.engine.REQUEST = {'AUTHENTICATED_USER': mock_user}

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_anonymous_user_can_not_subscribe(self):
        self.set_request_user('Anonymous User')
        self.assertFalse(self.engine.canUserSubscribeToUNS())

    def test_user_can_subscribe(self):
        canSubscribe = self.xmlrpc_server.UNSService.canSubscribe
        canSubscribe.return_value = True
        self.assertTrue(self.engine.canUserSubscribeToUNS('someone'))
        canSubscribe.assertCalledOnceWith('132547698', 'someone')

    def test_user_can_not_subscribe(self):
        canSubscribe = self.xmlrpc_server.UNSService.canSubscribe
        canSubscribe.return_value = False
        self.assertFalse(self.engine.canUserSubscribeToUNS('someone'))
        canSubscribe.assert_called_once_with('132547698', 'someone')

    def test_subscribe_to_country(self):
        event = "Envelope release"
        country = "es"
        self.engine.subscribeToUNS(filter_country=country,
                                   filter_event_types=[event])

        makeSubscription = self.xmlrpc_server.UNSService.makeSubscription
        makeSubscription.assert_called_once_with('132547698', 'someone', [
            {'http://rod.eionet.europa.eu/schema.rdf#event_type': event,
             'http://rod.eionet.europa.eu/schema.rdf#locality': country},
        ])

    @patch('Products.Reportek.DataflowsManager.DataflowsManager.dataflow_lookup')
    def test_subscribe_to_dataflow(self, mock_dataflow_lookup):
        event = "Envelope release"
        mock_dataflow_lookup.return_value = mock_dataflow
        self.engine.subscribeToUNS(dataflow_uris=[mock_dataflow['uri']],
                                   filter_event_types=[event])

        makeSubscription = self.xmlrpc_server.UNSService.makeSubscription
        makeSubscription.assert_called_once_with('132547698', 'someone', [
            {'http://rod.eionet.europa.eu/schema.rdf#event_type': event,
             'http://rod.eionet.europa.eu/schema.rdf#obligation': mock_dataflow['TITLE']},
        ])

    @patch('Products.Reportek.DataflowsManager.DataflowsManager.dataflow_lookup')
    def test_subscribe_to_country_and_dataflow(self, mock_dataflow_lookup):
        event = "Envelope release"
        mock_dataflow_lookup.return_value = mock_dataflow
        country = "es"
        self.engine.subscribeToUNS(filter_country=country,
                                   dataflow_uris=[mock_dataflow['uri']],
                                   filter_event_types=[event])

        makeSubscription = self.xmlrpc_server.UNSService.makeSubscription
        makeSubscription.assert_called_once_with('132547698', 'someone', [
            {'http://rod.eionet.europa.eu/schema.rdf#event_type': event,
             'http://rod.eionet.europa.eu/schema.rdf#obligation': mock_dataflow['TITLE'],
             'http://rod.eionet.europa.eu/schema.rdf#locality': country},
        ])

    def test_subscribe_return_success(self):
        ret = self.engine.subscribeToUNS()
        self.assertEqual(ret, (1, ''))

    def test_subscribe_return_error(self):
        msg = 'Fail :('
        makeSubscription = self.xmlrpc_server.UNSService.makeSubscription
        makeSubscription.side_effect = ValueError(msg)
        ret = self.engine.subscribeToUNS()
        self.assertEqual(ret, (0, msg))

    @patch('Products.Reportek.ReportekEngine.time')
    @patch('Products.Reportek.ReportekEngine.strftime')
    def test_send_notification_to_uns(self, mock_strftime, mock_time):
        from utils import create_fake_root
        from Products.Reportek.Envelope import Envelope

        envelope_uri = 'http://example.com/my/envelope'
        event = "Envelope release"
        label = "The test envelope has been released, ypee!"
        mock_time.return_value = 1338217590.558348
        mock_strftime.return_value = '2012-May-28 18:06:30'

        root = create_fake_root()
        process = Mock()
        e = Envelope(process, '', '', '', '', '', '', '', '')
        e._content_registry_ping = Mock()
        e.id = 'envelope'
        e.dataflow_uris = [mock_dataflow['uri']]
        e.country = mock_localities['es']['uri']
        e.localities_table = Mock(return_value=mock_localities.values())
        e.absolute_url = Mock(return_value=envelope_uri)
        e.getCountryName = Mock(return_value=mock_localities['es']['name'])
        self.engine.dataflow_lookup = Mock(return_value=mock_dataflow)
        root._setObject(e.id, e)
        envelope = root[e.id]

        ret = self.engine.sendNotificationToUNS(envelope, event, label)
        self.assertEqual(ret, 1)

        sendNotification = self.xmlrpc_server.UNSService.sendNotification
        sendNotification.assert_called_once_with('132547698', [
            ['http://example.com/my/envelope/events#ts1338217590.56',
             'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
             'http://rod.eionet.europa.eu/schema.rdf#Workflowevent'],
            ['http://example.com/my/envelope/events#ts1338217590.56',
             'http://purl.org/dc/elements/1.1/title',
             label],
            ['http://example.com/my/envelope/events#ts1338217590.56',
             'http://purl.org/dc/elements/1.1/identifier',
             envelope.absolute_url()],
            ['http://example.com/my/envelope/events#ts1338217590.56',
             'http://purl.org/dc/elements/1.1/date',
             mock_strftime.return_value],
            ['http://example.com/my/envelope/events#ts1338217590.56',
             'http://rod.eionet.europa.eu/schema.rdf#obligation',
             mock_dataflow['TITLE']],
            ['http://example.com/my/envelope/events#ts1338217590.56',
             'http://rod.eionet.europa.eu/schema.rdf#locality',
             mock_localities['es']['name']],
            ['http://example.com/my/envelope/events#ts1338217590.56',
             'http://rod.eionet.europa.eu/schema.rdf#actor',
             'system'],
            ['http://example.com/my/envelope/events#ts1338217590.56',
             'http://rod.eionet.europa.eu/schema.rdf#event_type',
             event],
        ])

    def test_send_notification_to_uns_error(self):
        envelope = Mock(dataflow_uris=[])
        sendNotification = self.xmlrpc_server.UNSService.sendNotification
        sendNotification.side_effect = ValueError
        ret = self.engine.sendNotificationToUNS(envelope, Mock(), Mock())
        self.assertEqual(ret, 0)
        self.assertEqual(sendNotification.call_count, 1)
