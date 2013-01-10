from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Five.browser import BrowserView


SESSION_MESSAGES_KEY = 'reportek_messages'


def add(request, text, cls='system'):
    session = request.SESSION

    try:
        messages = session[SESSION_MESSAGES_KEY]
    except KeyError:
        messages = session[SESSION_MESSAGES_KEY] = []

    messages.append({
        'text': text,
        'cls': cls,
    })


messages_zpt = PageTemplateFile('zpt/messages', globals())


class MessagesView(BrowserView):

    def __call__(self):
        session = self.request.SESSION
        try:
            messages = session[SESSION_MESSAGES_KEY]
        except KeyError:
            messages = []
        else:
            del session[SESSION_MESSAGES_KEY]
        return messages_zpt.__of__(self.aq_parent)(messages=messages)
