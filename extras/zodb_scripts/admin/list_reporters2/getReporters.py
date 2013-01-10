## Script (Python) "getReporters"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=dataflow_uris
##title=
##
users = {}
for brain in context.Catalog(meta_type = ['Report Collection'], dataflow_uris='http://rod.eionet.eu.int/obligations/%s' % dataflow_uris):
    collection = context.Catalog.getobject(brain.data_record_id_)
    #get local reporters
    for user, roles in collection.get_local_roles():
        if 'Reporter' in list(roles):
            country = collection.getCountryName()
            if not users.get(country):
                users[country]= list()
            users[country].append(user)
ulocal = []

for country in users:
    for user in users[country]:
        user_ob = context.acl_users.ldapmultiplugin.acl_users.getUserById(user)
        if user_ob:
            ulocal.append('%s: %s (uid=%s,mail=%s)' % (country, unicode(user_ob.cn, 'latin-1'), user, user_ob.mail))
return ulocal
