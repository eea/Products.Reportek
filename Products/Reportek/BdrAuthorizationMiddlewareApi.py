
import requests

import logging
logger = logging.getLogger("Reportek")

class AuthMiddlewareApi(object):
    DOMAIN_TO_OBLIGATION_FOLDER = {
        'FGAS': 'fgases',
    }
    # TODO: obtain those dynamically rather than hardcode them here
    DOMAIN_TO_OBLIGATION = {
        'FGAS': 'http://rod.eionet.europa.eu/obligations/713',
    }
    TIMEOUT = 20
    def __init__(self, url):
        self.baseUrl = url

    def getCollectionPaths(self, username):
        url = self.baseUrl + '/user/'  + username + '/companies'
        # use a short timeout here to not keep the user waiting at auth time
        response = requests.get(url, timeout=self.TIMEOUT)
        if response.status_code == 404:
            return []
        if response.status_code != requests.codes.ok:
            return None
        companies = response.json()
        paths = []
        for c in companies:
            try:
                path = self.buildCollectionPath(c['domain'], c['country'],
                                    str(c['company_id']), c['collection_id'])
                if not path:
                    raise ValueError("Cannot form path with company data: %s" % str(c))
                paths.append(path)
            except Exception as e:
                logger.warning("Error in company data received from SatelliteRegistry: %s" % repr(e))

        return paths

    def getCompanies(self):
        response = requests.get(self.baseUrl + "/undertaking/list",
                                timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
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
        if response.status_code == requests.codes.ok:
            return True
        return False

    def getCandidates(self):
        response = requests.get(self.baseUrl + "/candidate/list",
                                timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getCompanyDetailsById(self, companyId):
        response = requests.get(self.baseUrl + "/undertaking/{0}/details".format(companyId),
                                timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getCompanyDetailsByVat(self, companyVat):
        response = requests.get(self.baseUrl + "/undertaking/list_by_vat/{0}".format(companyVat),
                                timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getMatchingLog(self):
        response = requests.get(self.baseUrl + "/matching_log",
                                timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getDataSyncLog(self):
        response = requests.get(self.baseUrl + "/data_sync_log",
                                timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def unverifyCompany(self, companyId, userId):
        response = requests.post(self.baseUrl + "/candidate/unverify/{0}/".format(companyId),
                                 data={'user': userId}, timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getCompaniesExcelExport(self):
        response = requests.get(self.baseUrl + "/misc/undertaking/export",
                                timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
            return None
        return response

    def getUsersExcelExport(self):
        response = requests.get(self.baseUrl + "/misc/user/export",
                                timeout=self.TIMEOUT, verify=False)
        if response.status_code != requests.codes.ok:
            return None
        return response

    @classmethod
    def buildCollectionPath(cls, domain, country_code, company_id, old_collection_id=None):
        obligation_folder = cls.DOMAIN_TO_OBLIGATION_FOLDER.get(domain)
        if not obligation_folder:
            return None
        country_folder = country_code.lower()
        collection_folder = old_collection_id if old_collection_id else company_id
        return '/'.join([obligation_folder, country_folder, collection_folder])
