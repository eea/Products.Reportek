# flake8: noqa
# Script (Python) "EnvelopeRevoke"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=workitem_id, REQUEST
# title=Revoke the envelope
##
request = container.REQUEST  # noqa: F821

# Notify UNS
if container.ReportekEngine.UNS_server:  # noqa: F821
    container.ReportekEngine.sendNotificationToUNS(  # noqa: F821
        context.getMySelf(),  # noqa: F821
        'Envelope revoke', 'Envelope %s (%s) was revoked from public view' % (
            context.getMySelf().title_or_id(),  # noqa: F821
            context.getMySelf().absolute_url()),  # noqa: F821
        request.AUTHENTICATED_USER.getUserName())

# ping CR for deletion
if container.ReportekEngine.canPingCR():  # noqa: F821
    context.getMySelf().content_registry_ping(delete=True)  # noqa: F821

# Unset the release flag on the envelope/instance
context.getMySelf().unrelease_envelope()  # noqa: F821

# Delete the automatic feedback for the confirmation of release, if exists
context.getMySelf().manage_delObjects([x.id for x in context.getMySelf(  # noqa: F821
).objectValues('Report Feedback') if x.title.lower().find('receipt') != -1])
