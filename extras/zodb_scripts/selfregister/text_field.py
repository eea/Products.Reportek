## Script (Python) "text_field"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=fieldname, label, valresult, required=0
##title=Create a text entry field
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE

if required: req_class=" required"
else: req_class=""
if valresult.has_key(fieldname):
    err_class=' class="error"'
else: err_class=''

print '''<tr>'''
print '''   <td><label for="%s" class="question%s">%s</label></td>''' % (fieldname, req_class, label)
print '''   <td><input type="text" size="50" id="%s" name="%s" value="%s"%s/>''' % (fieldname, fieldname, html_quote(request.form.get(fieldname,'')), err_class)
if valresult.has_key(fieldname):
    print '''<div class="error-hint">%s</div>''' % html_quote(valresult[fieldname])
print '''</td>'''
print '''</tr>'''


return printed
