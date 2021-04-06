# Script (Python) "find_physicalpathspy"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
#from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE = request.RESPONSE
RESPONSE.setHeader('content-type', 'text/plain')

for hit in context.Catalog(
        meta_type='Report Envelope',
        dataflow_uris='http://rod.eionet.europa.eu/obligations/269'):
    env = hit.getObject()
    for obj in env.objectValues('Report Document'):
        physp = obj.physicalpath()[27:]
        if obj.id[-4:] == '.gml' and obj.absolute_url(1) != physp:
            print "%s\t%s" % (obj.absolute_url(1), physp)
return printed
