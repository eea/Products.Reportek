import os
from datetime import datetime
import logging
import zExceptions
from App.config import getConfiguration
import requests

try:
    import simplejson as json
except ImportError:
    import json


CUBE_TIMEOUT = 2  # two seconds


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

cube_log = logging.getLogger(__name__ + '.cube')

remote_feedback_log = logging.getLogger('Products.Reportek'
                                        '.RemoteApplication.feedback')

remote_conversion_log = logging.getLogger('Products.Reportek'
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


def log_to_cube(event):
    url = os.environ.get('CUBE_POST_URL')
    if not url:
        return

    request = event.request
    response = request.RESPONSE

    message = {
        "type": "request",
        "time": datetime.utcnow().isoformat(),
        "data": {
            "method": request.method,
            "path": request.PATH_INFO,
            "status": response.status,
        }
    }

    try:
        response = requests.post(url, data=json.dumps([message]),
                                      timeout=CUBE_TIMEOUT)
        if response.status_code != 200:
            cube_log.error("Error saving data: %r", response.json()['error'])
    except:
        cube_log.exception("Error saving data")


def initialize():
    env = getattr(getConfiguration(), 'environment', {})
    sentry_url = env.get('REPORTEK_ERROR_SENTRY_URL')

    logging.getLogger('requests').setLevel(logging.WARN)

    if sentry_url:
        from raven.handlers.logging import SentryHandler
        sentry_handler = SentryHandler(sentry_url)
        publish_error_log.addHandler(sentry_handler)
        remote_feedback_log.addHandler(sentry_handler)
        cube_log.addHandler(sentry_handler)
        remote_conversion_log.addHandler(sentry_handler)
        converter_detection_log.addHandler(sentry_handler)
        gisqa_log.addHandler(sentry_handler)

        from raven.contrib.zope import ZopeSentryHandler
        zope_sentry_handler = ZopeSentryHandler(sentry_url)
        publish_error_log.addHandler(zope_sentry_handler)
        remote_feedback_log.addHandler(zope_sentry_handler)
        cube_log.addHandler(zope_sentry_handler)
        remote_conversion_log.addHandler(zope_sentry_handler)
        converter_detection_log.addHandler(zope_sentry_handler)
        gisqa_log.addHandler(zope_sentry_handler)
