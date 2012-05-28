res = container.localities_table()
ldict = {}
for item in res:
    ldict[item['iso']] = item
ldict['YU'] = {'uri': 'http://rod.eionet.eu.int/spatial/41', 'name': 'Serbia and Montenegro', 'iso': 'CS'}
return ldict
