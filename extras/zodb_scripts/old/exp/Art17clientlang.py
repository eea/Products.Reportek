# Script (Python) "Art17clientlang"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
l = container.REQUEST.HTTP_ACCEPT_LANGUAGE
llist = l.lower().split(",")
p = llist[0].split('-')
return p[0]
