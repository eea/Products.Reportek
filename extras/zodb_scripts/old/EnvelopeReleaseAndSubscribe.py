## Script (Python) "EnvelopeReleaseAndSubscribe"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Release the envelope and subscribe actors to receive notifications
##
request = container.REQUEST

#Notify UNS
if container.ReportekEngine.UNS_server:
    container.ReportekEngine.sendNotificationToUNS(context.getMySelf(), 'Envelope release', 'Envelope %s (%s) released to public' % (context.title_or_id(), context.absolute_url()), request.AUTHENTICATED_USER.getUserName())

#Set the release flag on the envelope/instance
context.release_envelope()

context.subscribe_all_actors('Comment to feedback posted')
