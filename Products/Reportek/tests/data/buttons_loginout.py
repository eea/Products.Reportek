# Script (Python) "buttons_loginout"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=Buttons for login and out
##
request = container.REQUEST  # noqa: F821
RESPONSE = request.RESPONSE

if ('AUTHENTICATED_USER' in request
        and request['AUTHENTICATED_USER'].getUserName() != 'Anonymous User'):
    userobj = request['AUTHENTICATED_USER']
    print ("""<span><a id="logoutlink" href="/loggedout">"""
           """Logout (%s)</a></span>""" % userobj.getUserName())
else:
    print """<a id="loginlink" href="/loggedin">Login</a>"""
return printed  # noqa: F999
