## Script (Python) "create_organisation_folder"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
# Python script at /api/create_organisation_folder
request = container.REQUEST
country_code = request.form['country_code']
obligation_folder_name = request.form['obligation_folder_name']
account_uid = request.form['account_uid']
organisation_name = request.form['organisation_name']

root = container.restrictedTraverse('/')
obligation = dict(root.objectItems()).get(obligation_folder_name)
if obligation is None:
    return '{"success": false, "error": "obligation folder missing"}'

country = dict(obligation.objectItems()).get(country_code)
if country is None:
    return '{"success": false, "error": "country folder missing"}'

folder = dict(country.objectItems()).get(account_uid)
if folder is None:
    country.manage_addCollection(
        dataflow_uris=obligation.dataflow_uris,  # list of URIs
        country=country.country,  # URI
        id=account_uid,
        title=organisation_name,
        allow_collections=0, allow_envelopes=1,
        descr='', locality='',
        partofyear='', year='', endyear='')
    folder = dict(country.objectItems()).get(account_uid)
    folder.manage_setLocalRoles(account_uid, ['Owner'])
    created = 'true'

else:
    created = 'false'

path = '/'.join(folder.getPhysicalPath())
return '{"success": true, "created": %s, "path": "%s"}' % (created, path)
