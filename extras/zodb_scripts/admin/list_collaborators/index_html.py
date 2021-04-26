# flake8: noqa
# Script (Python) "index_html"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
# Import a standard function, and get the HTML request and response objects.
# from Products.PythonScripts.standard import string
REQUEST = container.REQUEST  # noqa: F821
RESPONSE = REQUEST.RESPONSE
role = 'Data Collaborator'


def pathcompare(p1, p2):
    return cmp(p1[0], p2[0])


print context.standard_html_header(context, context.REQUEST)  # noqa: F821
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
hits = container.Catalog(meta_type='Report Collection')  # noqa: F821
for hit in hits:
    obj = hit.getObject()
    results.append((obj.absolute_url(0),
                    '/' + obj.absolute_url(1),
                    obj.bobobase_modification_time().Date(),
                    obj.users_with_local_role(role),
                    list(obj.dataflow_uris)
                    ))
root_obj = context.restrictedTraverse(['', ])  # noqa: F821
results.append((root_obj.absolute_url(0),
                '/',
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
            ol.append(context.dataflow_lookup(o)['TITLE'])  # noqa: F821
        obl = string.join(ol, '\n')  # noqa: F821
        hover = str(len(hit[4]))
    if members != []:
        print """<tr%s>""" % evenstr
        print """<td><a href="%s">%s</a></td>
    <td>%s</td>
    <td title="%s">%s</td>
    <td>""" % (hit[0], hit[1], hit[2], obl, hover)
        for m in members:
            print """<a\
             href="http://www.eionet.europa.eu/directory/user?uid=%s">%s\
             </a>""" % (m, m)
            if m not in persons:
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
    if string.find(account, ' ') >= 0:  # noqa: F821
        err = 'Spaces&nbsp;in&nbsp;userid! '
    print '''<tr%s><td valign="top">%s<a\
     href="http://www.eionet.europa.eu/directory/user?uid=%s">%s</a></td>
<td valign="top">%s</td>
</tr>''' % (evenstr, err, account, account, string.join(paths, '<br/>'))  # noqa: F821
    if evenstr == '':
        evenstr = ' class="zebraeven"'
    else:
        evenstr = ''

print "</table>"
print context.standard_html_footer(context, context.REQUEST)  # noqa: F821

return printed  # noqa: F999
