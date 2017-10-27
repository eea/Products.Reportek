import os


class SiteErrorView(object):
    """View rendered on SiteError."""

    def __call__(self, *args, **kwargs):
        public_dsn = os.environ.get('SENTRY_PUBLIC_DSN', '')
        return self.index(public_dsn=public_dsn, error='500')
