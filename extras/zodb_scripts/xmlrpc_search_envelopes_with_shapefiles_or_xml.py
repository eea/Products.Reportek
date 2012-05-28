from Products.PythonScripts.standard import html_quote

def print_as_elm(mydict):
    attrs=[]
    for elm,value in mydict.items():
        attrs.append('%s="%s"' % (elm,html_quote(str(value))))
    return "  <envelope %s/>" % " ".join(attrs)

if RA_ID is None:
    RA_ID = 521

search_args = {
    'meta_type':'Report Envelope',
    'released':1,
    'dataflow_uris':'http://rod.eionet.eu.int/obligations/' + str(RA_ID)
}

if country is not None:
    if len(country) == 2:
        search_args['country'] = context.localities_iso_dict(string.upper(country))['uri']

envlist = []

for item in container.Catalog(search_args):
    obj = item.getObject()

    for file in obj.objectValues('Report Document'):
        if (string.upper(file.id)[-3:] == 'SHP' or file.xml_schema_location[:50] == 'http://water.eionet.europa.eu/schemas/dir200060ec/'):

            res = {
                'id': obj.id,
                'url': obj.absolute_url(0),
                'country_code': obj.getCountryCode(),
                'locality': obj.locality,
                'reportingdate': obj.reportingdate.HTML4(),
                'isreleased': obj.released
            }

            envlist.append(res)

            break

req = context.REQUEST

if req['CONTENT_TYPE'] == 'text/xml' and req['REQUEST_METHOD'] == 'POST':
    return envlist
else:
    req.RESPONSE.setHeader('content-type','text/xml; charset=UTF-8')
    print "<results>"
    for d in envlist:
         print print_as_elm(d)
    print "</results>"
    return printed
