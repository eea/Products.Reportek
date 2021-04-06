# Script (Python) "EnvelopeDeleteAllAutomaticFeedback"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
# title=Deletes all automatic feedback
##
l_feedback2delete = [x.id for x in context.getMySelf(
).objectValues('Report Feedback') if x.automatic]
context.getMySelf().manage_delObjects(l_feedback2delete)
