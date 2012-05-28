dummy = {'uri': '', 'name': 'Unknown', 'iso': 'XX'}
res = container.localities_table()
ldict = {}
for item in res:
    ldict[item['iso']] = item
if country:
   return ldict.get(country, dummy)
else:
   return ldict
