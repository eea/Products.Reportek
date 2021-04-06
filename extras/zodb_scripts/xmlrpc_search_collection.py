# Script (Python) "xmlrpc_search_collection"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=country
# title=Find collection harbouring AQ-1 and return path
##
for item in container.Catalog({'meta_type': 'Report Collection',
                               'dataflow_uris': 'http://rod.eionet.europa.eu/obligations/26',
                               'country': country}):
    return item.getPath()
