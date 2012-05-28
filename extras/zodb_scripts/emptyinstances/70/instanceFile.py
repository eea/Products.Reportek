## Script (Python) "instanceFile"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Empty instance for Directive on waste 75/442
##
l_parent = context.xmlexports.waste
l_file = getattr(l_parent, 'emptyinstance_75442.xml')
return l_file
