res = container.dataflow_table()
dfdict = {}
for item in res:
    dfdict[item['uri']] = item
return dfdict
