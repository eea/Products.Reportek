## Script (Python) "buttons_loginout"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
request = container.REQUEST
RESPONSE =  request.RESPONSE

if request.has_key('AUTHENTICATED_USER') and request['AUTHENTICATED_USER'].getUserName() != 'Anonymous User':
    userobj = request['AUTHENTICATED_USER']
    print """<span><a id="logoutlink" href="/loggedout" i18n:translate="">Logout (<span i18n:name="username">%s</span>)</a></span>""" % userobj.getUserName()
else:
    print """<a id="loginlink" href="/loggedin" i18n:translate="">Login</a>"""
return printed
