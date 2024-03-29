from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from DateTime import DateTime
from Products.Reportek.RepUtils import xmlEncode
from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.config import REPORTEK_DEPLOYMENT
from Products.Reportek.interfaces import IBaseDelivery
from Products.Reportek.RepUtils import parse_uri
from zope.interface import implements


class BaseDelivery(object):
    """BaseDelivery class."""
    implements(IBaseDelivery)

    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()

    def __init__(self, title=None, year=None, endyear=None, partofyear=None,
                 country=None, locality=None, descr=None, dataflow_uris=None):
        """ Envelope constructor
        """
        self.year = year
        self.endyear = endyear
        self._check_year_range()
        self.title = title
        self.partofyear = partofyear
        self.country = country
        self.locality = locality
        self.descr = descr
        if not dataflow_uris:
            dataflow_uris = []
        self.dataflow_uris = dataflow_uris

    def getStartDate(self):
        """ returns the start date in DateTime format
            Returns None if there is no start date
        """
        if self.year:
            l_year = str(self.year)
            if self.partofyear in ['', 'WHOLE_YEAR', 'FIRST_HALF',
                                   'FIRST_QUARTER', 'JANUARY']:
                return DateTime(l_year + '/01/01')
            elif self.partofyear == 'FEBRUARY':
                return DateTime(l_year + '/02/01')
            elif self.partofyear == 'MARCH':
                return DateTime(l_year + '/03/01')
            elif self.partofyear in ['APRIL', 'SECOND_QUARTER']:
                return DateTime(l_year + '/04/01')
            elif self.partofyear == 'MAY':
                return DateTime(l_year + '/05/01')
            elif self.partofyear == 'JUNE':
                return DateTime(l_year + '/06/01')
            elif self.partofyear in ['JULY', 'THIRD_QUARTER', 'SECOND_HALF']:
                return DateTime(l_year + '/07/01')
            elif self.partofyear == 'AUGUST':
                return DateTime(l_year + '/08/01')
            elif self.partofyear == 'SEPTEMBER':
                return DateTime(l_year + '/09/01')
            elif self.partofyear in ['OCTOBER', 'FOURTH_QUARTER']:
                return DateTime(l_year + '/10/01')
            elif self.partofyear == 'NOVEMBER':
                return DateTime(l_year + '/11/01')
            elif self.partofyear == 'DECEMBER':
                return DateTime(l_year + '/12/01')
        return None

    def getEndDate(self):
        endmonths = {
            '': '12-31',
            'WHOLE_YEAR': '12/31',
            'FIRST_HALF': '06/30',
            'SECOND_HALF': '12/31',
            'FIRST_QUARTER': '03/31',
            'SECOND_QUARTER': '06/30',
            'THIRD_QUARTER': '09/30',
            'FOURTH_QUARTER': '12/31',
            'JANUARY': '01/31',
            'FEBRUARY': '02/28',  # Fix leap year?
            'MARCH': '03/31',
            'APRIL': '04/30',
            'MAY': '05/31',
            'JUNE': '06/30',
            'JULY': '07/31',
            'AUGUST': '08/31',
            'SEPTEMBER': '09/30',
            'OCTOBER': '10/31',
            'NOVEMBER': '11/30',
            'DECEMBER': '12/31'
        }
        if self.endyear != '':
            try:
                if self.endyear >= self.year:
                    return DateTime(str(self.endyear) + '/12/31')
            except Exception:
                pass
        if self.year != '':
            startDT = self.getStartDate()  # returns DateTime
            return DateTime(
                startDT.strftime('%Y/') + endmonths.get(
                    self.partofyear, '12/31'))
        return None

    # Constructs periodical coverage from start/end dates
    def getPeriod(self):
        startDT = self.getStartDate()
        if startDT:
            startDate = startDT.strftime('%Y-%m-%d')
        else:
            return str(self.endyear)
        if self.endyear != '':
            try:
                if self.endyear > self.year:
                    return startDate + '/P' + str(
                        self.endyear - self.year + 1) + 'Y'
                if self.endyear == self.year:
                    return startDate
            except Exception:
                pass
        if self.partofyear in ['', 'WHOLE_YEAR']:
            return startDate + '/P1Y'
        if self.partofyear in ['FIRST_HALF', 'SECOND_HALF']:
            return startDate + '/P6M'
        if self.partofyear in ['FIRST_QUARTER', 'SECOND_QUARTER',
                               'THIRD_QUARTER', 'FOURTH_QUARTER']:
            return startDate + '/P3M'
        if self.partofyear in ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL',
                               'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER',
                               'OCTOBER', 'NOVEMBER', 'DECEMBER']:
            return startDate + '/P1M'
        return startDate

    def _check_year_range(self):
        """ Swap years if start bigger than end """
        if isinstance(self.year, int) and isinstance(self.endyear, int):
            try:
                if self.year > self.endyear:
                    y = self.year
                    self.year = self.endyear
                    self.endyear = y
            except Exception:
                pass

    security.declarePublic('years')

    def years(self):
        """ Return the range of years the object pertains to
        """
        if self.year == '':
            return ''
        if self.endyear == '':
            return [self.year]
        if int(self.year) > int(self.endyear):
            return range(int(self.endyear), int(self.year) + 1)
        else:
            return range(int(self.year), int(self.endyear) + 1)

    security.declareProtected('View', 'getObligations')

    def getObligations(self):
        lookup = self.ReportekEngine.dataflow_lookup
        return [(lookup(obl)['TITLE'], obl) for obl in self.dataflow_uris]

    security.declareProtected('View', 'get_export_data')

    def get_export_data(self, format='xls'):
        """ Return data for export
        """
        env_data = {}
        if getSecurityManager().checkPermission('View', self):
            if format == 'xls':
                accepted = True
                for fileObj in self.objectValues('Report Feedback'):
                    no_delivery_msgs = ("Data delivery was not acceptable",
                                        "Non-acceptance of F-gas report")
                    if fileObj.title in no_delivery_msgs:
                        accepted = False

                company_id = '-'
                company_meta = self.aq_parent.get_zope_company_meta()
                if (hasattr(self.aq_parent, 'company_id')):
                    company_id = self.aq_parent.company_id
                company = '-'
                userid = '-'
                if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                    company = (company_meta[0] if company_meta[0]
                               else self.aq_parent.title)
                    userid = (company_meta[1] if company_meta[1]
                              else self.aq_parent.id)
                obligations = [obl[0] for obl in self.getObligations()]

                env_data = {
                    'company_id': company_id,
                    'path': self.absolute_url_path(),
                    'country': self.getCountryName(),
                    'company': company.decode('utf-8'),
                    'userid': userid,
                    'title': self.title.decode('utf-8'),
                    'id': self.id,
                    'years': "{0}-{1}".format(self.year, self.endyear),
                    'end_year': self.endyear,
                    'obligation': obligations[0] if obligations else "Unknown",
                    'accepted': accepted
                }

        return env_data

    security.declareProtected('View', 'get_custom_cobjs_rdf_meta')

    def get_custom_cobjs_rdf_meta(self):
        """Return custom child objects metadata for RDF export."""
        return []

    def get_dflow_uris(self):
        return [df for df in self.dataflow_uris]

    security.declareProtected('View', 'rdf')

    def rdf(self, REQUEST):
        """Returns the delivery metadata in RDF format."""
        REQUEST.RESPONSE.setHeader('content-type',
                                   'application/rdf+xml; charset=utf-8')
        res = []
        res_a = res.append
        engine = self.getEngine()
        http_res = getattr(engine, 'exp_httpres', False)

        res_a('<?xml version="1.0" encoding="utf-8"?>')
        res_a(
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        res_a(' xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
        res_a(' xmlns:dcat="http://www.w3.org/ns/dcat#"')
        res_a(' xmlns:dct="http://purl.org/dc/terms/"')
        res_a(' xmlns:cr="http://cr.eionet.europa.eu/ontologies/contreg.rdf#"')
        res_a(' xmlns="http://rod.eionet.europa.eu/schema.rdf#">')

        res_a('<Delivery rdf:about="%s">' % xmlEncode(
            parse_uri(self.absolute_url(), http_res)))
        res_a('<rdfs:label>%s</rdfs:label>' % xmlEncode(self.title_or_id()))
        res_a('<dct:title>%s</dct:title>' % xmlEncode(self.title_or_id()))

        if self.descr:
            res_a('<dct:description>%s</dct:description>' %
                  xmlEncode(self.descr))

        if self.country:
            res.append('<locality rdf:resource="%s" />' %
                       self.country.replace('eionet.eu.int',
                                            'eionet.europa.eu'))
        if self.locality != '':
            res.append('<coverageNote>%s</coverageNote>' %
                       xmlEncode(self.locality))

        period = self.getPeriod()
        if period != '':
            res.append('<period>%s</period>' % period)

        startDT = self.getStartDate()
        if startDT:
            res.append(
                '''<startOfPeriod rdf:datatype="http://www.w3.org/2001'''
                '''/XMLSchema#date">%s</startOfPeriod>'''
                % startDT.strftime('%Y-%m-%d'))

        endDT = self.getEndDate()
        if endDT:
            res.append(
                '''<endOfPeriod rdf:datatype="http://www.w3.org/2001'''
                '''/XMLSchema#date">%s</endOfPeriod>'''
                % endDT.strftime('%Y-%m-%d'))

        for flow in self.dataflow_uris:
            res.append('<obligation rdf:resource="%s"/>' %
                       xmlEncode(flow.replace('eionet.eu.int',
                                              'eionet.europa.eu')))
        res.extend(self.get_custom_delivery_rdf_meta())
        res_a('</Delivery>')
        res.extend(self.get_custom_cobjs_rdf_meta())
        res_a('</rdf:RDF>')
        return '\n'.join(res)
