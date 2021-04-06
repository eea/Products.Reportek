# Script (Python) "ReceiptConfirmationPositive"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
# title=(Data delivery is acceptable
##
l_ret = """
<p><strong>Data is acceptable</strong></p>

<p>Your delivery can be accepted. Please finalise the submission.</p>

"""

context.getMySelf().manage_addFeedback(title="Automatic validation: Data delivery is acceptable",
                                       feedbacktext=l_ret, automatic=1, content_type='text/html')
context.completeWorkitem(workitem_id)
