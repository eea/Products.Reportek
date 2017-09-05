from AccessControl import ClassSecurityInfo
from interfaces import IRegistryManagement
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Products.Reportek.constants import DF_URL_PREFIX
from plone.memoize import ram
from requests.exceptions import RequestException
from time import time
from zope.interface import implementer
import logging
import Products
import requests

logger = logging.getLogger("Reportek")

@implementer(IRegistryManagement)
class RegistryManagement(Folder):

    security = ClassSecurityInfo()

    def __init__(self, id, title):
        self.id = id
        self.title = title

    def all_meta_types(self):
        types = ['Script (Python)', 'Folder', 'Page Template']
        return [t for t in Products.meta_types if t['name'] in types]


class BaseRegistryAPI(SimpleItem):

    TIMEOUT = 20

    def __init__(self, registry_name, url, token=None):
        self.registry_name = registry_name
        self.baseUrl = url
        self.token = token

    def set_base_url(self, url, token=None):
        self.baseUrl = url
        self.token = token

    def do_api_request(self, url, method='get', data=None, cookies=None,
                       headers=None, params=None):
        api_req = requests.get
        if method == 'post':
            api_req = requests.post

        try:
            response = api_req(url, data=data, cookies=cookies, headers=headers,
                               params=params, verify=False, timeout=self.TIMEOUT)
        except Exception as e:
            logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
            return None
        if response.status_code != requests.codes.ok:
            logger.warning("Retrieved a %s status code when contacting SatelliteRegistry's url: %s " % (response.status_code, url))
            return None

        return response


class FGASRegistryAPI(BaseRegistryAPI):
    DOMAIN_TO_OBLIGATION_FOLDER = {
        'FGAS': 'fgases',
        'ODS': 'ods'
    }
    # TODO: obtain those dynamically rather than hardcode them here
    DOMAIN_TO_OBLIGATION = {
        'FGAS': DF_URL_PREFIX + '713',
        'ODS': DF_URL_PREFIX + '213',
    }
    COUNTRY_TO_FOLDER = {
        'uk': 'gb',
        'el': 'gr'
    }

    def get_registry_companies(self, domain='FGAS', detailed=False):
        page = 'list-small'
        if detailed:
            page = 'list'
        url_prefix = '/'.join([self.baseUrl, 'undertaking', domain])
        url = '/'.join([url_prefix, page])
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})

        if response:
            return response.json()

    @ram.cache(lambda *args, **kwargs: args[2] + str(time() // (60 * 60)))
    def get_company_details(self, company_id, domain='FGAS'):
        url = '/'.join([self.baseUrl, 'undertaking', domain, company_id,
                        'details'])
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def getCompanyDetailsById(self, companyId, domain='FGAS'):
        details = self.get_company_details(companyId, domain=domain)
        keysToVerify = ['domain', 'address', 'company_id', 'collection_id']
        if details:
            if reduce(lambda i, x: i and x in details, keysToVerify, True):
                path = self.buildCollectionPath(
                    details['domain'],
                    details['country_code'],
                    str(details['company_id']),
                    details['collection_id']
                )
                if path:
                    details['path'] = '/' + path

            return details

    def getCollectionPaths(self, username):
        url = self.baseUrl + '/user/' + username + '/companies'
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})
        paths = []
        if response:
            companies = response.json()
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

    def existsCompany(self, params, domain='FGAS'):
        url = '/'.join([self.baseUrl, 'undertaking', domain, 'filter/'])
        response = self.do_api_request(url,
                                       params=params,
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def verifyCandidate(self, companyId, userId, candidateId=None, domain='FGAS'):
        # use the right pattern for Api url
        verify_endpoint = '/'.join(['candidate', domain, 'verify-none',
                                    companyId])
        if candidateId:
            verify_endpoint = '/'.join(['candidate', domain, 'verify',
                                        companyId, candidateId])

        api_url = '/'.join([self.baseUrl, verify_endpoint])

        response = self.do_api_request(api_url,
                                       data={'user': userId},
                                       method="post",
                                       headers={'Authorization': self.token})
        if response:
            if response.status_code == requests.codes.ok:
                data = response.json()
                if 'verified' in data and data['verified']:
                    return True
            return False

    def getCandidates(self, domain='FGAS'):
        url = '/'.join([self.baseUrl, 'candidate', domain, 'list'])
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})

        if response:
            return response.json()

        return []

    def getUsers(self, domain='FGAS'):
        url = '/'.join([self.baseUrl, 'user', domain, 'list'])
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def getMatchingLog(self, domain='FGAS'):
        url = '/'.join([self.baseUrl, 'log', 'matching', domain])
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def getDataSyncLog(self, domain='FGAS'):
        url = self.baseUrl + '/log/sync'
        url = '/'.join([self.baseUrl, 'log', 'sync', domain])
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def unverifyCompany(self, companyId, userId, domain='FGAS'):
        co = self.get_company_details(companyId, domain)
        if co:
            url = '/'.join([self.baseUrl + 'candidate', domain,
                            'unverify/{0}/'.format(companyId)])
            data = {'user': userId}
            response = self.do_api_request(url,
                                           data=data,
                                           method="post",
                                           headers={'Authorization': self.token})
            if response:
                unverifyResponse = response.json()
                if not unverifyResponse:
                    return None
                # unverify succeeded; proceed with unLock an email alerts
                path = self._unlockCompany(str(companyId), co['oldcompany_account'],
                                           co['country_code'], co['domain'], userId)
                email_sending_failed = False
                url = self.baseUrl + '/alert_lockdown/unmatch'
                data = {
                    'company_id': companyId,
                    'user': userId,
                    'oldcollection_path': path
                }
                response = self.do_api_request(url,
                                               data=data,
                                               method="post",
                                               headers={'Authorization': self.token})
                if not response:
                    email_sending_failed = True
                if email_sending_failed:
                    logger.warning("Lockdown notification emails of %s not sent" % path)

                return unverifyResponse

    def updateCompanyStatus(self, company_id, status, domain='FGAS'):
        url = '/'.join([self.baseUrl, 'undertaking', domain,
                        company_id, 'status_update'])
        data = {'status': status}
        response = self.do_api_request(url, data=data,
                                       method="post",
                                       headers={'Authorization': self.token})

        return response

    def getCompaniesExcelExport(self, domain='FGAS'):
        url = '/'.join([self.baseUrl, 'export', 'undertaking', domain])
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})

        return response

    def getUsersExcelExport(self):
        url = self.baseUrl + '/export/user/list'
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})

        return response

    def getSettings(self):
        url = self.baseUrl + '/settings'
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def getAllEmails(self):
        url = self.baseUrl + '/mail/list'
        response = self.do_api_request(url,
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def addEmail(self, first_name, last_name, email):
        url = self.baseUrl + '/mail/add'
        data = {
            'mail': email,
            'first_name': first_name,
            'last_name': last_name
        }
        response = self.do_api_request(url, data=data, method='post',
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def delEmail(self, email):
        url = self.baseUrl + '/mail/delete'
        data = {
            'mail': email
        }
        response = self.do_api_request(url, data=data, method='post',
                                       headers={'Authorization': self.token})
        if response:
            return response.json()

    def lockDownCompany(self, company_id, old_collection_id, country_code, domain, user):
        path = self.buildCollectionPath(domain, country_code,
                                        str(company_id), old_collection_id)
        bdrAuth = self.authMiddleware
        bdrAuth.lockDownCollection(path, user)
        email_sending_failed = False
        url = '/'.join([self.baseUrl, 'alert_lockdown', 'wrong_match', domain])
        data = {
            'company_id': company_id,
            'user': user
        }
        response = self.do_api_request(url, data=data,
                                       method='post',
                                       headers={'Authorization': self.token})
        if not response:
            email_sending_failed = True
        if email_sending_failed:
            logger.warning("Lockdown notification emails of %s not sent" % path)


    def _unlockCompany(self, company_id, old_collection_id, country_code, domain, user):
        path = self.buildCollectionPath(domain, country_code, str(company_id), old_collection_id)
        bdrAuth = self.authMiddleware
        bdrAuth.unlockCollection(path, user)
        return path

    def unlockCompany(self, company_id, old_collection_id, country_code, domain, user):
        path = self._unlockCompany(company_id, old_collection_id, country_code, domain, user)

        email_sending_failed = False
        url = '/'.join([self.baseUrl, 'alert_lockdown', 'wrong_lockdown',
                        domain])
        data = {
            'company_id': company_id,
            'user': user
        }
        response = self.do_api_request(url, data=data,
                                       method='post',
                                       headers={'Authorization': self.token})
        if not response:
            email_sending_failed = True

        if email_sending_failed:
            logger.warning("Lockdown notification emails of %s not sent" % path)


    def lockedCompany(self, company_id, old_collection_id, country_code, domain):
        path = self.buildCollectionPath(domain, country_code, str(company_id), old_collection_id)
        bdrAuth = self.authMiddleware
        return bdrAuth.lockedCollection(path)

    @classmethod
    def getCountryFolder(cls, country_code):
        country_code = country_code.lower()
        return cls.COUNTRY_TO_FOLDER.get(country_code, country_code)

    @classmethod
    def buildCollectionPath(cls, domain, country_code, company_id, old_collection_id=None):
        obligation_folder = cls.DOMAIN_TO_OBLIGATION_FOLDER.get(domain)
        if not obligation_folder or not country_code:
            return None
        country_folder = cls.getCountryFolder(country_code)
        collection_folder = old_collection_id if old_collection_id else company_id
        return '/'.join([obligation_folder, country_folder, collection_folder])


class BDRRegistryAPI(BaseRegistryAPI):

    def do_login(self):
        """ Login to BDR Registry. Credentials come from
            ReportekEngine properties
        """
        url = self.baseUrl + '/accounts/login'

        client = requests.session()
        csrf = None
        try:
            csrf = client.get(url).cookies.get('csrftoken')
        except RequestException as e:
            logger.warning("Unable to retrieve csrf: %s" % str(e))

        engine = self.getEngine()

        data = {
            'username': getattr(engine, 'bdr_registry_username', ''),
            'password': getattr(engine, 'bdr_registry_password', ''),
            'csrfmiddlewaretoken': csrf,
            'next': '/'
        }
        try:
            resp = client.post(url, data=data, headers=dict(Referer=url))
        except RequestException as e:
            logger.warning("Unable to login to BDRRegistry: %s" % str(e))
            return None

        if resp:
            if resp.status_code == 200:
                # I see no other way of getting the sessionid
                cookies = resp.request.headers.get('Cookie').split(';')
                for cookie in cookies:
                    cookie = cookie.strip()
                    session = cookie.split('sessionid=')
                    if len(session) == 2:
                        sessionid = session[-1]
                        self.cookies = dict(sessionid=sessionid)
                        return self.cookies


    def do_api_request(self, url, method='get', data=None, cookies=None, headers=None, params=None):
        """ Do login to BDR Registry before api calls
        """
        if not cookies:
            cookies = self.do_login()

        return super(BDRRegistryAPI, self).do_api_request(url,
                                                          method=method,
                                                          data=data,
                                                          cookies=cookies,
                                                          headers=headers,
                                                          params=params
                                                          )

    def get_registry_companies(self):
        """ Get the list of companies from the Registry
        """
        url = self.baseUrl + '/management/companies/export/json'

        response = self.do_api_request(url)
        if response:
            return response.json()

    @ram.cache(lambda *args, **kwargs: args[2] + str(time() // (60 * 60)))
    def get_company_details(self, company_id):
        """ Get company details from Registry
        """
        url = self.baseUrl + '/management/companies/account/{0}'.format(company_id)
        response = self.do_api_request(url)

        if response:
            return response.json()
