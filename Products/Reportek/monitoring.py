import os
import socket
import logging
import logging.handlers


publish_error_log = logging.getLogger(__name__)
publish_error_log.propagate = False


def log_pub_failure(event):
    if event.retry:
        return

    if publish_error_log.handlers:
        publish_error_log.error('Exception on %s [%s]',
                                event.request.URL,
                                event.request.method,
                                exc_info=event.exc_info)


def initialize():
    from App.config import getConfiguration

    env = getattr(getConfiguration(), 'environment', {})
    mail_handler_cfg = {
        'fromaddr': '%s@%s' % (os.environ['LOGNAME'], socket.getfqdn()),
        'toaddrs': env.get('REPORTEK_ERROR_MAIL_TO', '').split(),
        'subject': "Error in Reportek",
        'mailhost': env.get('REPORTEK_ERROR_SMTP_HOST', 'localhost'),
    }
    site_error_log = logging.getLogger('Zope.SiteErrorLog')

    if mail_handler_cfg['toaddrs']:
        mail_handler = logging.handlers.SMTPHandler(**mail_handler_cfg)
        site_error_log.addHandler(mail_handler)

    sentry_url = env.get('REPORTEK_ERROR_SENTRY_URL')
    if sentry_url:
        from raven.handlers.logging import SentryHandler
        sentry_handler = SentryHandler(sentry_url)
        publish_error_log.addHandler(sentry_handler)
