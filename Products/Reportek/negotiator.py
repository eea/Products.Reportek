# -*- coding: UTF-8 -*-
from zope.i18n.negotiator import Negotiator, normalize_lang, normalize_langs
from zope.i18n.interfaces import ITranslationDomain
from zope.component import queryUtility


class CustomNegotiator(Negotiator):

    LANGUAGE_NAMES = {
        u'bg': u'Български',
        u'cs': u'čeština',
        u'hr': u'Hrvatski',
        u'da': u'dansk',
        u'nl': u'Nederlands',
        u'el': u'ελληνικά',
        u'en': u'English',
        u'et': u'eesti',
        u'fi': u'Suomi',
        u'fr': u'Français',
        u'de': u'Deutsch',
        u'hu': u'magyar',
        u'is': u'Íslenska',
        u'it': u'italiano',
        u'lv': u'Latviešu',
        u'lt': u'lietuvių',
        u'mt': u'Malti',
        u'no': u'Norsk',
        u'pl': u'polski',
        u'pt': u'Português',
        u'ro': u'Română',
        u'sk': u'slovenčina',
        u'sl': u'Slovenščina',
        u'es': u'Español',
        u'sv': u'Svenska',
        u'tr': u'Türkçe',
        u'ru': u'русский',
    }

    @classmethod
    def getBaseLangName(cls, lang):
        baseEndIdx = lang.find('-')
        if baseEndIdx >= 0:
            return lang[:baseEndIdx]
        else:
            return lang

    def getLanguage(self, langs, request):

        # get lang from cookie
        langs = normalize_langs(langs)
        lang = self.getCookieLanguage(request)
        if lang and (lang in langs or self.getBaseLangName(lang) in langs):
            return lang
        # get lang from site default ?!?
        parents = getattr(request, 'PARENTS', None)
        app = parents[-1] if parents else None
        lang = getattr(app, 'default_language', None)
        if lang and lang in langs:
            return lang
        # get lang from browser settings
        return super(CustomNegotiator, self).getLanguage(langs, request)

    def getCookieLanguage(self, request):
        lang = request.cookies.get('reportek_language', None)
        return normalize_lang(lang) if lang else None

    def getAvailableLanguages(self):
        translation_domain = queryUtility(ITranslationDomain, 'default')
        language_codes = translation_domain.getCatalogsInfo().keys()
        language_codes = normalize_langs(language_codes)
        languages = {}
        for code in language_codes:
            languages[code] = self.LANGUAGE_NAMES.get(code, code)
        return languages

    def getSelectedLanguage(self, request):
        return self.getLanguage(self.getAvailableLanguages().keys(), request)
