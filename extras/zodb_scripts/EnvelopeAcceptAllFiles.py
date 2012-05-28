# This script accepts all files that aren't already accepted.
# It is to be called just before 'End' activity.
# It requires the user to have 'Change Feedback' permission, which the 'Client' role has.
for x in context.objectValues('Report Document'):
    if x.get_accept_time() is None:
        x.set_accept_time()
