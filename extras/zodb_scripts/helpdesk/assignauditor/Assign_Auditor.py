## Script (Python) "Assign_Auditor"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=REQUEST=None, **kwargs
##title=
##
if REQUEST:
    kwargs.update(REQUEST.form)

query = {
  'dataflow_uris': kwargs.get('cobligation', ''),
  'meta_type': 'Report Collection',
}

catalog = context.Catalog
brains = catalog(**query)

countries = kwargs.get('ccountries', [])
res = []
for brain in brains:
    doc = brain.getObject()
    try:
        country = doc.getCountryCode()
    except KeyError:
        continue
    if country.lower() not in countries:
        continue
    for user in kwargs.get('dns', []):
        doc.manage_setLocalRoles(user, ['Auditor',])
    res.append(doc)
return res
