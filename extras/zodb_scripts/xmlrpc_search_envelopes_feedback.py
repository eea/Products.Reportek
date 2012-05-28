## Script (Python) "xmlrpc_search_envelopes_feedback"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=obligation='http://rod.eionet.eu.int/obligations/37', released=1
##title=Find envelopes and get the feedback items
##
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
        'released': obj.reportingdate.HTML4(),
        'startyear': obj.year,
        'endyear': obj.endyear,
        'partofyear': obj.partofyear,
    }
    feedbacklist = []
    for file in obj.objectValues('Report Feedback'):
        feedbacklist.append((file.id, file.automatic,
            file.content_type,
            file.feedbacktext, file.document_id, file.releasedate.ISO()))
    res['feedbacks'] = feedbacklist

    reslist.append(res)
return reslist
