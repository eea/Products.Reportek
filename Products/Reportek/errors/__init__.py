from Acquisition import aq_parent
import json
import re


class ErrorView(object):
    """View rendered on some errors."""

    def __call__(self, *args, **kwargs):
        accept = self.request.environ.get("HTTP_ACCEPT")
        error_type = self.context.__class__.__name__
        if accept == 'application/json':
            status = {
                'Unauthorized': 401,
                'NotFound': 404,
                'BadRequest': 400
            }
            self.request.response.setHeader('Content-Type', 'application/json')
            self.request.response.setStatus(status.get(error_type))
            error = {
                'title': error_type,
                'description': re.sub('<[^<]+?>', '', self.context.message)
            }
            data = {
                'errors': [error],
            }
            return self.request.response.write(json.dumps(data, indent=4))

        ctx = aq_parent(self)
        return ctx.standard_error_message(ctx, self.request,
                                          error_type=error_type,
                                          error_value=self.context.message)
