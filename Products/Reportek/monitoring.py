import logging
import zExceptions
from App.config import getConfiguration


ignored_types = (
    zExceptions.Redirect,
    zExceptions.Unauthorized,
    zExceptions.Forbidden,
    zExceptions.NotFound,
    zExceptions.MethodNotAllowed,
    zExceptions.BadRequest,
)


publish_error_log = logging.getLogger(__name__ + '.publish_errors')
publish_error_log.propagate = False

remote_feedback_log = logging.getLogger('Products.Reportek'
                                        '.RemoteApplication.feedback')
remote_conversion_log = logging.getLogger(
    'Products.Reportek'
    '.EnvelopeCustomDataflows.conversion')
converter_detection_log = logging.getLogger('Products.Reportek'
                                            '.Converters.detection')
gisqa_log = logging.getLogger('Products.Reportek.RemoteRESTApplication.gisqa')


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
    env = getattr(getConfiguration(), 'environment', {})
    sentry_url = env.get('REPORTEK_ERROR_SENTRY_URL')

    logging.getLogger('requests').setLevel(logging.WARN)

    if sentry_url:
        from raven.contrib.zope import ZopeSentryHandler
        zope_sentry_handler = ZopeSentryHandler(sentry_url)
        publish_error_log.addHandler(zope_sentry_handler)
        remote_feedback_log.addHandler(zope_sentry_handler)
        remote_conversion_log.addHandler(zope_sentry_handler)
        converter_detection_log.addHandler(zope_sentry_handler)
        gisqa_log.addHandler(zope_sentry_handler)
