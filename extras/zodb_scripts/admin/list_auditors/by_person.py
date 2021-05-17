REQUEST = container.REQUEST  # noqa: F821
RESPONSE = REQUEST.RESPONSE
role = 'Auditor'


def pathcompare(p1, p2):
    return cmp(p1[0], p2[0])


print context.standard_html_header(context, context.REQUEST)  # noqa: F821

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

for hit in results:
    members = hit[3]
    if members != []:
        for m in members:
            if m not in persons:
                persons[m] = []
            persons[m].append(hit[1])

print """
<div id="tabbedmenu">
  <ul>
    <li><a href="/admin/list_auditors">Grouped by path</a></li>
    <li id="currenttab"><span>Grouped by person</span></li>
  </ul>
</div>
<div id="tabbedmenuend"></div>
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
    print '''<tr%s><td valign="top">%s\
    <a href="http://www.eionet.europa.eu/directory/user?uid=%s">%s</a></td>
<td valign="top">%s</td>
</tr>''' % (evenstr, err, account, account,
            string.join(paths, '<br/>'))  # noqa: F821
    if evenstr == '':
        evenstr = ' class="zebraeven"'
    else:
        evenstr = ''

print "</table>"
print context.standard_html_footer(context, context.REQUEST)  # noqa: F821

return printed  # noqa
