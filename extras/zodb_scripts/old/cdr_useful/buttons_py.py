# flake8: noqa
# Script (Python) "buttons_py"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=Grey leftside buttons for services
##
from Products.PythonScripts.standard import html_quote
buttons = [
    ('/searchdataflow', 'Search', 'Search'),
    ('/ReportekEngine/globalworklist',
     "The envelopes that haven't been released yet", 'Global worklist'),
    ('/help', 'Introduction to Reportnet Repository', 'Help'),
]
# This is a rather complex piece of code, but it is even more complex to
# write it as straight HTML.

# The syntax is:
#  ( 'url', 'description', 'text on image' ),
# Remember to end with a comma.
# ('http://eea.eionet.eu.int:9000/','Directory Services','Directory'),
print '<h2>Services</h2>'
print '<ul>'
for item in buttons:
    print '<li><a href="%s" title="%s">%s</a></li>' % (html_quote(item[0]), item[1], item[2])

print '</ul>'
return printed
