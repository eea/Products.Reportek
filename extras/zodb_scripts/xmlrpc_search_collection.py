## Script (Python) "xmlrpc_search_collection"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=country
##title=
##
for item in container.Catalog({'meta_type':'Report Collection',
   'dataflow_uris':'http://rod.eionet.eu.int/obligations/26',
   'country': country}):
    return item.getPath()
