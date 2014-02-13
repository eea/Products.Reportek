## Script (Python) "upload.html"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
context.REQUEST.RESPONSE.redirect(container.REQUEST.VIRTUAL_URL.replace('/upload.html',''), lock=0)
