res = container.localities_table()
ldict = {}
for item in res:
    ldict[item['uri']] = item
return ldict
