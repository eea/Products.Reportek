
import requests

import logging
logger = logging.getLogger("Reportek")

import Acquisition

class AuthMiddlewareApi(Acquisition.Implicit):
    DOMAIN_TO_OBLIGATION_FOLDER = {
        'FGAS': 'fgases',
    }
    # TODO: obtain those dynamically rather than hardcode them here
    DOMAIN_TO_OBLIGATION = {
        'FGAS': 'http://rod.eionet.europa.eu/obligations/713',
    }
    COUNTRY_TO_FOLDER = {
        'uk': 'gb',
        'el': 'gr'
    }
    TIMEOUT = 20
    def __init__(self, url):
        self.baseUrl = url

    def getCollectionPaths(self, username):
        url = self.baseUrl + '/user/' + username + '/companies'
        # use a short timeout here to not keep the user waiting at auth time
        try:
            response = requests.get(url, timeout=self.TIMEOUT)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return []
        if response.status_code in (404, 400):
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

    def getCompaniesAjax(self):
        try:
            response = requests.get(self.baseUrl + "/undertaking/list-small",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getCompanies(self):
        try:
            response = requests.get(self.baseUrl + "/undertaking/list",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def existsCompany(self, params):
        try:
            response = requests.get(self.baseUrl + "/undertaking/filter/",
                                timeout=self.TIMEOUT, verify=False,
                                params=params)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def verifyCandidate(self, companyId, candidateId, userId):
        # use the right pattern for Api url
        api_url = "/candidate/verify-none/{0}/"
        if candidateId:
            api_url = "/candidate/verify/{0}/{1}/"

        api_url = api_url.format(companyId, candidateId)
        try:
            response = requests.post(self.baseUrl + api_url,
                                 data={'user': userId},
                                 timeout=self.TIMEOUT,
                                 verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return False
        if response.status_code == requests.codes.ok:
            data = response.json()
            if 'verified' in data and data['verified']:
                return True
        return False

    def getCandidates(self):
        try:
            response = requests.get(self.baseUrl + "/candidate/list",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getUsers(self):
        try:
            response = requests.get(self.baseUrl + "/user/list",
                                    timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getCompanyDetailsById(self, companyId):
        try:
            response = requests.get(self.baseUrl + "/undertaking/{0}/details".format(companyId),
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None

        details = response.json()

        keysToVerify = ['domain', 'address', 'company_id', 'collection_id']
        if reduce(lambda i, x: i and x in details, keysToVerify, True):
            path = self.buildCollectionPath(
                details['domain'],
                details['country_code'],
                str(details['company_id']),
                details['collection_id']
            )
            details['path'] = '/' + path

        return details

    def getMatchingLog(self):
        try:
            response = requests.get(self.baseUrl + "/matching_log",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getDataSyncLog(self):
        try:
            response = requests.get(self.baseUrl + "/data_sync_log",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def unverifyCompany(self, companyId, userId):
        co = self.getCompanyDetailsById(companyId)
        try:
            response = requests.post(self.baseUrl + "/candidate/unverify/{0}/".format(companyId),
                                 data={'user': userId}, timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        unverifyResponse = response.json()
        if not unverifyResponse:
            return None
        # unverify succeeded; proceed with unLock an email alerts
        path = self._unlockCompany(str(companyId), co['oldcompany_account'],
                                   co['country_code'], co['domain'], userId)
        email_sending_failed = False
        try:
            response = requests.post(self.baseUrl + '/misc/alert_lockdown/unmatch',
                                     data={'company_id': companyId,
                                           'user': userId,
                                           'oldcompany_id': co['oldcompany_id'],
                                           'oldcollection_path': path},
                                     timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            email_sending_failed = True
        if response.status_code != requests.codes.ok or not response.json():
            email_sending_failed = True
        if email_sending_failed:
            logger.warning("Lockdown notification emails of %s not sent" % path)

        return unverifyResponse


    def getCompaniesExcelExport(self):
        try:
            response = requests.get(self.baseUrl + "/misc/undertaking/export",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response

    def getUsersExcelExport(self):
        try:
            response = requests.get(self.baseUrl + "/misc/user/export",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response

    def getSettings(self):
        try:
            response = requests.get(self.baseUrl + "/misc/settings",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def getAllEmails(self):
        try:
            response = requests.get(self.baseUrl + "/misc/mail/list",
                                timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return None
        return response.json()

    def addEmail(self, first_name, last_name, email):
        try:
            response = requests.post(self.baseUrl + "/misc/mail/add",
                                     data={
                                         'mail': email,
                                         'first_name': first_name,
                                         'last_name': last_name
                                     },
                                     timeout=self.TIMEOUT,
                                     verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None

        if response.status_code != requests.codes.ok:
            return False
        return response.json()

    def delEmail(self, email):
        try:
            response = requests.post(self.baseUrl + "/misc/mail/delete",
                                     data={'mail': email},
                                     timeout=self.TIMEOUT,
                                     verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            return False
        return response.json()

    def lockDownCompany(self, company_id, old_collection_id, country_code, domain, user):
        path = self.buildCollectionPath(domain, country_code, str(company_id), old_collection_id)
        bdrAuth = self.aq_parent
        bdrAuth.lockDownCollection(path, user)
        email_sending_failed = False
        try:
            response = requests.post(self.baseUrl + '/misc/alert_lockdown/wrong_match',
                                     data={'company_id': company_id,
                                           'user': user},
                                     timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            email_sending_failed = True
        if response.status_code != requests.codes.ok or not response.json():
            email_sending_failed = True
        if email_sending_failed:
            logger.warning("Lockdown notification emails of %s not sent" % path)


    def _unlockCompany(self, company_id, old_collection_id, country_code, domain, user):
        path = self.buildCollectionPath(domain, country_code, str(company_id), old_collection_id)
        bdrAuth = self.aq_parent
        bdrAuth.unlockCollection(path, user)
        return path

    def unlockCompany(self, company_id, old_collection_id, country_code, domain, user):
        path = self._unlockCompany(company_id, old_collection_id, country_code, domain, user)

        email_sending_failed = False
        try:
            response = requests.post(self.baseUrl + '/misc/alert_lockdown/wrong_lockdown',
                                     data={'company_id': company_id,
                                           'user': user},
                                     timeout=self.TIMEOUT, verify=False)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            email_sending_failed = True
        if response.status_code != requests.codes.ok or not response.json():
            email_sending_failed = True
        if email_sending_failed:
            logger.warning("Lockdown notification emails of %s not sent" % path)


    def lockedCompany(self, company_id, old_collection_id, country_code, domain):
        path = self.buildCollectionPath(domain, country_code, str(company_id), old_collection_id)
        bdrAuth = self.aq_parent
        return bdrAuth.lockedCollection(path)

    @classmethod
    def getCountryFolder(cls, country_code):
        country_code = country_code.lower()
        return cls.COUNTRY_TO_FOLDER.get(country_code, country_code)

    @classmethod
    def buildCollectionPath(cls, domain, country_code, company_id, old_collection_id=None):
        obligation_folder = cls.DOMAIN_TO_OBLIGATION_FOLDER.get(domain)
        if not obligation_folder:
            return None
        country_folder = cls.getCountryFolder(country_code)
        collection_folder = old_collection_id if old_collection_id else company_id
        return '/'.join([obligation_folder, country_folder, collection_folder])
