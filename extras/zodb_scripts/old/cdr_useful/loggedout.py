## Script (Python) "loggedout"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Logs you out from the website
##
REQUEST = container.REQUEST
RESPONSE =  REQUEST.RESPONSE
print context.standard_html_header(context,context.REQUEST)
#also works: print context['standard_html_header'](context,context.REQUEST)
print "<h1>Next time, click on the OK button in the login dialogue</h1>\n"
if REQUEST.AUTHENTICATED_USER.getUserName() != 'Anonymous User':
    RESPONSE.setStatus(401)
    RESPONSE.setHeader('WWW-Authenticate','Basic realm="Zope"')
else:
    if REQUEST.has_key('HTTP_REFERER') and REQUEST['HTTP_REFERER'] != '':
        RESPONSE.redirect(REQUEST['HTTP_REFERER'])
print context.standard_html_footer(context,context.REQUEST)
return printed
