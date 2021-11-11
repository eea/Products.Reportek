# flake8: noqa
# Script (Python) "envelopes.rdf"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=Extract all envelopes in RDF format
##
from Products.PythonScripts.standard import html_quote, url_quote
request = container.REQUEST
RESPONSE = request.RESPONSE

print """<?xml version="1.0" encoding="utf-8" ?>
<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
  xmlns:rod="http://rod.eionet.europa.eu/schema.rdf#">"""

RESPONSE.setHeader('content-type', 'application/rdf+xml;charset=utf-8')

s_url = request.SERVER_URL
print """<rdf:Description rdf:about="">
   <rdfs:label>Deliveries from %s</rdfs:label>
</rdf:Description>""" % s_url
# dow = context.ZopeTime().dow()
# reportingdate=context.ZopeTime() - 360 - dow, reportingdate_usage='range:min'
for item in container.Catalog(meta_type='Report Envelope', released=1):
    try:
        print """<rod:Delivery rdf:about="%s%s"/>""" % (s_url, html_quote(url_quote(item.getPath())))
    except:
        print """<!-- deleted envelope %s -->""" % item.id

print """</rdf:RDF>"""
return printed
