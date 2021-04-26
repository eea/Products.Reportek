# flake8: noqa
# Script (Python) "Assign_preparer"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=REQUEST=None, **kwargs
# title=
##
if REQUEST:  # noqa: F821
    kwargs.update(REQUEST.form)  # noqa: F821

query = {
    'dataflow_uris': kwargs.get('cobligation', ''),  # noqa: F821
    'meta_type': 'Report Collection',
}

catalog = context.Catalog  # noqa: F821
brains = catalog(**query)

countries = kwargs.get('ccountries', [])  # noqa: F821
res = []
for brain in brains:
    doc = brain.getObject()
    try:
        country = doc.getCountryCode()
    except KeyError:
        continue
    if country.lower() not in countries:
        continue
    for user in kwargs.get('dns', []):  # noqa: F821
        doc.manage_setLocalRoles(user, ['Preparer', ])
    res.append(doc)
return res  # noqa: F999
