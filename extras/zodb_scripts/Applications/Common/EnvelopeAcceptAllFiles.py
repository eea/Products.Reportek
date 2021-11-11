# flake8: noqa
# Script (Python) "EnvelopeAcceptAllFiles"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=workitem_id, REQUEST
# title=Marks all files in an envelope accepted
##
# This script accepts all files that aren't already accepted.
# It is to be called just before 'End' activity.
# It requires the user to have 'Change Feedback' permission, which the
# 'Client' role has.
for x in context.getMySelf().objectValues('Report Document'):  # noqa: F821
    if x.get_accept_time() is None:
        x.set_accept_time()
