# This script removes restrictions from all files that aren't already unrestricted.
# It is to be called just before 'End' activity.
# It requires the user to have 'Change Feedback' permission, which the 'Client' role has.
if context.areRestrictions():
    context.manage_unrestrict(context.objectIds())
