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
        local_roles = [role for role in doc.get_local_roles_for_userid(user) if role != 'Auditor']
        if local_roles:
            doc.manage_setLocalRoles(user, local_roles)
        else:
            doc.manage_delLocalRoles(userids=[user,])
    res.append(doc)
return res
