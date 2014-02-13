## Script (Python) "BDR Reporting manual_2012-v1.1.pdf"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
context.REQUEST.RESPONSE.redirect(container.REQUEST.VIRTUAL_URL.replace('/BDR%20Reporting%20manual_2012-v1.1.pdf',''), lock=0)
