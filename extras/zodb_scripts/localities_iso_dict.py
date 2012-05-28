## Script (Python) "localities_iso_dict"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=country=None
##title=Build localities with ISO code as key
##
dummy = {'uri': '', 'name': 'Unknown', 'iso': 'XX'}
res = container.localities_table()
ldict = {}
for item in res:
    ldict[item['iso']] = item
if country:
   return ldict.get(country, dummy)
else:
   return ldict
