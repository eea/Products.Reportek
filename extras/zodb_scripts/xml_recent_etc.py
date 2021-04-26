# flake8: noqa
# Script (Python) "xml_recent_etc"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=country_code=None,RA_ID=None,released=None,releasedafter=None
# title=Find envelopes by obligation (used by Hermann)
##
from Products.PythonScripts.standard import html_quote

reslist = []


def print_as_attrs(mydict, str1, str2):
    attrs = []
    for elm, value in mydict.items():
        attrs.append('%s="%s"' % (elm, html_quote(str(value))))
    return str1 + " ".join(attrs) + str2


search_args = {'meta_type': 'Report Envelope',
               'sort_on': 'reportingdate', 'sort_order': 'reverse'}

if country_code is not None:
    if len(country_code) == 2:
        search_args['country'] = context.localities_iso_dict(
            string.upper(country_code))['uri']


if RA_ID is not None and RA_ID != '':
    dataflow_uris = []

    ra_ids = string.split(RA_ID, '|')

    for number in ra_ids:
        dataflow_uris.append(
            'http://rod.eionet.europa.eu/obligations/' + number)

    search_args['dataflow_uris'] = dataflow_uris


if released is not None:
    if released == '0' or released == '1':
        search_args['released'] = int(released)

if releasedafter is None or releasedafter == '':
    reportingdate = context.ZopeTime() - 90
    search_args['reportingdate'] = {'query': reportingdate, 'range': 'min'}
elif len(releasedafter) == 10:
    search_args['reportingdate'] = {
        'query': DateTime(releasedafter), 'range': 'min'}


for item in container.Catalog(search_args):
    obj = item.getObject()

    res = {
        'url': obj.absolute_url(0),
        'id': obj.id,
        'title': obj.title,
        'dataflow_uris': obj.dataflow_uris,
        # 'description': obj.descr,
        # 'country': obj.country,
        'country_name': obj.getCountryName(),
        'country_code': obj.getCountryCode(),
        'locality': obj.locality,
        'reportingdate': obj.reportingdate.HTML4(),
        'released': obj.released,
        'startyear': obj.year,
        'endyear': obj.endyear,
        'partofyear': obj.partofyear,
        'lastworkitem': obj.objectValues('Workitem')[-1].activity_id
    }

    filelist = []
    for file in obj.objectValues('Report Document'):
        filelist.append((file.id, file.xml_schema_location))
    res['files'] = filelist

    feedbacklist = []
    for file in obj.objectValues('Report Feedback'):
        feedbacklist.append((file.id, file.automatic, file.content_type,
                             file.document_id, file.releasedate.ISO(), file.title))
    res['feedbacks'] = feedbacklist

    """

    workitemlist = []
    for item in obj.objectValues('Workitem'):
        workitemlist.append(item.activity_id)

    res['workitems'] = workitemlist

    feedbacklist = []
    for file in obj.objectValues('Report Feedback'):
        feedbacklist.append((file.id, file.automatic,file.content_type,
            file.document_id, file.releasedate.ISO(), file.title))
    res['feedbacks'] = feedbacklist

    filelist = []
    for file in obj.objectValues('Report Document'):
        if file.get_accept_time() is not None:
            accepttime = file.get_accept_time().ISO()
        else: accepttime = '0000-00-00 00:00:00'
        filelist.append((file.id, file.content_type,
            file.xml_schema_location,
            file.title, file.upload_time().ISO(), accepttime), )
    res['files'] = filelist

    eventlist = []
    for file in obj.objectValues('Workitem'):
        for event in file.event_log:
            eventlist.append((event['time'].ISO(), event['event'], event['comment']) )
    eventlist.sort()
    res['events'] = eventlist

    """

    reslist.append(res)

req = context.REQUEST

req.RESPONSE.setHeader('content-type', 'text/xml; charset=UTF-8')

print print_as_attrs(search_args, '<results ', '>')

for d in reslist:
    print print_as_attrs(d, '  <result ', '/>')

print "</results>"

return printed
