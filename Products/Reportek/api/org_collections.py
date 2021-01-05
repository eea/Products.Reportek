import json

from Products.Five import BrowserView


class OrgCollections(BrowserView):
    """Organisation collections management view, specific for BDR Registry colls"""

    def create_organisation_folder(self):
        """Create an organisation folder"""
        self.request.RESPONSE.setHeader("Content-Type", "application/json")
        country_code = self.request.form.get('country_code')
        obligation_folder_name = self.request.form.get('obligation_folder_name')
        account_uid = self.request.form.get('account_uid')
        organisation_name = self.request.form.get('organisation_name')


        dflow_coll = self.context.unrestrictedTraverse('/{}'.format(obligation_folder_name), None)
        if not dflow_coll:
            return json.dumps({
                "success": False,
                "error": "obligation folder missing"
            })

        country = dict(dflow_coll.objectItems()).get(country_code)
        if country is None:
            return json.dumps({
                "success": False,
                "error": "country folder missing"
            })

        folder = dict(country.objectItems()).get(account_uid)
        if folder is None:
            country.manage_addCollection(
                dataflow_uris=list(dflow_coll.dataflow_uris),  # list of URIs
                country=country.country,  # URI
                id=account_uid,
                title=organisation_name,
                allow_collections=0, allow_envelopes=1,
                descr='', locality='',
                partofyear='', year='', endyear='', old_company_id=account_uid)
            folder = dict(country.objectItems()).get(account_uid)
            folder.manage_setLocalRoles(account_uid, ['Owner'])
            created = True
        else:
            created = False

        path = '/'.join(folder.getPhysicalPath())
        return json.dumps({
            "success": True,
            "created": created,
            "path": path
        })

    def update_organisation_name(self):
        """Update the title of the organisation folder"""
        self.request.RESPONSE.setHeader("Content-Type", "application/json")
        updated = False
        COUNTRY_TO_FOLDER = {
            'uk': 'gb',
            'gb': 'gb',
            'uk_gb': 'gb',
            'el': 'gr',
            'non_eu': 'non-eu'
        }
        country_code = self.request.form.get('country_code')
        country_folder = COUNTRY_TO_FOLDER.get(country_code, country_code)
        obligation_code = self.request.form.get('obligation_folder_name')
        account = self.request.form.get('account_uid')
        org_name = self.request.form.get('organisation_name')
        if not country_folder or not obligation_code or not account or not org_name:
            self.request.response.setStatus(400)
            return json.dumps({"updated": False})
        if isinstance(org_name, unicode):
            org_name = org_name.encode('utf-8')

        oldcompany_account = self.request.form.get('oldcompany_account')
        if oldcompany_account:
            account = oldcompany_account

        search_path = str('/'.join([obligation_code, country_folder, account]))
        root = self.context.restrictedTraverse('/')
        collection = root.restrictedTraverse(search_path, None)

        if collection:
            if collection.title != org_name:
                collection.manage_changeCollection(title=org_name)
                updated = True

        return json.dumps({"updated": updated})
