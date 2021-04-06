# Script (Python) "revoke_roles"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=username, paths
# title=
##
for path in paths:
    folder = context.restrictedTraverse(path)
    folder.manage_delLocalRoles(userids=[username, ])
