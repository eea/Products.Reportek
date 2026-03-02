import os
import logging
from beaker.middleware import SessionMiddleware
from zope.traversing.interfaces import IBeforeTraverseEvent
from zope.component import adapter

logger = logging.getLogger('Products.Reportek.session')

def beaker_session_filter_factory(app, global_conf, **local_conf):
    """
    WSGI filter_app factory for PasteDeploy.
    This inspects the USE_BEAKER_SESSION environment variable.
    If true, it wraps the Zope application in Beaker's SessionMiddleware
    configured for Redis. Otherwise, it simply returns the unmodified
    Zope application.
    """
    use_beaker = os.environ.get('USE_BEAKER_SESSION', '0').lower() in ('1', 'true', 'yes')

    if not use_beaker:
        logger.info("Beaker session backend is DISABLED. Passing WSGI app through unmodified.")
        return app

    redis_url = os.environ.get('REDIS_SESSION_URL', 'redis://redis:6379/0')
    secret = os.environ.get('SESSION_SECRET', 'secret_key')

    logger.info("Injecting Beaker session backend via Redis: {0}".format(redis_url))
    
    # Configure Beaker to use Redis
    session_opts = {
        'session.type': 'ext:redis',
        'session.url': redis_url,
        'session.secret': secret,
        'session.key': 'beaker.session',
        'session.auto': True,
        'session.cookie_expires': True, # expire on browser close by default
        # Add timeout or max_age if persistent sessions are needed
    }

    return SessionMiddleware(app, session_opts)

@adapter(IBeforeTraverseEvent)
def extract_beaker_session(event):
    """
    Subscribes to IBeforeTraverseEvent to intercept the request early.
    If 'beaker.session' is in the WSGI environ, we bind it to request.SESSION
    so Zope code continues to work securely as a drop-in replacement.
    """
    request = event.request
    
    if 'beaker.session' in request.environ:
        request.SESSION = request.environ['beaker.session']
