## Script (Python) "EnvelopeAddAutomaticFeedback"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Automatic feedback when no documents uploaded
##
if 'feedback' + str(int(context.reportingdate)) in context.objectIds('Report Feedback'):
    context.manage_delObjects('feedback' + str(int(context.reportingdate)))

context.manage_addFeedback(title="You didn't upload!",
    feedbacktext="You are expected to upload a document in this envelope before releasing it.", 
    automatic=1)
context.unrelease_envelope()
    
context.completeWorkitem(workitem_id)
