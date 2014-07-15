## Script (Python) "EnvelopeRevoke"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Revoke the envelope
##
request = container.REQUEST

#Notify UNS
if container.ReportekEngine.UNS_server:
    container.ReportekEngine.sendNotificationToUNS(context.getMySelf(), 'Envelope revoke', 'Envelope %s (%s) was revoked from public view' % (context.getMySelf().title_or_id(), context.getMySelf().absolute_url()), request.AUTHENTICATED_USER.getUserName())

#ping CR for deletion
if container.ReportekEngine.canPingCR():
    context.getMySelf().content_registry_ping(delete=True)

#Unset the release flag on the envelope/instance
context.getMySelf().unrelease_envelope()

#Delete the automatic feedback for the confirmation of release, if exists
context.getMySelf().manage_delObjects([x.id for x in context.getMySelf().objectValues('Report Feedback') if x.title.lower().find('receipt') != -1])
