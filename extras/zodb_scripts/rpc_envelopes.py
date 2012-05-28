# Example code:

# Import a standard function, and get the HTML request and response objects.
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE
result = []
for inx in context.Catalog({'meta_type':'Report Envelope',
     'dataflow_uris':dataflow,
     'sort_on':'reportingdate',
     'sort_order':'reverse' }):
    item = inx.getObject()
    if item.title == '':
        btitle = item.getId()
    else:
        btitle = item.title
    result.append({'country':item.country, 'url':item.absolute_url(),'title':btitle,
'year':item.year,'endyear':item.endyear,'reportingdate':item.reportingdate.HTML4() })
return result
