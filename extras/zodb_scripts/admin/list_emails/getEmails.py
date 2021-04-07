# Script (Python) "getEmails"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=dataflow_uris, country, separator=0
# title=
##
local_users = {}
global_users = {}

try:
    separator = int(separator)  # noqa: F821
except Exception:
    separator = 0

if country:  # noqa: F821
    collections = context.Catalog(  # noqa: F821
        meta_type=['Report Collection'],
        dataflow_uris='http://rod.eionet.europa.eu/obligations/%s' %
        dataflow_uris,  # noqa: F821
        country=country)  # noqa: F821
else:
    collections = context.Catalog(  # noqa: F821
        meta_type=['Report Collection'],
        dataflow_uris='http://rod.eionet.europa.eu/obligations/%s' %
        dataflow_uris)  # noqa: F821

for brain in collections:
    collection = context.Catalog.getobject(brain.data_record_id_)  # noqa: F821

    # get local reporters
    for user, roles in collection.get_local_roles():
        if 'Reporter' in list(roles):
            local_users[user] = ''

    # get top-level reporters (country reporters)
    path = collection.restrictedTraverse(collection.getPhysicalPath()[1])
    for user, roles in path.get_local_roles():
        if 'Reporter' in list(roles):
            global_users[user] = ''


ulocal = []
for user in local_users:
    user_ob = context.acl_users.ldapmultiplugin.acl_users.getUserById(user)  # noqa: F821
    if user_ob:
        ulocal.append('%s <%s>' %
                      (unicode(user_ob.cn, 'latin-1'), user_ob.mail))

uglobal = []
for user in global_users:
    user_ob = context.acl_users.ldapmultiplugin.acl_users.getUserById(user)  # noqa: F821
    if user_ob:
        uglobal.append('%s <%s>' %
                       (unicode(user_ob.cn, 'latin-1'), user_ob.mail))

if separator:
    delimiter = ', '
else:
    delimiter = '; '
return delimiter.join(ulocal), delimiter.join(uglobal)  # noqa: F999
