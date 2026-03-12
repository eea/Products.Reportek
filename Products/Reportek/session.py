import logging
import os

from beaker.middleware import SessionMiddleware
from zope.component import adapter
from ZPublisher.interfaces import IPubStart

logger = logging.getLogger("Products.Reportek.session")


def beaker_session_filter_factory(app, global_conf, **local_conf):
    """
    WSGI filter_app factory for PasteDeploy.
    This inspects the USE_BEAKER_SESSION environment variable.
    If true, it wraps the Zope application in Beaker's SessionMiddleware
    configured for Redis. Otherwise, it simply returns the unmodified
    Zope application.
    """
    use_beaker = os.environ.get("USE_BEAKER_SESSION", "0").lower() in (
        "1",
        "true",
        "yes",
    )

    if not use_beaker:
        logger.info(
            "Beaker session backend is DISABLED. "
            "Passing WSGI app through unmodified."
        )
        return app

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    secret = os.environ.get("SESSION_SECRET", "secret_key")

    logger.info(
        "Injecting Beaker session backend via Redis: {0}".format(redis_url)
    )

    timeout = int(os.environ.get("SESSION_MANAGER_TIMEOUT", "30")) * 60
    cookie_expires_env = os.environ.get("SESSION_COOKIE_EXPIRES", "true").lower()
    if cookie_expires_env in ("true", "1", "yes"):
        cookie_expires = True  # expire on browser close
    elif cookie_expires_env in ("false", "0", "no"):
        cookie_expires = False  # never expire
    else:
        cookie_expires = int(cookie_expires_env)  # seconds

    # Configure Beaker to use Redis
    session_opts = {
        "session.type": "ext:redis",
        "session.url": redis_url,
        "session.secret": secret,
        "session.key": "beaker.session",
        "session.auto": True,
        "session.cookie_expires": cookie_expires,
        "session.timeout": timeout,  # expire server-side after inactivity (seconds)
    }

    return SessionMiddleware(app, session_opts)


class ZopeBeakerSessionWrapper:
    """
    Wraps a Beaker session to provide the API expected by Zope legacy code,
    such as .set(key, value) and .delete(key).
    """

    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, beaker_session):
        self._beaker_session = beaker_session

    def set(self, key, value):
        self._beaker_session[key] = value

    def get(self, key, default=None):
        return self._beaker_session.get(key, default)

    def delete(self, key):
        if key in self._beaker_session:
            del self._beaker_session[key]

    def has_key(self, key):
        return key in self._beaker_session

    def getId(self):
        return getattr(self._beaker_session, "id", None)

    def invalidate(self):
        if hasattr(self._beaker_session, "invalidate"):
            self._beaker_session.invalidate()

    def keys(self):
        return self._beaker_session.keys()

    def values(self):
        return self._beaker_session.values()

    def items(self):
        return self._beaker_session.items()

    def update(self, d):
        self._beaker_session.update(d)

    def clear(self):
        self._beaker_session.clear()

    def __getitem__(self, key):
        return self._beaker_session[key]

    def __setitem__(self, key, value):
        self._beaker_session[key] = value

    def __delitem__(self, key):
        del self._beaker_session[key]

    def __contains__(self, key):
        return key in self._beaker_session


@adapter(IPubStart)
def extract_beaker_session(event):
    """
    Subscribes to IBeforeTraverseEvent to intercept the request early.
    If 'beaker.session' is in the WSGI environ, we bind it to request.SESSION
    so Zope code continues to work securely as a drop-in replacement.
    """
    request = event.request
    if "beaker.session" in request.environ:
        logger.info("SETTING request.SESSION: {}")
        request.SESSION = ZopeBeakerSessionWrapper(
            request.environ["beaker.session"]
        )
