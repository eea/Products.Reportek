# Script (Python) "Aupdaterarfiles"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
fs = []
for e in container.Catalog(meta_type='Report Envelope'):
    eo = e.getObject()
    fs.extend([x for x in eo.objectValues(
        'Report Document') if x.id[-4:] == '.rar'])

for x in fs:
    x.manage_editDocument(content_type='application/x-rar-compressed')
    print x.absolute_url()
    print x.content_type

return printed
