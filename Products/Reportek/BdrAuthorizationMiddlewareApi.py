
import requests
import json

import logging
logger = logging.getLogger("Reportek")

class AuthMiddlewareApi(object):
    DOMAIN_TO_OBLIGATION_FOLDER = {
        'FGAS': 'fgases',
        'ODS': 'ods',
    }
    def __init__(self, url):
        self.baseUrl = url

    def getCollectionPaths(self, username):
        url = self.baseUrl + '/user/detail/' + username
        # use a short timeout here to not keep the user waiting at auth time
        result = requests.get(url, timeout=2)
        if not result or result.status_code != 200:
            return None
        companies = json.loads(result.text)
        paths = []
        for c in companies:
            try:
                obligation_folder = self.DOMAIN_TO_OBLIGATION_FOLDER[c['domain']]
                country_folder = c['country'].lower()
                collection_folder = c['collection_id'] if c['collection_id'] else str(c['external_id'])
                path = '/'.join([obligation_folder, country_folder, collection_folder])
                paths.append(path)
            except Exception as e:
                logger.warning("Error in company data received from SatelliteRegistry: %s" % repr(e))

        return paths
