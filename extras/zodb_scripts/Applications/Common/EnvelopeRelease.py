# Script (Python) "EnvelopeRelease"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=workitem_id, REQUEST
# title=Release the envelope
##
request = container.REQUEST  # noqa: F821

# If the flag to upload files restricted by default has been set in the Draft
# activity, remove it now
if 'default_restricted' in request.SESSION:
    request.SESSION.delete('default_restricted')

# Notify UNS
if container.ReportekEngine.UNS_server:  # noqa: F821
    container.ReportekEngine.sendNotificationToUNS(  # noqa: F821
        context.getMySelf(),  # noqa: F821
        'Envelope release', 'Envelope %s (%s) released to public' % (
            context.getMySelf().title_or_id(),  # noqa: F821
            context.getMySelf().absolute_url()),  # noqa: F821
        request.AUTHENTICATED_USER.getUserName())

# ping CR
if container.ReportekEngine.canPingCR():  # noqa: F821
    context.getMySelf().content_registry_ping()  # noqa: F821

# Set the release flag on the envelope/instance
context.getMySelf().release_envelope()  # noqa: F821
