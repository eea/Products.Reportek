# flake8: noqa
# Script (Python) "searchxmlfiles"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
##parameters=schema, country=None
# title=XML-RPC script to find XML files matching a specific schema/doctype
##
from Products.PythonScripts.standard import html_quote


def print_as_elm(mydict):
    attrs = []
    for elm, value in mydict.items():
        attrs.append('%s="%s"' % (elm, html_quote(str(value))))
    return "<file %s/>" % " ".join(attrs)


reslist = []

search_args = {
    'meta_type': 'Report Document',
    'xml_schema_location': schema
}

if country is not None:
    if len(country) == 2:
        search_args['country'] = context.localities_iso_dict(country)['uri']
    else:
        search_args['country'] = country

for item in container.Catalog(search_args):
    obj = item.getObject()
    if obj.get_accept_time() is not None:
        accepttime = obj.get_accept_time().HTML4()
    else:
        accepttime = ''
    res = {'url': obj.absolute_url(0),
           'title': obj.title,
           'country': obj.country,
           'country_name': obj.getCountryName(),
           'country_code': obj.getCountryCode(),
           'locality': obj.locality,
           'isreleased': obj.released,
           'released': obj.reportingdate.HTML4(),
           'startyear': obj.year,
           'endyear': obj.endyear,
           'partofyear': obj.partofyear,
           'uploaded': obj.upload_time().HTML4(),
           'accepted': accepttime,
           }

    reslist.append(res)

req = context.REQUEST
if req['CONTENT_TYPE'] == 'text/xml' and req['REQUEST_METHOD'] == 'POST':
    return reslist
else:
    req.RESPONSE.setHeader('content-type', 'text/xml; charset=UTF-8')
    print "<results>"
    for d in reslist:
        print print_as_elm(d)
    print "</results>"
    return printed
