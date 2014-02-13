## Script (Python) "checkbox_field"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=fieldname, valresult
##title=Create a checkbox - value is always "1"
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE


status=''
if request.form.get(fieldname,'') != '':
    status=' checked="checked"'
if valresult.has_key(fieldname):
    err_class=' class="error"'
else: err_class=''

print '''<input type="checkbox" id="%s" name="%s" value="1"%s%s/>''' % (fieldname, fieldname, status, err_class)
return printed
