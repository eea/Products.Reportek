# Script (Python) "localities_iso_dict"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
res = container.localities_table()
ldict = {}
for item in res:
    ldict[item['iso']] = item
ldict['YU'] = {'uri': 'http://rod.eionet.europa.eu/spatial/41',
               'name': 'Serbia and Montenegro', 'iso': 'CS'}
return ldict
