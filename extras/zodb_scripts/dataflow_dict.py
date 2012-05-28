top = container.REQUEST.PARENTS[-1]
res = top.dataflow_rod()
dfdict = {}
for item in res:
    if item['uri'][:5] == 'null/':
        item['uri'] = 'http://rod.eionet.europa.eu/obligations/' + item['uri'][5:]
    dfdict[item['uri']] = item
return dfdict
