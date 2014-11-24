
import requests

import logging
logger = logging.getLogger("Reportek")

class AuthMiddlewareApi(object):
    DOMAIN_TO_OBLIGATION_FOLDER = {
        'FGAS': 'fgases',
        'ODS': 'ods',
    }
    TIMEOUT = 2
    def __init__(self, url):
        self.baseUrl = url

    def getCollectionPaths(self, username):
        url = self.baseUrl + '/user/detail/' + username
        # use a short timeout here to not keep the user waiting at auth time
        response = requests.get(url, timeout=self.TIMEOUT)
        if not response or response.status_code != requests.codes.ok:
            return None
        companies = response.json()
        paths = []
        for c in companies:
            try:
                obligation_folder = self.DOMAIN_TO_OBLIGATION_FOLDER[c['domain']]
                country_folder = c['country'].lower()
                collection_folder = c['collection_id'] if c['collection_id'] else str(c['company_id'])
                path = '/'.join([obligation_folder, country_folder, collection_folder])
                paths.append(path)
            except Exception as e:
                logger.warning("Error in company data received from SatelliteRegistry: %s" % repr(e))

        return paths

    def getCompanies(self):
        response = requests.get(self.baseUrl + "/undertaking/list", timeout=self.TIMEOUT, verify=False)
        if not response or response.status_code != requests.codes.ok:
            return None
        return response.json()

    def verifyCandidate(self, newId, candidateId):
        response = requests.get(self.baseUrl + "/candidate/verify/{0}/{1}".format(newId, candidateId),
                                timeout=self.TIMEOUT, verify=False)
        if response and response.status_code == requests.codes.ok:
            return True
        else:
            return False

    def getCandidates(self):
        response = requests.get(self.baseUrl + "/candidate/list", timeout=self.TIMEOUT, verify=False)
        if not response or response.status_code != requests.codes.ok:
            return None
        return response.json()


    def getCompanyDetails(self, companyId):
        response = requests.get(self.baseUrl + "/undertaking/%s/details" % companyId,
                                timeout=self.TIMEOUT, verify=False)
        if not response or response.status_code != requests.codes.ok:
            return None
        return response.json()
