## Script (Python) "EnvelopeDeleteAutomaticFeedback"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Deletes all automatic feedback
##
l_feedback2delete = [x.id for x in context.objectValues('Report Feedback') if x.automatic == 1 and x.activity_id == '']
context.manage_delObjects(l_feedback2delete)
