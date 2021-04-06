# Script (Python) "dataflow_dict"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
res = container.dataflow_table()
dfdict = {}
for item in res:
    dfdict[item['uri']] = item
return dfdict
