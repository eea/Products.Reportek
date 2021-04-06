# Script (Python) "EnvelopeAddAutomaticFeedback"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
# title=Automatic feedback when no documents uploaded
##
request = container.REQUEST

if 'feedback' + str(int(context.getMySelf().reportingdate)) in context.getMySelf().objectIds('Report Feedback'):
    context.getMySelf().manage_delObjects(
        'feedback' + str(int(context.getMySelf().reportingdate)))

context.getMySelf().manage_addFeedback(title="You didn't upload!",
                                       feedbacktext="You are expected to upload a document in this envelope before releasing it.",
                                       automatic=1)
context.getMySelf().unrelease_envelope()

context.getMySelf().completeWorkitem(workitem_id)
