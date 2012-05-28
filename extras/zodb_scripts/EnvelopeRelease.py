## Script (Python) "EnvelopeRelease"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Release the envelope
##
request = container.REQUEST

#If the flag to upload files restricted by default has been set in the Draft activity, remove it now
if request.SESSION.has_key('default_restricted'):
    request.SESSION.delete('default_restricted')

#Notify UNS
if container.ReportekEngine.UNS_server:
    container.ReportekEngine.sendNotificationToUNS(context.getMySelf(), 'Envelope release', 'Envelope %s (%s) released to public' % (context.title_or_id(), context.absolute_url()), request.AUTHENTICATED_USER.getUserName())

#Set the release flag on the envelope/instance
context.release_envelope()
