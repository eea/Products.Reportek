## Script (Python) "buttons_py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Grey leftside buttons for services
##
buttons = [
('/searchdataflow', 'Search', 'Search by obligation' ),
('/searchxml', 'Search', 'Search XML files' ),
('/ReportekEngine/searchfeedbacks', 'Search', 'Search for feedback'),
('/ReportekEngine/globalworklist', "The envelopes that haven't been released yet", 'Global worklist'),
('ReportekEngine/subscriptions_html', 'Subscribe to receive notifications', 'Notifications' ),
('/help', 'Introduction to Reportnet Repository', 'Help' ),
 ]
# This is a rather complex piece of code, but it is even more complex to
# write it as straight HTML.

# The syntax is:
#  ( 'url', 'description', 'text on image' ),
# Remember to end with a comma.
# ('http://eea.eionet.eu.int:9000/','Directory Services','Directory'),
from Products.PythonScripts.standard import html_quote

print '<ul>'
for item in buttons:
    print '<li><a href="%s" title="%s">%s </a></li>' % (html_quote(item[0]), item[1], item[2] )

userobj = container.REQUEST['AUTHENTICATED_USER']
if userobj.has_permission("View management screens", container):
    print """<li><a href="manage">Manage </a></li>"""

print '</ul>'
return printed
