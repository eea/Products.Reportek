## Script (Python) "utf8toiso"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=text
##title=
##
return unicode(text,'utf-8').encode('cp1252','ignore')
