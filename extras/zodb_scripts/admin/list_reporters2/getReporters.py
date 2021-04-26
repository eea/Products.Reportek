# flake8: noqa
# Script (Python) "getReporters"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=dataflow_uris, country
# title=
##
users = {}
if country:  # noqa: F821
    collections = context.Catalog(  # noqa: F821
        meta_type=['Report Collection'],
        dataflow_uris='http://rod.eionet.europa.eu/obligations/%s' %
        dataflow_uris, country=country)  # noqa: F821
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
            country = collection.getCountryName()
            if not users.get(country):
                users[country] = list()
            users[country].append(user)
ulocal = []

for country in users:
    for user in users[country]:
        user_ob = context.acl_users.ldapmultiplugin.acl_users.getUserById(user)  # noqa: F821
        if user_ob:
            ulocal.append('%s: %s (uid=%s,mail=%s)' % (
                country, unicode(user_ob.cn, 'latin-1'), user, user_ob.mail))
return ulocal  # noqa: F999
