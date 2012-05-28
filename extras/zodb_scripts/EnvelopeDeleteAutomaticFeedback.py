#
# Deletes all QA feedback that is created by QA scripts - NOT confirmation letters etc.
#
def is_automatic(s):
    if s[:12] == "AutomaticQA_": return True
    return False

l_feedback2delete = filter(is_automatic, context.objectIds('Report Feedback'))
context.manage_delObjects(l_feedback2delete)
