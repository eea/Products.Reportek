# Script (Python) "parseobligations"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=triples
# title=Parse EIONET ROD files
##
oblmap = {
    'http://www.w3.org/2000/01/rdf-schema#label': 'TITLE',
    'http://rod.eionet.europa.eu/schema.rdf#instrument': 'source_uri',
    'http://rod.eionet.europa.eu/schema.rdf#details_url': 'details_url',
}

legmap = {
    'http://www.w3.org/2000/01/rdf-schema#label': 'SOURCE_TITLE',
}


def processdetails(subject):
    legalobj = triples.query(subject=subject)
    for j in legalobj:
        if j['predicate'] == 'http://purl.org/dc/elements/1.1/identifier':
            return j['object']
    return ''


def processlegal(subject):
    legalobj = triples.query(subject=subject)
    for j in legalobj:
        if j['predicate'] == 'http://www.w3.org/2000/01/rdf-schema#label':
            return j['object']
    return ''


#
# 1. Get all the obligation uris in a list
# 2. For each uri get the title, and instrument.
res = []
# get the obligations from RDFGrabber triples
obligationspos = triples.query(
    object='http://rod.eionet.europa.eu/schema.rdf#Obligation')
for obl in obligationspos:
    odict = {}
    odict['uri'] = obl['subject']
    odict['terminated'] = '0'
    buf = triples.query(subject=obl['subject'])
    for j in buf:
        if j['predicate'] == 'http://www.w3.org/2000/01/rdf-schema#label':
            odict['TITLE'] = j['object']
        if j['predicate'] == 'http://purl.org/dc/elements/1.1/title':
            odict['TITLE'] = j['object']
        if j['predicate'] == 'http://rod.eionet.europa.eu/schema.rdf#details_url':
            odict['details_url'] = processdetails(j['object'])
        if j['predicate'] == 'http://rod.eionet.europa.eu/schema.rdf#terminated':
            odict['terminated'] = j['object']
        if j['predicate'] == 'http://rod.eionet.europa.eu/schema.rdf#instrument':
            odict['source_uri'] = j['object']
            odict['SOURCE_TITLE'] = processlegal(j['object'])
    res.append(odict)
return res
