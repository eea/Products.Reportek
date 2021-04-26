# flake8: noqa
# Script (Python) "EnvelopeAddFeedback"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
# title=Feedback form
##
if len(context.objectIds('Report Document')) == 0:
    if 'feedback' + str(int(context.reportingdate)) in context.objectIds('Report Feedback'):
        context.manage_delObjects('feedback' + str(int(context.reportingdate)))
    context.manage_addFeedback(title="You didn't upload!",
                               feedbacktext="""Hello, you are expected to upload something...

Not just go through the motions""", automatic=1)
    context.unrelease_envelope()
else:
    context.manage_addFeedback(title="Automatic feedback", feedbacktext="""Hello there,

This is a dummy feedback that doesn't really do anything except
to demonstrate that automatic feedback is possible.
""", automatic=1)

context.completeWorkitem(workitem_id)
