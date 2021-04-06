# Script (Python) "index2_html"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
##title=Reporters in EU
##
# Import a standard function, and get the HTML request and response objects.
#from Products.PythonScripts.standard import string
REQUEST = container.REQUEST
RESPONSE = REQUEST.RESPONSE
role = 'Reporter'


def pathcompare(p1, p2):
    return cmp(p1[0], p2[0])


print context.standard_html_header(context, context.REQUEST)
print """<div class="quickjumps">
<h2>Jump to</h2>
<a href="#byperson">Sorted by person</a>
</div>
<a name="bypath"></a><h1>%ss by path</h1>
<table class="datatable">      
<tr>
<th>Path</th>
<th>Last change</th>
<th>Obl</th>
<th>%ss</th>
</tr>""" % (role, role)
persons = {}
results = []
hits = container.Catalog(meta_type='Report Collection')
for hit in hits:
    obj = hit.getObject()
    results.append((obj.absolute_url(0),
                    '/eu/' + obj.absolute_url(1),
                    obj.bobobase_modification_time().Date(),
                    obj.users_with_local_role(role),
                    obj.dataflow_uris
                    ))
root_obj = context.restrictedTraverse(['', ])
results.append((root_obj.absolute_url(0),
                '/eu/',
                root_obj.bobobase_modification_time().Date(),
                root_obj.users_with_local_role(role),
                []
                ))
results.sort(pathcompare)
evenstr = ''
for hit in results:
    members = hit[3]
    obl = "None"
    hover = "None"
    if len(hit[4]) > 0:
        ol = []
        for o in hit[4]:
            ol.append(context.dataflow_lookup(o)['TITLE'])
        obl = string.join(ol, '\n')
        hover = str(len(hit[4]))
    if members != []:
        print """<tr%s>""" % evenstr
        print """<td><a href="%s">%s</a></td>
    <td>%s</td>
    <td title="%s">%s</td>
    <td>""" % (hit[0], hit[1], hit[2], obl, hover)
        for m in members:
            print """<a href="http://www.eionet.europa.eu/directory/user?uid=%s">%s</a>""" % (m, m)
            if not persons.has_key(m):
                persons[m] = []
            persons[m].append(hit[1])
        print """</td></tr>"""
        if evenstr == '':
            evenstr = ' class="zebraeven"'
        else:
            evenstr = ''


print """</table>
<div class="quickjumps">
<h2>Jump to</h2>
<a href="#bypath">Sorted by path</a>
</div>
<a name="byperson"></a><h2>By person</h2>
<table class="datatable">
<tr>
  <th>%s</th>
  <th>Path</th>
</tr>""" % role

evenstr = ''
pitems = persons.items()
pitems.sort()
for account, paths in pitems:
    err = ''
    if string.find(account, ' ') >= 0:
        err = 'Spaces&nbsp;in&nbsp;userid! '
    print '''<tr%s><td valign="top">%s<a href="http://www.eionet.europa.eu/directory/user?uid=%s">%s</a></td>
<td valign="top">%s</td>
</tr>''' % (evenstr, err, account, account, string.join(paths, '<br/>'))
    if evenstr == '':
        evenstr = ' class="zebraeven"'
    else:
        evenstr = ''

print "</table>"
print context.standard_html_footer(context, context.REQUEST)

return printed
