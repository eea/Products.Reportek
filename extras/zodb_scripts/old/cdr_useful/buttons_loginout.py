# Script (Python) "buttons_loginout"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=Buttons for login and out
##
request = container.REQUEST
RESPONSE = request.RESPONSE

if request.has_key('AUTHENTICATED_USER') and request['AUTHENTICATED_USER'].getUserName() != 'Anonymous User':
    userobj = request['AUTHENTICATED_USER']
    print """<h2>Logged in as<br />%s</h2>""" % userobj.getUserName()
    print """<ul>
<li><a href="/loggedout">Logout</a></li>"""
    if userobj.has_permission("View management screens", container):
        print """<li><a href="manage">Manage</a></li>"""
else:
    print """<h2>Not logged in</h2>
<ul>
<li><a href="/loggedin">Login</a></li>"""
print "</ul>"
return printed
