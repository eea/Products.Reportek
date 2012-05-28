reslist = []

for item in container.Catalog({'meta_type':'Report Envelope',
   'dataflow_uris':obligation, 
   'released':released}):
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
    events = []
    for file in obj.objectValues('Workitem'):
        for event in file.event_log:
            events.append((event['time'].ISO(), event['event'], event['comment']) )
    events.sort()
    res['events'] = events

    reslist.append(res)
return reslist
