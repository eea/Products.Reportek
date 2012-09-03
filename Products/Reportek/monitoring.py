import logging
import zExceptions


ignored_types = (
    zExceptions.Redirect,
    zExceptions.Unauthorized,
    zExceptions.Forbidden,
    zExceptions.NotFound,
    zExceptions.MethodNotAllowed,
    zExceptions.BadRequest,
)


publish_error_log = logging.getLogger(__name__)
publish_error_log.propagate = False

remote_feedback_log = logging.getLogger('Products.Reportek'
                                        '.RemoteApplication.feedback')


def log_pub_failure(event):
    if event.retry:
        return

    if publish_error_log.handlers:
        if not issubclass(event.exc_info[0], ignored_types):
            publish_error_log.error('Exception on %s [%s]',
                                    event.request.URL,
                                    event.request.method,
                                    exc_info=event.exc_info)


def initialize():
    from App.config import getConfiguration

    env = getattr(getConfiguration(), 'environment', {})
    sentry_url = env.get('REPORTEK_ERROR_SENTRY_URL')

    if sentry_url:
        from raven.handlers.logging import SentryHandler
        sentry_handler = SentryHandler(sentry_url)
        publish_error_log.addHandler(sentry_handler)
        remote_feedback_log.addHandler(sentry_handler)
