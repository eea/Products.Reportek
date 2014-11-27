
import requests

import logging
logger = logging.getLogger("Reportek")

class AuthMiddlewareApi(object):
    DOMAIN_TO_OBLIGATION_FOLDER = {
        'FGAS': 'fgases',
        'ODS': 'ods',
    }
    TIMEOUT = 20
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
                path = self.buildCollectionPath(c['domain'], c['country'],
                                    str(c['company_id']), c['collection_id'])
                paths.append(path)
            except Exception as e:
                logger.warning("Error in company data received from SatelliteRegistry: %s" % repr(e))

        return paths

    def getCompanies(self):
        response = requests.get(self.baseUrl + "/undertaking/list", timeout=self.TIMEOUT, verify=False)
        if not response or response.status_code != requests.codes.ok:
            return None
        return response.json()

    def verifyCandidate(self, companyId, candidateId, userId):
        # use the right pattern for Api url
        api_url = "/candidate/verify-none/{0}/"
        if candidateId:
            api_url = "/candidate/verify/{0}/{1}/"

        api_url = api_url.format(companyId, candidateId)
        response = requests.post(self.baseUrl + api_url,
                                 data={'user': userId},
                                 timeout=self.TIMEOUT,
                                 verify=False)
        if response and response.status_code == requests.codes.ok:
            return True
        return False

    def getCandidates(self):
        response = requests.get(self.baseUrl + "/candidate/list", timeout=self.TIMEOUT, verify=False)
        if not response or response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getCompanyDetailsById(self, companyId):
        response = requests.get(self.baseUrl + "/undertaking/{0}/details".format(companyId),
                                timeout=self.TIMEOUT, verify=False)
        if not response or response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getCompanyDetailsByVat(self, companyVat):
        response = requests.get(self.baseUrl + "/undertaking/list_by_vat/{0}".format(companyVat),
                                timeout=self.TIMEOUT, verify=False)
        if not response or response.status_code != requests.codes.ok:
            return None
        return response.json()


    @classmethod
    def buildCollectionPath(cls, domain, country_code, company_id, old_collection_id=None):
        obligation_folder = cls.DOMAIN_TO_OBLIGATION_FOLDER[domain]
        country_folder = country_code.lower()
        collection_folder = old_collection_id if old_collection_id else company_id
        return '/'.join([obligation_folder, country_folder, collection_folder])
