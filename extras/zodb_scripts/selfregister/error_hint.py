## Script (Python) "error_hint"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=fieldname, valresult
##title=Create text with hint
##
from Products.PythonScripts.standard import html_quote

if valresult.has_key(fieldname):
    print '''<div class="error-hint">%s</div>''' % html_quote(valresult[fieldname])

return printed
