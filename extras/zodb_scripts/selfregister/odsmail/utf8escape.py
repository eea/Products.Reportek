## Script (Python) "utf8escape"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=text, quote=0
##title=Escape national characters UTF-8
##
from Products.PythonScripts.standard import html_quote
if quote:
    text = html_quote(text)
return unicode(text,'utf-8').encode('ascii','xmlcharrefreplace')
