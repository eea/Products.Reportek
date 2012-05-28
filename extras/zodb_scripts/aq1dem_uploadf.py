## Script (Python) "aq1dem_uploadf"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=country, title, year, file
##title=Upload a regular file
##
request = container.REQUEST
actor = request.AUTHENTICATED_USER.getUserName()
# Look up the right URI for country iso-code
c_uri = None
for c in container.localities_table():
    if c['iso'] == country:
        c_uri = c['uri']
        break
if c_uri is None:
   raise RuntimeError, "Country not found"
for item in container.Catalog({'meta_type':'Report Collection',
   'dataflow_uris':'http://rod.eionet.eu.int/obligations/131',
   'country': c_uri}):
    collection = item.getObject()
    break
# NOT FINISHED
descr=""
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
chosen.manage_addProduct['Reportek'].manage_addDocument('myfile','Zip file of obscure origin', file,'application/x-zip')
chosen.completeWorkitem('0', actor=actor)
#chosen.release_envelope()
return chosen.absolute_url()
