import unittest

from AccessControl import Unauthorized

from Products.Reportek.browser.envelope_history import EnvelopeHistoryView


class DummyResponse:
    def __init__(self):
        self.headers = {}

    def setHeader(self, name, value):
        self.headers[name.lower()] = value

    def getHeader(self, name):
        return self.headers.get(name.lower())


class DummyUser:
    def __init__(self, name="user.one"):
        self.name = name

    def getUserName(self):
        return self.name


class DummyRequest:
    debug = None

    def __init__(self, user=None):
        self.form = {}
        self.environ = {}
        self.response = DummyResponse()
        self.AUTHENTICATED_USER = user or DummyUser()

    def get(self, key, default=None):
        return self.form.get(key, default)


class DummyEnvelope:
    def __init__(self, path):
        self.path = path

    def absolute_url_path(self):
        return self.path


class TestEnvelopeHistoryContentType(unittest.TestCase):
    """The response content type must not depend on the RAM cache.

    ``ViewPageTemplateFile.__call__`` sets ``Content-Type`` as a side effect of
    rendering, so on a cache hit - where the template never runs - the header
    was left unset and ZPublisher fell back to ``text/plain; charset=utf-8``,
    showing raw HTML in the browser.
    """

    def _make_view(self, envelope, user=None):
        view = EnvelopeHistoryView(envelope, DummyRequest(user=user))
        view.index = self._make_index(view)
        return view

    def _make_index(self, view):
        def index():
            self.renders += 1
            # Mimic Products.Five ViewPageTemplateFile.__call__, which only
            # sets the header when it is not already present.
            response = view.request.response
            if not response.getHeader("Content-Type"):
                response.setHeader("Content-Type", "text/html")
            return "<div>history</div>"

        return index

    def setUp(self):
        self.renders = 0

    def test_content_type_is_html_on_render_and_on_cache_hit(self):
        envelope = DummyEnvelope("/envelopes/content-type-test")

        first = self._make_view(envelope)
        first_body = first()

        self.assertEqual(self.renders, 1)
        self.assertEqual(first_body, "<div>history</div>")
        self.assertEqual(first.request.response.getHeader("Content-Type"), "text/html")

        # A second request for the same envelope is served from the RAM cache.
        second = self._make_view(envelope)
        second_body = second()

        self.assertEqual(self.renders, 1, "expected a RAM cache hit, not a re-render")
        self.assertEqual(second_body, first_body)
        self.assertEqual(second.request.response.getHeader("Content-Type"), "text/html")

    def test_content_type_is_set_before_the_body_is_produced(self):
        envelope = DummyEnvelope("/envelopes/header-ordering-test")
        view = self._make_view(envelope)
        seen = {}

        def cached_call():
            seen["content_type"] = view.request.response.getHeader("Content-Type")
            return "<div>history</div>"

        view._cached_call = cached_call
        view()

        self.assertEqual(seen["content_type"], "text/html")

    def test_anonymous_is_still_rejected(self):
        view = self._make_view(
            DummyEnvelope("/envelopes/anonymous-test"),
            user=DummyUser("Anonymous User"),
        )
        with self.assertRaises(Unauthorized):
            view()
        self.assertEqual(self.renders, 0)


if __name__ == "__main__":
    unittest.main()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(
        unittest.TestLoader().loadTestsFromTestCase(TestEnvelopeHistoryContentType)
    )
    return suite
