## Script (Python) "localities_dict"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=country=None
##title=Build dictionary with URI as key
##
dummy = {'uri': '', 'name': 'Unknown', 'iso': 'XX'}
res = container.localities_table()
ldict = {}
for item in res:
    ldict[item['uri']] = item
if country:
   return ldict.get(country, dummy)
else:
   return ldict
