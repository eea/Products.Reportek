request = container.REQUEST
RESPONSE =  request.RESPONSE

if request.has_key('AUTHENTICATED_USER') and request['AUTHENTICATED_USER'].getUserName() != 'Anonymous User':
    userobj = request['AUTHENTICATED_USER']
    print """<span><a id="logoutlink" href="/loggedout">Logout (%s)</a></span>""" % userobj.getUserName()
else:
    print """<a id="loginlink" href="http://%s/loggedin">Login</a>""" % request.get('HTTP_X_FORWARDED_HOST','')
return printed
