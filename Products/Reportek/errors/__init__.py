from Acquisition import aq_parent
import json
import re


class BadRequestErrorView(object):
    """View rendered on BadRequestError."""

    def __call__(self, *args, **kwargs):
        accept = self.request.environ.get("HTTP_ACCEPT")
        error_type = 'BadRequest'
        if accept == 'application/json':
            self.request.RESPONSE.setHeader('Content-Type', 'application/json')
            error = {
                'title': error_type,
                'description': re.sub('<[^<]+?>', '', self.context.message)
            }
            data = {
                'errors': [error],
            }
            return json.dumps(data, indent=4)

        ctx = aq_parent(self)
        return ctx.standard_error_message(ctx, self.request,
                                          error_type=error_type,
                                          error_value=self.context.message)

