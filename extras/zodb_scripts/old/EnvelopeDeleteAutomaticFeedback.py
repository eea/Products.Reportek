## Script (Python) "EnvelopeDeleteAutomaticFeedback"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Deletes all automatic feedback
##
#
# Deletes all QA feedback that is created by QA scripts - NOT confirmation letters etc.
#
def is_automatic(s):
    #if s[:12] == "AutomaticQA_": return True
    if getattr(context, s).automatic == 1: return True
    return False

l_feedback2delete = filter(is_automatic, context.objectIds('Report Feedback'))
context.manage_delObjects(l_feedback2delete)
