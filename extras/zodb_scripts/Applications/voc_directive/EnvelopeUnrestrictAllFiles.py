## Script (Python) "EnvelopeUnrestrictAllFiles"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=
##
# This script removes restrictions from all files that aren't already unrestricted.
# It is to be called just before 'End' activity.
# It requires the user to have 'Change Feedback' permission, which the 'Client' role has.
if context.getMySelf().areRestrictions():
    context.getMySelf().manage_unrestrict(context.getMySelf().objectIds())
