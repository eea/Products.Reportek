## Script (Python) "envelopes.rdf"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE =  request.RESPONSE

print """<?xml version="1.0" encoding="utf-8" ?>
<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dctype="http://purl.org/dc/dcmitype/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
  xmlns:cr="http://cr.eionet.europa.eu/ontologies/contreg.rdf#"
  xmlns:rod="http://rod.eionet.europa.eu/schema.rdf#">"""

RESPONSE.setHeader('content-type', 'text/xml;charset=utf-8')
print """<rdf:Description rdf:about="">
   <rdfs:label>Deliveries from %s</rdfs:label>
</rdf:Description>""" % request.SERVER_URL
dow = context.ZopeTime().dow()
for item in container.Catalog(meta_type='Report Envelope', released=1,
                  reportingdate=context.ZopeTime() - 360 - dow, reportingdate_usage='range:min'):
  try:
    ob = item.getObject()
    print """<rod:Delivery rdf:about="%s">""" % html_quote(ob.absolute_url())
    print """  <dc:title>%s</dc:title>""" % html_quote(ob.title_or_id())
    if ob.descr:
        print """  <dc:description>%s</dc:description>""" % html_quote(ob.descr)

    print """  <rod:released>%s</rod:released>""" % ob.reportingdate.HTML4()
    print """  <dc:identifier>%s</dc:identifier>""" % html_quote(ob.absolute_url())
    if ob.country:
        print """  <rod:locality rdf:resource="%s" />""" % ob.country.replace('eionet.eu.int','eionet.europa.eu')

    for year in ob.years():
        print """  <rod:period>%s</rod:period>""" % year

    for flow in ob.dataflow_uris:
        print """  <rod:obligation rdf:resource="%s" />""" % html_quote(flow.replace('eionet.eu.int','eionet.europa.eu'))

    for fileid in ob.objectIds('Report Document'):
        print """  <rod:file rdf:resource="%s/%s"/>""" % (html_quote(ob.absolute_url()), fileid)
 
    print """ </rod:Delivery>"""
    for fileobj in ob.objectValues('Report Document'):
        print """<dctype:Dataset rdf:about="%s">""" % fileobj.absolute_url()
        if fileobj.title != '' and fileobj.title != None:
            print """<rdfs:label>%s</rdfs:label>""" % fileobj.title
        print """<dc:date>%s</dc:date>""" % fileobj.upload_time().HTML4()
        print """<cr:mediaType>%s</cr:mediaType>""" % fileobj.content_type
        if fileobj.content_type == "text/xml":
           print """<cr:xmlSchema>%s</cr:xmlSchema>""" % fileobj.xml_schema_location
        print """</dctype:Dataset>"""
  except:
    print """<!-- deleted envelope %s -->""" % item.id;



print """</rdf:RDF>"""
return printed
