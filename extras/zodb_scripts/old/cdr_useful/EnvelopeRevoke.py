# flake8: noqa
# Script (Python) "EnvelopeRevoke"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
# title=Revoke the envelope
##
# Unset the release flag on the envelope/instance
context.unrelease_envelope()
