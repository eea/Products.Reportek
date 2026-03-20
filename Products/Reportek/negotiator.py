# -*- coding: UTF-8 -*-
from zope.component import queryUtility
from zope.i18n.interfaces import ITranslationDomain
from zope.i18n.negotiator import Negotiator, normalize_lang, normalize_langs
from zope.tal.translationcontext import TranslationContext


class CustomNegotiator(Negotiator):
    LANGUAGE_NAMES = {
        "bg": "Български",
        "cs": "čeština",
        "hr": "Hrvatski",
        "da": "dansk",
        "nl": "Nederlands",
        "el": "ελληνικά",
        "en": "English",
        "et": "eesti",
        "fi": "Suomi",
        "fr": "Français",
        "de": "Deutsch",
        "hu": "magyar",
        "is": "Íslenska",
        "it": "italiano",
        "lv": "Latviešu",
        "lt": "lietuvių",
        "mt": "Malti",
        "no": "Norsk",
        "pl": "polski",
        "pt": "Português",
        "ro": "Română",
        "sk": "slovenčina",
        "sl": "Slovenščina",
        "es": "Español",
        "sv": "Svenska",
        "tr": "Türkçe",
        "ru": "русский",
        "ga": "Gaeilge",
    }

    @classmethod
    def getBaseLangName(cls, lang):
        baseEndIdx = lang.find("-")
        if baseEndIdx >= 0:
            return lang[:baseEndIdx]
        else:
            return lang

    # alters its argument !
    @classmethod
    def purgeWeirdZopeI18nTestLang(cls, langs):
        if "test" in langs:
            langs.pop("test")

    def getLanguage(self, langs, request):
        if not langs:
            return None
        # get lang from cookie
        langs = normalize_langs(langs)
        self.purgeWeirdZopeI18nTestLang(langs)
        lang = self.getCookieLanguage(request)
        if lang and (lang in langs or self.getBaseLangName(lang) in langs):
            return lang
        # get lang from site default ?!?
        parents = getattr(request, "PARENTS", None)
        app = parents[-1] if parents else None
        lang = getattr(app, "default_language", None)
        if lang and lang in langs:
            return lang
        # get lang from browser settings
        return super(CustomNegotiator, self).getLanguage(langs, request)

    def getCookieLanguage(self, request):
        lang = request.cookies.get("reportek_language", None)
        return normalize_lang(lang) if lang else None

    def getAvailableLanguages(self):
        domain = TranslationContext().domain
        # keep in mind: this is the name of the .mo file as in default.mo
        translation_domain = queryUtility(ITranslationDomain, domain)
        if not translation_domain:
            return {}
        langs = translation_domain.getCatalogsInfo()
        self.purgeWeirdZopeI18nTestLang(langs)
        language_codes = normalize_langs(list(langs.keys()))
        languages = {}
        for code in language_codes:
            languages[code] = self.LANGUAGE_NAMES.get(code, code)
        return languages

    def getSelectedLanguage(self, request):
        return self.getLanguage(list(self.getAvailableLanguages().keys()), request)
