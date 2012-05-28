request = container.REQUEST
RESPONSE =  request.RESPONSE

descr=""
endyear=""
partofyear="Whole Year"
locality=""

print context.standard_html_header(context,context.REQUEST)
print "<h1>Results</h1>"
print "<ol>"
# finds the collection in the catalog
for item in container.Catalog({'meta_type':'Report Collection', 'dataflow_uris':dataflow_uris}):
    collection = item.getObject()
    print '<li>Creating in: <a href="%s">%s</a></li>' % (item.getPath(), item.getPath())

    collection.manage_addProduct['Reportek'].manage_addEnvelope(title, descr, year,
      endyear, partofyear, locality)

print "</ol>"

print context.standard_html_footer(context,context.REQUEST)
return printed
