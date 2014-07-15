## Script (Python) "xmlrpc_search_envelopes"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=obligation='http://rod.eionet.europa.eu/obligations/37', released=1, releasedafter='2000-01-01'
##title=Find envelopes for merging (Used by SMR for Noise DF5)
##
reslist = []

for item in container.Catalog({'meta_type': 'Report Envelope',
   'dataflow_uris': obligation, 
   'released': released,
   'reportingdate': {'query':DateTime(releasedafter), 'range':'min' }
   }):
    obj = item.getObject()
    res = { 'url': obj.absolute_url(0),
        'title': obj.title,
        'description': obj.descr,
        'dataflow_uris': obj.dataflow_uris,
        'country': obj.country,
        'country_name': obj.getCountryName(),
        'country_code': obj.getCountryCode(),
        'locality': obj.locality,
        'isreleased': obj.released,
        'released': obj.reportingdate.HTML4(),
        'startyear': obj.year,
        'endyear': obj.endyear,
        'partofyear': obj.partofyear,
    }
    filelist = []
    for file in obj.objectValues('Report Document'):
        if file.get_accept_time() is not None:
            accepttime = file.get_accept_time().HTML4()
        else: accepttime = ''
        filelist.append((file.id, file.content_type,
            file.xml_schema_location,
            file.title, file.upload_time().HTML4(), accepttime), )
    res['files'] = filelist

    reslist.append(res)
return reslist
