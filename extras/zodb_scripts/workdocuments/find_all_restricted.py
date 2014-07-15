## Script (Python) "find_all_restricted"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
#from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE
RESPONSE.setHeader('content-type', 'text/plain')

for hit in context.Catalog(
      meta_type='Report Envelope',
      dataflow_uris='http://rod.eionet.europa.eu/obligations/269'):
    env = hit.getObject()
    for obj in env.objectValues('Report Document'):
        if not obj.acquiredRolesAreUsedBy('View'):
            print obj.id, obj.getCountryCode()
return printed
