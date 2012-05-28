request = container.REQUEST
response = request.RESPONSE
actor = request.AUTHENTICATED_USER.getUserName()
if actor == 'Anonymous User':
    raise RuntimeError, 'You did not login first'
container.logtheupload(container.REQUEST)
# Look up the right URI for country iso-code
c_uri = None
for c in container.localities_table():
    if c['iso'] == country:
        c_uri = c['uri']
        break
if c_uri is None:
   raise RuntimeError, "Country not found"
# finds the collection in the catalog
for item in container.Catalog({'meta_type':'Report Collection',
   'dataflow_uris':'http://rod.eionet.eu.int/obligations/131',
   'country': c_uri}):
    collection = item.getObject()
    break
# NOT FINISHED
descr="Uploaded via AQ-DEM"
endyear=""
partofyear="Whole Year"
locality=""
collection.manage_addProduct['Reportek'].manage_addEnvelope(title, descr, year,
  endyear, partofyear, locality)
# Should return the path of the new envelope
# How do we get it?
currtime = ""
for item in collection.objectValues('Report Envelope'):
    if item.bobobase_modification_time().HTML4() > currtime:
        currtime = item.bobobase_modification_time().HTML4()
        chosen = item
chosen.activateWorkitem('0', actor=actor)
chosen.manage_addzipfile(file)
chosen.completeWorkitem('0', actor=actor)
#chosen.release_envelope()
container.logtheend(chosen.absolute_url())
response.setStatus(200)
return chosen.absolute_url()
