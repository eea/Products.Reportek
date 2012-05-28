request = container.REQUEST

#Notify UNS
if container.ReportekEngine.UNS_server:
    container.ReportekEngine.sendNotificationToUNS(context.getMySelf(), 'Envelope revoke', 'Envelope %s (%s) was revoked from public view' % (context.title_or_id(), context.absolute_url()), request.AUTHENTICATED_USER.getUserName())

#Unset the release flag on the envelope/instance
context.unrelease_envelope()
