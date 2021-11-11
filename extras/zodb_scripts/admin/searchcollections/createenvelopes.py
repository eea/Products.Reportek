# flake8: noqa
# Script (Python) "createenvelopes"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=dataflow_uris, title, year
# title=Creates envelopes for WFD-Art3
##
request = container.REQUEST  # noqa: F821
RESPONSE = request.RESPONSE

descr = ""
endyear = ""
partofyear = "Whole Year"
locality = ""

print context.standard_html_header(context, context.REQUEST)  # noqa: F821
print "<h1>Results</h1>"
print "<ol>"
# finds the collection in the catalog
for item in container.Catalog(  # noqa: F821
    {'meta_type': 'Report Collection',
     'dataflow_uris': dataflow_uris}):  # noqa: F821
    collection = item.getObject()
    print '<li>Creating in: <a href="%s">%s</a></li>' % (item.getPath(),
                                                         item.getPath())

    collection.manage_addProduct['Reportek'].manage_addEnvelope(title, descr,  # noqa: F821
                                                                year, endyear,  # noqa: F821
                                                                partofyear,
                                                                locality)

print "</ol>"

print context.standard_html_footer(context, context.REQUEST)  # noqa: F821
return printed  # noqa: F999
