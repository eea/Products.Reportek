## Script (Python) "EnvelopeRestrictAllFiles"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Marks all files in an envelope restricted
##
# This script accepts all files that aren't already accepted.
# It is to be called just before 'Release' activity.
ids = context.objectIds('Report Document')
if len(ids) > 0:
    context.manage_restrict(ids)