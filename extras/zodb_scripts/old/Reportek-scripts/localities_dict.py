## Script (Python) "localities_dict"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Build dictionary with uri as key
##
res = container.localities_table()
ldict = {}
for item in res:
    ldict[item['uri']] = item
return ldict
