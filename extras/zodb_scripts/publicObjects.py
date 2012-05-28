"""
Returns sub-folders and DTML documents that have a
true 'siteMap' property.
"""
results=[]
for object in context.objectValues(['Folder', 'Repository Referral',
'Report Document','Report Envelope','Report Collection']):
    if object.meta_type == 'Folder' and len(object.id) == 2 or object.meta_type != 'Folder': 
        results.append(object)
return results
