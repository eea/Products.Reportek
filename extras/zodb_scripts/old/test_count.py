## Script (Python) "test_count"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
request = container.REQUEST
RESPONSE =  request.RESPONSE

def bytetostring(value):
    bytes = float(value)
    if bytes >= 1000:
        bytes = bytes/1024
        typ = 'KB'
        if bytes >= 1000:
            bytes = bytes/1024
            typ = 'MB'
        strg = '%4.2f' % bytes
        strg = strg[:4]
        if strg[3]=='.': strg = strg[:3]
    else:
        typ = 'Bytes'
        strg = '%4.0f' % bytes
    strg = strg+ ' ' + typ
    return strg

eeams = ['at', 'be', 'bg', 'cy', 'cz', 'dk', 'ee', 'fi', 'fr', 'de', 'gr', 'hu', 'is', 'ie', 'it', 'lv', 'li', 'lt', 'lu', 'mt', 'nl', 'no', 'pl', 'pt', 'ro', 'sk', 'si', 'es', 'se', 'ch', 'tr', 'gb']

for k in container.objectValues('Report Collection'):
  l_count = 0
  l_countsize = 0
  if k.id in eeams:
    #print '%s ========================================' % k.title
    eu_ob = getattr(k, 'eu')
    art17_ob = None

    for l in eu_ob.objectValues('Report Collection'):
        if l.id == 'art17':
            art17_ob = l

    if art17_ob != None:
        for m in art17_ob.objectValues('Report Envelope'):
          for doc in m.objectValues('Report Document'):
            if doc.xml_schema_location == 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd':
              l_count += 1
              l_countsize += doc.get_size()
              #print ('%s :: %s' ) % (doc.id, doc.absolute_url())
  print '%s :: %s' % (k.title, l_count)
  print 'Total size: %s' % bytetostring(l_countsize)
  print '-------------'

return printed
