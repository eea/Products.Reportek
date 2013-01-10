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

#Unset the release flag on the envelope/instance
context.getMySelf().unrelease_envelope()
