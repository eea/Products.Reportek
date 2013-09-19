from zope.i18n.negotiator import Negotiator


class CustomNegotiator(Negotiator):

    def getLanguage(self, langs, env):

        parents = getattr(env, 'PARENTS', None)
        app = parents[-1] if parents else None
        lang = getattr(app, 'default_language', None)
        if lang:
            return lang
        return super(CustomNegotiator, self).getLanguage(langs, env)
