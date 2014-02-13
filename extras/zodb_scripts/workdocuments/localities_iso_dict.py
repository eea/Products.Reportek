## Script (Python) "localities_iso_dict"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Build dictionary with ISO as key
##
res = container.localities_table()
ldict = {}
for item in res:
    ldict[item['iso']] = item
return ldict
