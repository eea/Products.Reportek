# Script (Python) "find_collections_by_dataflow_py"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=Creates envelopes for WFD-Art3
##
request = container.REQUEST
RESPONSE = request.RESPONSE

eeams = ['at', 'be', 'bg',
         'cy', 'cz', 'dk', 'ee', 'fi', 'fr', 'de', 'gr', 'hu',
         'is', 'ie', 'it', 'lv', 'li', 'lt', 'lu', 'mt',
         'nl', 'no', 'pl', 'pt', 'ro', 'sk', 'si',
         'es', 'se', 'ch', 'tr', 'gb']

obligation = 'http://rod.eionet.europa.eu/obligations/525'
title = "Subunit geometries – submission 2008"
descr = ""
year = "2008"
endyear = ""
partofyear = "Whole Year"
locality = ""

# finds the collection in the catalog
for item in container.Catalog({'meta_type': 'Report Collection', 'dataflow_uris': obligation}):
    collection = item.getObject()
    print item.getPath()
    print item.country
#
    collection.manage_addProduct['Reportek'].manage_addEnvelope(title, descr, year,
                                                                endyear, partofyear, locality)
return printed
