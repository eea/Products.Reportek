## Script (Python) "getReporters"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=dataflow_uris
##title=
##
local_users = {}

for brain in context.Catalog(meta_type = ['Report Collection'], dataflow_uris='http://rod.eionet.eu.int/obligations/%s' % dataflow_uris):
    collection = context.Catalog.getobject(brain.data_record_id_)

    #get local reporters
    for user, roles in collection.get_local_roles():
        if 'Reporter' in list(roles):
            local_users[user] = collection.getCountryName()

ulocal = []
for user in local_users:
    user_ob = context.acl_users.getUserById(user)
    if user_ob:
        ulocal.append('%s: %s (uid=%s,mail=%s)' % (local_users[user], unicode(user_ob.cn, 'latin-1'), user, user_ob.mail))

return ulocal
