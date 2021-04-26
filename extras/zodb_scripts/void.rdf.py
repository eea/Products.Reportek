# flake8: noqa
# Script (Python) "void.rdf"
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

RESPONSE.setHeader('content-type', 'application/rdf+xml;charset=utf-8')

print """<?xml version="1.0" encoding="utf-8" ?>
<rdf:RDF xml:lang="en"
           xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
           xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
           xmlns:owl="http://www.w3.org/2002/07/owl#"
           xmlns:dcterms="http://purl.org/dc/terms/"
           xmlns:foaf="http://xmlns.com/foaf/0.1/"
           xmlns:void="http://rdfs.org/ns/void#">

   <!-- This file is a listing of the RDF outputs provided by CDR
        See http://rdfs.org/ns/void-guide
    -->

"""
serverurl = html_quote(request.SERVER_URL)

print """<void:Linkset rdf:ID="D2O">
    <void:linkPredicate rdf:resource="http://rod.eionet.europa.eu/schema.rdf#locality"/>
    <void:linkPredicate rdf:resource="http://rod.eionet.europa.eu/schema.rdf#obligation"/>
    <void:target rdf:resource="#deliveries"/>
    <void:target rdf:resource="#obligations"/>
</void:Linkset>

<void:Dataset rdf:ID="obligations">
    <foaf:homepage rdf:resource="http://rod.eionet.europa.eu/"/>
</void:Dataset>

<void:Dataset rdf:ID="deliveries">
    <rdfs:label>Deliveries from %s</rdfs:label>
    <void:vocabulary rdf:resource="http://rod.eionet.europa.eu/schema.rdf"/>
    <void:subset rdf:resource="#D2O"/>
""" % serverurl

for item in container.Catalog(meta_type='Report Envelope', released=1):
    try:
        print """<void:dataDump rdf:resource="%s%s"/>""" % (serverurl, html_quote(item.getPath()))
    except:
        print """<!-- deleted envelope %s -->""" % item.id

print """</void:Dataset>
</rdf:RDF>"""
return printed
