# This script accepts all files that aren't already accepted.
# It is to be called just before 'Release' activity.
ids = context.objectIds('Report Document')
if len(ids) > 0:
    context.manage_restrict(ids)
