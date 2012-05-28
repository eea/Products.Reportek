if 'feedback' + str(int(context.reportingdate)) in context.objectIds('Report Feedback'):
    context.manage_delObjects('feedback' + str(int(context.reportingdate)))

automatic_qa_env = context.callQAEnvelopeForArt17()

context.manage_addFeedback(title="Automatic envelope statistics",
    feedbacktext=str(automatic_qa_env), 
    content_type='text/html',
    automatic=1)
    
context.completeWorkitem(workitem_id)
