# Script (Python) "EnvelopeDeleteAutomaticFeedback"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
# title=Delete all automatic feedback
##
#
# Deletes all QA feedback that is created by QA scripts - NOT confirmation letters etc.
#
def is_automatic(s):
    if s[:12] == "AutomaticQA_":
        return True
    return False


l_feedback2delete = filter(
    is_automatic, context.getMySelf().objectIds('Report Feedback'))
context.getMySelf().manage_delObjects(l_feedback2delete)
