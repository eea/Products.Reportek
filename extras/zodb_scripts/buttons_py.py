## Script (Python) "buttons_py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
buttons = [
('/','BDR home','BDR home'),
('/searchdataflow', 'Search', 'Search' ),
#('ReportekEngine/subscriptions_html', 'Subscribe to receive notifications', 'Notifications' ),
('/help', 'Introduction to Reportnet Repository', 'Help' ),
('/selfregister', 'Create an account to report statistics', 'Self-registration' ),
 ]

# The syntax is:
#  ( 'url', 'description', 'text on image' ),
# Remember to end with a comma.
from Products.PythonScripts.standard import html_quote
print '<ul>'
for item in buttons:
    print '<li><a href="%s" title="%s" i18n:translate="" i18n:attributes="title">%s </a></li>' % (html_quote(item[0]), item[1], item[2] )

userobj = container.REQUEST['AUTHENTICATED_USER']

if userobj.getId():
    print '<li><a href="https://bdr.eionet.europa.eu/registry/edit_organisation?uid=%s" i18n:translate="">Edit organisation</a></li>' %userobj.getId()

print '</ul>'
return printed
