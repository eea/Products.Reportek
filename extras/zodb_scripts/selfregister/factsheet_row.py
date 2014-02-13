## Script (Python) "factsheet_row"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=value, label
##title=Show a factsheet row
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE

def safe_quote(value):
    text = html_quote(value)
    return unicode(text,'utf-8').encode('ascii','xmlcharrefreplace')

print '''<tr>'''
print '''   <th scope="row" style="text-align:left">%s</th>''' % label
print '''   <td>%s</td>''' % safe_quote(value)
print '''</tr>'''

return printed
