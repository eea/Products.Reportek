## Script (Python) "instanceFile"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Empty instance for ELV questionnaire
##
l_parent = context.xmlexports.dir200053ec
l_file = getattr(l_parent, 'emptyinstance.xml')
return l_file
