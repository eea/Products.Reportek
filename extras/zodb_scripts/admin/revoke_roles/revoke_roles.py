# Script (Python) "revoke_roles"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=username, paths
# title=
##
for path in paths:  # noqa: F821
    folder = context.restrictedTraverse(path)  # noqa: F821
    folder.manage_delLocalRoles(userids=[username, ])  # noqa: F821
