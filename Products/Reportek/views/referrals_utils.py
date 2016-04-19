from Acquisition import aq_base
from base_admin import BaseAdmin
from operator import itemgetter
from Products.Reportek import constants
import json
import logging
logger = logging.getLogger("Reportek")


class ReferralsUtils(BaseAdmin):
    """ Referrals Utils
    """

    def api_get_referrals_status(self):

        obligations = self.request.get('obligations', [])
        countries = self.request.get('countries', [])
        allow_referrals = bool(int(self.request.get('allow_referrals', '1')))
        explicit = bool(int(self.request.get('explicit', '0')))
        brains = self.search_catalog(obligations, countries, role='')
        results = []
        for brain in brains:
            col_obligations = []
            for uri in list(brain.dataflow_uris):
                try:
                    title = self.get_obligations_title()[uri]
                except KeyError:
                    title = 'Unknown/Deleted obligation'
                col_obligations.append({
                    'uri': uri,
                    'title': title
                })
            col_obligations.sort(key=itemgetter('title'))
            coll_data = {
                'path': brain.getPath(),
                'country': brain.getCountryName,
                'obligations': col_obligations,
                'title': brain.title,
                'rid': brain.getRID()
            }
            coll = brain.getObject()
            prop_allowed_referrals = getattr(aq_base(coll),
                                             'prop_allowed_referrals',
                                             None)
            allowed_referrals = coll.are_referrals_allowed()
            coll_data['allowed_referrals'] = allowed_referrals
            coll_data['prop_allowed_referrals'] = prop_allowed_referrals
            is_req = (
                (allow_referrals == bool(allowed_referrals)) and
                (explicit == (prop_allowed_referrals is not None))
            )
            if is_req:
                results.append(coll_data)

        results.sort(key=itemgetter('path'))

        return json.dumps({"data": results})

    def api_update_referrals_status(self):
        catalog = self.context.restrictedTraverse(constants.DEFAULT_CATALOG, None)
        updated = []
        errors = []
        if catalog:
            for rs_setting, value in self.request.form.items():
                if rs_setting.startswith('rstatus:'):
                    try:
                        rid = int(rs_setting.split('rstatus:')[-1])
                        obj = catalog.getobject(rid)
                        value = int(value)
                        if obj.are_referrals_allowed() != value:
                            obj.prop_allowed_referrals = value
                            updated.append({
                                'rid': rid,
                                'title': obj.title,
                                'url': obj.absolute_url()
                                })
                    except Exception as e:
                        logger.warning("Error changing referral status for RID: {} (Error: {})".format(rid, str(e)))
                        errors.append({
                            'rid': rid,
                            'error': str(e)
                        })

        return json.dumps({"updated": updated, "errors": errors})

