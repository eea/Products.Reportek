# flake8: noqa
# flake8: noqa
# Script (Python) "publicObjects"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
"""
Returns sub-folders and DTML documents that have a
true 'siteMap' property.
"""
results = []
for object in context.objectValues(['Folder', 'Repository Referral',
                                    'Report Document', 'Report Envelope', 'Report Collection']):
    if object.meta_type == 'Folder' and len(object.id) == 2 or object.meta_type != 'Folder':
        results.append(object)
return results
