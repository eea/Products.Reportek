## Script (Python) "headerlines"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
# Example code:

# Import a standard function, and get the HTML request and response objects.
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE

print request.get_header('HTTP_AUTHORIZATION','ukendt')
print "---------------------"
for k,v in request.items():
    print k,v
return printed
