# Script (Python) "xmlrpc_search_envelopes_events"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=obligation='http://rod.eionet.europa.eu/obligations/37', released=1, releasedafter='2000-01-01'
# title=Find envelopes for merging
##
reslist = []

for item in container.Catalog({'meta_type': 'Report Envelope',
                               'dataflow_uris': obligation,
                               'released': released,
                               'reportingdate': {'query': DateTime(releasedafter), 'range': 'min'}
                               }):
    obj = item.getObject()
    res = {'url': obj.absolute_url(0),
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
    events = []
    for file in obj.objectValues('Workitem'):
        for event in file.event_log:
            events.append(
                (event['time'].ISO(), event['event'], event['comment']))
    events.sort()
    res['events'] = events

    reslist.append(res)
return reslist
