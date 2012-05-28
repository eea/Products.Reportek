## Script (Python) "parselocalities"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=triples
##title=Parse ROD localities
##
def listsort(s1,s2):
    if s1['name'] > s2['name']:
        return 1
    elif s1['name'] < s2['name']:
        return -1
    else:
        return 0

#
#1. Get all the locality uris in a list
#2. For each uri get the name and iso.
res = []
#get the obligations from RDFGrabber triples
obligationspos = triples.query(object='http://rod.eionet.eu.int/schema.rdf#Locality')
for obl in obligationspos:
    odict = {}
    odict['uri'] = obl['subject']
    buf = triples.query(subject=obl['subject'])
    for j in buf:
        if j['predicate'] == 'http://www.w3.org/2000/01/rdf-schema#label':
            odict['name'] = j['object']
        if j['predicate'] == 'http://rod.eionet.eu.int/schema.rdf#loccode':
            odict['iso'] = j['object']
    res.append(odict)
res.sort(listsort)
return res
