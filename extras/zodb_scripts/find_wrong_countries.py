# Script (Python) "find_wrong_countries"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=Collections and envelopes with a wrong country
##
print 'The collections and envelopes with a wrong country\n\n'

# for a in container.Catalog(meta_type=['Report Collection', 'Report Envelope']):
for a in container.Catalog(meta_type=['Report Envelope']):
    x = a.getObject()
    top_parent = context.restrictedTraverse(x.getPhysicalPath()[1])
    if hasattr(top_parent, 'country'):
        if x.country != top_parent.country:
            print 'Before: %s, %s' % (x.absolute_url(), x.getCountryName())
            if x.meta_type == 'Report Collection':
                x.manage_changeCollection(country=top_parent.country)
            else:
                x.manage_changeEnvelope(country=top_parent.country)
            print 'After: %s' % x.getCountryName()

return printed
