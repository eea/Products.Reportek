from Products.Five import BrowserView


class EnvelopeHistoryView(BrowserView):
    def __init__(self, context, request):
        super(EnvelopeHistoryView, self).__init__(context, request)
        try:
            import plone.protect.interfaces
            from zope.interface import alsoProvides

            if hasattr(plone.protect.interfaces, "IDisableCSRFProtection"):
                alsoProvides(
                    self.request,
                    plone.protect.interfaces.IDisableCSRFProtection,
                )
        except ImportError:
            pass

    def get_formatted_workitem_info(self, workitem, expanded=False):
        """Returns formatted information for a workitem"""
        return {
            "date": workitem.lastActivityDate().strftime("%Y/%m/%d"),
            "activity_name": workitem.getActivityAttribute("title"),
            "activity_id": workitem.activity_id,
            "actor": workitem.actor if workitem.actor else "",
            "status": workitem.status,
            "id": workitem.id,
            "details": workitem.workitemDetails if expanded else "",
            "is_renamed": not workitem.getActivityAttribute("title"),
        }

    def get_workitems(self):
        """Returns all workitems for the envelope"""
        return self.context.objectValues("Workitem")

    def is_expanded(self, workitem_id):
        """Checks if a workitem is expanded"""
        return self.request.get("w" + workitem_id) == "1"

    def get_toggle_url(self, workitem_id, current_state):
        """Returns URL for toggling workitem expansion"""
        new_state = "0" if current_state else "1"
        return "{}?{}".format(
            self.request.URL0,
            self.context.changeQueryString(
                self.request.get("QUERY_STRING", ""),
                "w" + workitem_id,
                new_state,
            ),
        )
