## Script (Python) "dataflow_dict"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
top = container.REQUEST.PARENTS[-1]
res = top.dataflow_rod()
dfdict = {}
for item in res:
    if item['uri'][:5] == 'null/':
        item['uri'] = 'http://rod.eionet.europa.eu/obligations/' + item['uri'][5:]
    dfdict[item['uri']] = item
return dfdict
