# flake8: noqa
# Script (Python) "A_getlocalusers"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
# Example code:

# Import a standard function, and get the HTML request and response objects.
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE = request.RESPONSE

for dn, roles in container.acl_users.getLocalUsers():
    if 'Client' in roles:
        uobj = container.acl_users.getUserDetails(dn, 'dictionary')
        if uobj:
            print "%-30s %s" % (dn, uobj.get('cn', ['Unknown'])[0])
return printed
