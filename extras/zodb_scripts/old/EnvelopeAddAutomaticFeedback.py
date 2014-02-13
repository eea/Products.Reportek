## Script (Python) "EnvelopeAddAutomaticFeedback"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Automatic feedback when no documents uploaded or the delivery has blocking errors
##
if 'feedback' + str(int(context.reportingdate)) in context.objectIds('Report Feedback'):
    context.manage_delObjects('feedback' + str(int(context.reportingdate)))

context.manage_addFeedback(title="Data delivery was not acceptable!",
    feedbacktext="You either did not upload any files in this envelope or your delivery did not pass the automatic quality assessment. Please correct the errors by modifying the questionnaire before submitting your delivery. The list of errors can be found from the Feedback report attached to the envelope.. Please go back to draft mode and fix these errors.", 
    automatic=1)
context.unrelease_envelope()
    
context.completeWorkitem(workitem_id)
