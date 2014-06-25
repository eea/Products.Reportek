## Script (Python) "fortest"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
for k in container.objectValues('Report Envelope'):
  print k.id, k.title, k.released

return printed
