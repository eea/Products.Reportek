# Script (Python) "xmlrpc_search_shapefile"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=country=None,RA_ID=None
# title=Find shapefiles (used by Hermann for WFD reporting)
##
from Products.PythonScripts.standard import html_quote


def print_as_elm(mydict):
    attrs = []
    for elm, value in mydict.items():
        attrs.append('%s="%s"' % (elm, html_quote(str(value))))
    return "  <file %s/>" % " ".join(attrs)


if RA_ID is None:
    RA_ID = 521

search_args = {
    'meta_type': 'Report Envelope',
    'dataflow_uris': 'http://rod.eionet.europa.eu/obligations/' + str(RA_ID)
}

if country is not None:
    if len(country) == 2:
        search_args['country'] = context.localities_iso_dict(string.upper(country))[
            'uri']

filelist = []

for item in container.Catalog(search_args):
    obj = item.getObject()

    for file in obj.objectValues('Report Document'):
        if (string.upper(file.id)[-3:] == 'DBF' or file.xml_schema_location[:50] == 'http://water.eionet.europa.eu/schemas/dir200060ec/'):
            #   if (file.id):

            ps = file.permission_settings()

            for p in ps:
                if (p['name'] == 'View'):
                    restricted = (not p['acquire']) + 0
                    break

            res = {
                'url': file.absolute_url(0),
                'physicalpath': file.physicalpath(),
                'id': file.id,
                'country_code': file.getCountryCode(),
                'locality': file.locality,
                'schema': file.xml_schema_location,
                'reportingdate': file.reportingdate.HTML4(),
                'unixtime': int(file.reportingdate),
                'isreleased': file.released,
                'isrestricted': restricted,
                'uploaded': file.upload_time().HTML4()
            }
            filelist.append(res)

req = context.REQUEST

if req['CONTENT_TYPE'] == 'text/xml' and req['REQUEST_METHOD'] == 'POST':
    return filelist
else:
    req.RESPONSE.setHeader('content-type', 'text/xml; charset=UTF-8')
    print "<results>"
    for d in filelist:
        print print_as_elm(d)
    print "</results>"
    return printed
