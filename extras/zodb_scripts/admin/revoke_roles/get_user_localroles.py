# Script (Python) "get_user_localroles"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=username
# title=
##
results = []
for brain in context.Catalog(meta_type='Report Collection'):  # noqa: F821
    coll = brain.getObject()
    local_roles = coll.get_local_roles_for_userid(username)  # noqa: F821
    if local_roles:
        results.append({
            'country': coll.getCountryName,
            'collection': coll,
            'roles': ', '.join([role for role in local_roles])
        })

return results  # noqa: F999
