import unittest
from mock import Mock, patch
from Products.Reportek.negotiator import CustomNegotiator
from ZPublisher.HTTPRequest import HTTPRequest
from zope.i18n.negotiator import normalize_lang


class TestCustomNegotiator(unittest.TestCase):
    # not normalized languages
    AVAILABLE_LANGS = [
        'eN',
        'RO',
        'Fr'
    ]
    AVAILABLE_LANGS_NAME = [
        u'English',
        u'Rom\xe2n\u0103',
        u'Fran\xe7ais',
    ]

    def setUp(self):
        self.negotiator = CustomNegotiator()

    def test_getLanguage_fromCookie(self):
        request = Mock(HTTPRequest)

        request.cookies = {'reportek_language': 'en'}
        lang = self.negotiator.getLanguage(self.AVAILABLE_LANGS, request)
        expected_lang = 'en'
        self.assertEqual(lang, expected_lang)

        # not normalized lang code
        request.cookies = {'reportek_language': 'en_US'}
        lang = self.negotiator.getLanguage(self.AVAILABLE_LANGS, request)
        expected_lang = 'en-us'
        self.assertEqual(lang, expected_lang)

    def test_getLanguage_fromDefault(self):
        request = Mock(HTTPRequest)
        request.cookies = {}

        parent = Mock()
        parent.default_language = 'fr'
        request.PARENTS = [parent]
        lang = self.negotiator.getLanguage(self.AVAILABLE_LANGS, request)
        expected_lang = 'fr'
        self.assertEqual(lang, expected_lang)

    @patch('zope.i18n.negotiator.Negotiator.getLanguage')
    def test_getLanguage_fromSuperClass(self, mock_superGetLanguage):
        request = Mock(HTTPRequest)
        request.cookies = {}
        self.negotiator.getLanguage(self.AVAILABLE_LANGS, request)
        self.assertEqual(mock_superGetLanguage.call_count, 1)

    @patch('Products.Reportek.negotiator.queryUtility')
    def test_getAvailableLanguages(self, mock_queryUtility):
        mock_translation_domain = Mock()
        langs_dict = {}
        for lang in self.AVAILABLE_LANGS + ['test']:
            langs_dict[lang] = lang
        mock_translation_domain.getCatalogsInfo.return_value = langs_dict
        mock_queryUtility.return_value = mock_translation_domain
        langs = self.negotiator.getAvailableLanguages()
        self.assertEqual(langs, dict(zip(
            [normalize_lang(lang) for lang in self.AVAILABLE_LANGS],
            self.AVAILABLE_LANGS_NAME)))
