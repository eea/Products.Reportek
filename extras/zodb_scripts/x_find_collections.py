## Script (Python) "x_find_collections"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Find reporters that have not released yet
##
# This script looks at all report collections. Then for each collection it loops through every envelope
# If the envelope is released after the cut-off date then the company has delivered
# Otherwise it is considered a non-delivery.
# Acceptance of delivery is NOT considered.

request = container.REQUEST
response = request.RESPONSE

cutoffDate = DateTime("2013-01-01")

response.setHeader('content-type', 'text/plain;charset=utf-8')

def quote(s):
    return s.replace('"','""')

for item in container.Catalog(meta_type='Report Collection', sort_on='id'):
  try:
    ob = item.getObject()
    if len(ob.id) > 6:
      hasReleased = 0
      for env in ob.objectValues():
        if env.reportingdate > cutoffDate and env.released == 1:
          hasReleased=1

      if not hasReleased:
          print '"%s","%s"' % (ob.id, quote(ob.title))
  except:
    print "Exception"

return printed
