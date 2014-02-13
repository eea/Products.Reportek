## Script (Python) "optiontabs"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=option_tabs
##title=Create tabs
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST

n = len(option_tabs)-1
a = 0
ot_inx = 0
for ot in option_tabs:
    action = ot['action']
    if request.URL[-len(action):] == action or request.URL[-11:] == '/index_html' and ot_inx == 0:
        a = ot
    ot_inx = ot_inx + 1

    if request.has_key('management_view') and management_view==label:
        a = ot
    new_action=string.replace(action,'/index_html','/')

#  for debugging...
#  URL  (whole string): <dtml-var URL><br>
#  action (substring): <dtml-var action><br>
#  new action        : <dtml-var new_action><br>
#  Index: <dtml-var "_.string.find(URL,new_action[:_.string.find(new_action,'?')])"><br>

    if string.find(request.URL,new_action[:string.find(new_action,'?')])>-1:
        a = ot

print '''<div id="tabbedmenu">
    <ul>'''
for ot in option_tabs:
    if ot == a:
        print '''<li id="currenttab"><span>%s</span></li>''' % html_quote(ot['label'])
    else:
        print '''<li><a href="%s">%s</a></li>''' % (html_quote(ot['action']), html_quote(ot['label']))

print '''</ul>
</div>
<div id="tabbedmenuend"></div>'''

return printed
