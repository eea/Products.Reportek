## Script (Python) "table_to_dict"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=table, key
##title=Make a lookup dictionary from a list
##
mydict = {}
for item in table:
    mydict[item[key]] = item
return mydict
