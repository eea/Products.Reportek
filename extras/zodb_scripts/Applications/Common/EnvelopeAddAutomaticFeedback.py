# flake8: noqa
# Script (Python) "EnvelopeAddAutomaticFeedback"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=workitem_id, REQUEST
# title=Automatic feedback when no documents uploaded
##
request = container.REQUEST  # noqa: F821
fbs = context.getMySelf().objectIds('Report Feedback')  # noqa: F821
if 'feedback' + str(int(context.getMySelf().reportingdate)) in fbs:  # noqa: F821
    context.getMySelf().manage_delObjects(  # noqa: F821
        'feedback' + str(int(context.getMySelf().reportingdate)))  # noqa: F821

context.getMySelf().manage_addFeedback(  # noqa: F821
    title="You didn't upload!",
    feedbacktext="You are expected to upload a document in this envelope\
     before releasing it.",
    automatic=1)
context.getMySelf().unrelease_envelope()  # noqa: F821

context.getMySelf().completeWorkitem(workitem_id)  # noqa: F821
