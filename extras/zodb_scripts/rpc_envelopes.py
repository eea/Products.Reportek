# Script (Python) "rpc_envelopes"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=dataflow
# title=Query catalog for a dataflow return in XML-RPC
##
# Example code:

# Import a standard function, and get the HTML request and response objects.
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE = request.RESPONSE
result = []
for inx in context.Catalog({'meta_type': 'Report Envelope',
                            'dataflow_uris': dataflow,
                            'sort_on': 'reportingdate',
                            'sort_order': 'reverse'}):
    item = inx.getObject()
    if item.title == '':
        btitle = item.getId()
    else:
        btitle = item.title
    result.append({'country': item.country, 'url': item.absolute_url(), 'title': btitle,
                   'year': item.year, 'endyear': item.endyear, 'reportingdate': item.reportingdate.HTML4()})
return result
