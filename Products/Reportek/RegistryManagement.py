from AccessControl import ClassSecurityInfo
from interfaces import IRegistryManagement
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from zope.interface import implementer
import eventlet
import logging
import Products
import requests

logger = logging.getLogger("Reportek")
eventlet.monkey_patch()


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

    def __init__(self, url):
        self.baseUrl = url

    def do_api_request(self, url, method='get', data=None, cookies=None, headers=None):
        api_req = requests.get
        if type == 'post':
            api_req = requests.post

        with eventlet.Timeout(self.TIMEOUT, False):
            try:
                response = api_req(url, data=data, cookies=cookies, headers=headers, verify=False)
            except eventlet.Timeout as e:
                logger.warning("Timeout while retrieving data from Registry (%s)" % str(e))
                return None
            except Exception as e:
                logger.warning("Error contacting SatelliteRegistry (%s)" % str(e))
                return None
            if response.status_code != requests.codes.ok:
                return None

            return response


class FGASRegistryAPI(BaseRegistryAPI):
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

    def get_registry_companies(self, detailed=False):
        page = 'list-small'
        if detailed:
            page = 'list'
        url_prefix = self.baseUrl + '/undertaking/'
        url = url_prefix + page
        response = self.do_api_request(url)

        if response:
            return response.json()

    def get_company_details(self, company_id):
        url = self.baseUrl + '/undertaking/{0}/details'.format(company_id)
        response = self.do_api_request(url)

        return response.json()


class BDRRegistryAPI(BaseRegistryAPI):

    def do_login(self):
        """ Login to BDR Registry. Credentials come from
            ReportekEngine properties
        """
        url = self.baseUrl + '/accounts/login'

        client = requests.session()

        csrf = client.get(url).cookies['csrftoken']
        engine = self.getEngine()

        data = {
            'username': getattr(engine, 'bdr_registry_username', ''),
            'password': getattr(engine, 'bdr_registry_password', ''),
            'csrfmiddlewaretoken': csrf,
            'next': '/'
        }
        resp = client.post(url, data=data, headers=dict(Referer=url))
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


    def do_api_request(self, url, method='get', data=None, cookies=None, headers=None):
        """ Do login to BDR Registry before api calls
        """
        if not cookies:
            cookies = self.do_login()

        return super(BDRRegistryAPI, self).do_api_request(url,
                                                          method=method,
                                                          data=data,
                                                          cookies=cookies,
                                                          headers=headers
                                                          )

    def get_registry_companies(self):
        """ Get the list of companies from the Registry
        """
        url = self.baseUrl + '/management/companies/export/json'

        response = self.do_api_request(url)
        if response:
            return response.json()

    def get_company_details(self, company_id):
        """ Get company details from Registry
        """
        url = self.baseUrl + '/management/companies/account/{0}'.format(company_id)
        response = self.do_api_request(url)

        if response:
            return response.json()
