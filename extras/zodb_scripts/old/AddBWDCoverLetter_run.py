## Script (Python) "AddBWDCoverLetter_run"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
for x in container.Catalog(meta_type='Report Envelope', dataflow_uris=['http://rod.eionet.europa.eu/obligations/531', 'http://rod.eionet.europa.eu/obligations/532']):
  obj = x.getObject()
  if obj.year == 2011:
    fbs = [y.title for y in obj.objectValues('Report Feedback') if y.title == 'Confirmation of receipt']
    if not fbs and obj.released:
      obj.AddBWDCoverLetter()
      print obj.absolute_url(1)

return printed
