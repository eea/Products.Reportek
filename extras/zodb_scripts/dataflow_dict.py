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
res = top.obligations.list_obligations()
dfdict = {}
for item in res:
    dfdict[item['uri']] = item
return dfdict
