# Script (Python) "envelopes.rdf"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=Extract all envelopes in RDF format for one year back
##
from Products.PythonScripts.standard import html_quote
request = container.REQUEST
RESPONSE = request.RESPONSE

print """<?xml version="1.0" encoding="utf-8" ?>
<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
  xmlns:rod="http://rod.eionet.europa.eu/schema.rdf#">"""

RESPONSE.setHeader('content-type', 'application/rdf+xml;charset=utf-8')

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

        print """  <dc:date>%s</dc:date>""" % ob.reportingdate.HTML4()
        print """  <dc:identifier>%s</dc:identifier>""" % html_quote(ob.absolute_url())
        if ob.country:
            print """  <rod:locality rdf:resource="%s" />""" % ob.country

        for year in ob.years():
            print """  <dc:coverage>%s</dc:coverage>""" % year

        for flow in ob.dataflow_uris:
            print """  <rod:obligation rdf:resource="%s" />""" % html_quote(flow)

        print """ </rod:Delivery>"""

    except:
        print """<!-- deleted envelope %s -->""" % item.id


print """</rdf:RDF>"""
return printed
