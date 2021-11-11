REQUEST = container.REQUEST  # noqa: F821
RESPONSE = REQUEST.RESPONSE
role = 'Reporter'
filtered_obl = REQUEST.form.get('obligation', None)


def pathcompare(p1, p2):
    return cmp(p1[0], p2[0])


print context.standard_html_header(context, context.REQUEST)  # noqa: F821

print """<a name="bypath"></a>
<div id="tabbedmenu">
  <ul>
    <li id="currenttab"><span>Grouped by path</span></li>
    <li><a href=/admin/list_reporters/by_person>Grouped by person</a></li>
  </ul>
</div>
<div id="tabbedmenuend"></div>"""

print """<h1>Filter by obligation</h1>
<form method="get">
  <select id="obligation" name="obligation">
  <option value="">(All obligations)</option>
"""

data = context.ReportekEngine.dataflow_table_grouped()  # noqa: F821
groups = data[0]
items = data[1]

for group in groups:
    group_label = group if len(group) <= 80 else group[:77]
    print """<optgroup label="%s">""" % group_label
    for item in items[group]:
        extra_attributes = 'class="terminated"' if item.get(
            'terminated', None) == '1' else ''
        if item['uri'] == filtered_obl:
            extra_attributes = extra_attributes + ' selected="selected"'
        print """<option value="%s" %s>""" % (item['uri'], extra_attributes)
        prefix = ' '.join(item['SOURCE_TITLE'].split()[0:2])
        if len(item['TITLE']) <= 80:
            title = item['TITLE']
        else:
            title = "%s ..." % item['TITLE'][:77]
        print """[%s] %s</option>""" % (prefix, title)
    print """</optgroup>"""

print """</select><input type="submit" value="Filter" /></form>"""

print """<table class="datatable">
<tr>
<th>Path</th>
<th>Last change</th>
<th>Obligations</th>
<th>%ss</th>
</tr>""" % role
persons = {}
results = []
hits = container.Catalog(meta_type='Report Collection')  # noqa: F821
for hit in hits:
    obj = hit.getObject()
    if not filtered_obl or filtered_obl in obj.dataflow_uris:
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
    obl = ""
    hover = "0 obligation(s)"
    if len(hit[4]) > 0:
        ol = []
        for o in hit[4]:
            ol.append(context.dataflow_lookup(o)['TITLE'])  # noqa: F821
        obl = string.join(ol, '<br />')  # noqa: F821
        hover = str(len(hit[4])) + " obligation(s)"
    if members != []:
        print """<tr%s>""" % evenstr
        print """<td><a href="%s">%s</a></td>
    <td>%s</td>
    <td title="%s">%s</td>
    <td>""" % (hit[0], hit[1][:40], hit[2], hover, obl)
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

print "</table>"

print context.standard_html_footer(context, context.REQUEST)  # noqa: F821

return printed  # noqa
