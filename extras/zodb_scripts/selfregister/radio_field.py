## Script (Python) "radio_field"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=fieldname, fieldvalue, fieldlabel, valresult
##title=Create a radio box - value is always "1"
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE


status=''
if request.form.get(fieldname,'') == fieldvalue:
    status=' checked="checked"'
if valresult.has_key(fieldname):
    err_class=' class="error"'
else: err_class=''

print '''<input type="radio" id="%s" name="%s" value="%s"%s%s/>''' % (fieldname+'_'+fieldvalue, \
  fieldname, fieldvalue, status, err_class)
print '''<label for="%s">%s</label>''' % (fieldname+'_'+fieldvalue, html_quote(fieldlabel))
return printed
