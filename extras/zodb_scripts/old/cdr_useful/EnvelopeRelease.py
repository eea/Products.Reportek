## Script (Python) "EnvelopeRelease"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Release the envelope
##
#Set the release flag on the envelope/instance
context.release_envelope()
