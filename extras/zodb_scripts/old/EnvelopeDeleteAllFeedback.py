## Script (Python) "EnvelopeDeleteAllFeedback"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Deletes all feedback - including manual
##
context.manage_delObjects(context.objectIds('Report Feedback'))
