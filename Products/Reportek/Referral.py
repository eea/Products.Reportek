# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is Reportek version 1.0.
#
# The Initial Developer of the Original Code is European Environment
# Agency (EEA).  Portions created by EEA are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Soren Roug, EEA


"""Referral object

Referrals are used to tell Reportnet that the delivery is located 
elsewhere. The countries often incorrectly use them to point to
another location /inside/ CDR.

Referrals are obsolete. It is better to use an Envelope with a hyperlink in it.

$Id$"""

import time, types, os, string
import Products
from Products.ZCatalog.CatalogAwareness import CatalogAware
from OFS.SimpleItem import SimpleItem
import Globals
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl import getSecurityManager, ClassSecurityInfo
import AccessControl.Role
from DateTime import DateTime

# Product imports
import RepUtils
from CountriesManager import CountriesManager

manage_addReferralForm = PageTemplateFile('zpt/referral/add', globals())


def manage_addReferral(self, title, descr, referral_url, year, endyear,
                       partofyear, country, locality, dataflow_uris,
                       REQUEST=None):
    """ Add a new Referral object with id *id*. """
    id = RepUtils.generate_id("ref")
    ob = Referral()
    ob.id = id
    ob.title = title
    ob.referral_url = referral_url
    try:
        ob.year = int(year)
    except:
        ob.year = ''
    try:
        ob.endyear = int(endyear)
    except:
        ob.endyear = ''
    ob.partofyear = partofyear
    ob.country = country
    ob.locality = locality
    ob.descr = descr
    ob.released = 1
    ob.dataflow_uris = dataflow_uris
    self._setObject(id, ob)
    ob = self._getOb(id)
    if REQUEST is not None:
        # Return to containers's view
        return REQUEST.RESPONSE.redirect(self.absolute_url())


class Referral(CatalogAware, SimpleItem, CountriesManager):
    """ Referrals are basic objects that provide a standard
        interface for object management. Referral objects also implement
        a management interface and can have arbitrary properties.
    """
    meta_type='Repository Referral'

    # Create a SecurityInfo for this class. We will use this
    # in the rest of our class definition to make security
    # assertions.
    security = ClassSecurityInfo()

    manage_options=(
        (
        {'label':'Properties', 'action':'manage_prop',
         'help':('Reportek','Referral_Properties.stx')},
        {'label':'View', 'action':'index_html',
         'help':('OFSP','Referral_View.stx')},
        )+
        AccessControl.Role.RoleManager.manage_options+
        SimpleItem.manage_options
        )

    def get_reportingdate(self):
        return self.bobobase_modification_time()

    reportingdate = property(get_reportingdate)

    def __setstate__(self,state):
        Referral.inheritedAttribute('__setstate__')(self, state)
        if type(self.year) is types.StringType and self.year != '':
            try:
                self.year = int(self.year)
            except:
                self.year = ''

        if not hasattr(self,'endyear'):
            self.endyear = ''

        if type(self.endyear) is types.StringType and self.endyear != '':
            try:
                self.endyear = int(self.endyear)
            except:
                self.endyear = ''

        # The new URI-based obligation codes. Can now be multiple
        if not hasattr(self,'dataflow_uris'):
            if self.dataflow:
                self.dataflow_uris = ( "http://rod.eionet.europa.eu/obligations/" + self.dataflow, )
            else:
                self.dataflow_uris = ( )

    security.declarePrivate('get_first_accept')
    def get_first_accept(self):
        """ Figures out which type of content the webbrowser prefers
            If it is 'application/rdf+xml', then send RDF
        """
        s = self.REQUEST.get_header('HTTP_ACCEPT','*/*')
        segs = s.split(',')
        firstseg = segs[0].split(';')
        return firstseg[0].strip()

    def getStartDate(self):
        """ returns the start date in DateTime format
            Returns None if there is no start date
        """
        if self.year:
            l_year = str(self.year)
            if self.partofyear in ['', 'Whole Year', 'First Half', 'First Quarter', 'January']:
                return DateTime(l_year + '/01/01')
            elif self.partofyear == 'February':
                return DateTime(l_year + '/02/01')
            elif self.partofyear == 'March':
                return DateTime(l_year + '/03/01')
            elif self.partofyear in ['April', 'Second Quarter']:
                return DateTime(l_year + '/04/01')
            elif self.partofyear == 'May':
                return DateTime(l_year + '/05/01')
            elif self.partofyear == 'June':
                return DateTime(l_year + '/06/01')
            elif self.partofyear in ['July', 'Third Quarter', 'Second Half']:
                return DateTime(l_year + '/07/01')
            elif self.partofyear == 'August':
                return DateTime(l_year + '/08/01')
            elif self.partofyear == 'September':
                return DateTime(l_year + '/09/01')
            elif self.partofyear in ['October', 'Fourth Quarter']:
                return DateTime(l_year + '/10/01')
            elif self.partofyear == 'November':
                return DateTime(l_year + '/11/01')
            elif self.partofyear == 'December':
                return DateTime(l_year + '/12/01')
        return None

    def getEndDate(self):
        endmonths = {
         '': '12-31',
         'Whole Year': '12/31',
         'First Half': '06/30',
         'Second Half': '12/31',
         'First Quarter': '03/31',
         'Second Quarter': '06/30',
         'Third Quarter': '09/30',
         'Fourth Quarter': '12/31',
         'January': '01/31',
         'February': '02/28', # Fix leap year?
         'March': '03/31',
         'April': '04/30',
         'May': '05/31',
         'June': '06/30',
         'July': '07/31',
         'August': '08/31',
         'September': '09/30',
         'October': '10/31',
         'November': '11/30',
         'December': '12/31'
        }
        if self.endyear != '':
            try:
                if self.endyear >= self.year:
                    return DateTime(str(self.endyear) + '/12/31')
            except:
                pass
        if self.year != '':
            startDT = self.getStartDate() # returns DateTime
            return DateTime(startDT.strftime('%Y/') + endmonths.get(self.partofyear,'12/31'))
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
                    return startDate + '/P' + str(self.endyear - self.year + 1) + 'Y'
                if self.endyear == self.year:
                    return startDate
            except:
                pass
        if self.partofyear in ['', 'Whole Year']:
            return startDate + '/P1Y'
        if self.partofyear in ['First Half', 'Second Half']:
            return startDate + '/P6M'
        if self.partofyear in ['First Quarter', 'Second Quarter', 'Third Quarter', 'Fourth Quarter']:
            return startDate + '/P3M'
        if self.partofyear in ['January', 'February', 'March', 'April', 
          'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December' ]:
            return startDate + '/P1M'
        return startDate

    security.declareProtected('View', 'index_html')
    index_html = PageTemplateFile('zpt/referral/index', globals())

    security.declareProtected('View', 'referral_tabs')
    referral_tabs = PageTemplateFile('zpt/referral/tabs', globals())

    security.declareProtected('Change Collections', 'manage_prop')
    manage_prop = PageTemplateFile('zpt/referral/prop', globals())

    security.declarePublic('years')

    def years(self):
        """ Return the range of years the object pertains to """
        if self.year == '':
            return ''
        if self.endyear == '':
            return [ self.year ]
        if int(self.year) > int(self.endyear):
            return range(int(self.endyear),int(self.year)+1)
        else:
            return range(int(self.year),int(self.endyear)+1)

    security.declareProtected('View', 'manage_main')

    def manage_main(self,*args,**kw):
        """ Define manage main to be context aware """
#       manage_main_inh = Referral.inheritedAttribute ("manage_main")

        if getSecurityManager().checkPermission('View management screens',self):
            return apply(self.manage_prop,(self,)+ args,kw)
        else:
            return apply(self.index_html,(self,)+ args, kw)

    security.declareProtected('View', 'rdf')
    def rdf(self, REQUEST):
        """ Returns the envelope metadata in RDF format
            This includes files and feedback objects
        """
        REQUEST.RESPONSE.setHeader('content-type', 'application/rdf+xml; charset=utf-8')
        res = []
        res_a = res.append  #optimisation

        res_a('<?xml version="1.0" encoding="utf-8"?>')
        res_a('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        res_a(' xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"')
        res_a(' xmlns:dct="http://purl.org/dc/terms/"')
        res_a(' xmlns:cr="http://cr.eionet.europa.eu/ontologies/contreg.rdf#"')
        res_a(' xmlns="http://rod.eionet.europa.eu/schema.rdf#">')

        res_a('<Delivery rdf:about="%s">' % RepUtils.xmlEncode(self.absolute_url()))
        res_a('<rdfs:label>%s</rdfs:label>' % RepUtils.xmlEncode(self.title_or_id()))
        res_a('<dct:title>%s</dct:title>' % RepUtils.xmlEncode(self.title_or_id()))
        if self.descr:
            res_a('<dct:description>%s</dct:description>' % RepUtils.xmlEncode(self.descr))

        if self.country:
            res_a('<locality rdf:resource="%s" />' % self.country.replace('eionet.eu.int','eionet.europa.eu'))
        if self.locality != '':
            res_a('<coverageNote>%s</coverageNote>' % RepUtils.xmlEncode(self.locality))

        period = self.getPeriod()
        if period != '':
            res_a('<period>%s</period>' % period)

        startDT = self.getStartDate()
        if startDT:
            res_a('<startOfPeriod rdf:datatype="http://www.w3.org/2001/XMLSchema#date">%s</startOfPeriod>' % startDT.strftime('%Y-%m-%d'))

        endDT = self.getEndDate()
        if endDT:
            res_a('<endOfPeriod rdf:datatype="http://www.w3.org/2001/XMLSchema#date">%s</endOfPeriod>' % endDT.strftime('%Y-%m-%d'))

        for flow in self.dataflow_uris:
            res_a('<obligation rdf:resource="%s"/>' % RepUtils.xmlEncode(flow.replace('eionet.eu.int','eionet.europa.eu')))

        res_a('<link>%s</link>' % RepUtils.xmlEncode(self.referral_url))
        res_a('<hasFile rdf:resource="%s"/>' % RepUtils.xmlEncode(self.referral_url))
        res_a('</Delivery>')
#       res_a('<File rdf:about="%s">' % RepUtils.xmlEncode(self.referral_url))
#       res_a('</File>')

        res_a('</rdf:RDF>')
        return '\n'.join(res)

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
                if (hasattr(self.aq_parent, 'company_id')):
                    company_id = self.aq_parent.company_id

                obligations = [obl[0] for obl in self.getObligations()]

                env_data = {
                    'company_id': company_id,
                    'released': self.released,
                    'path': self.absolute_url_path(),
                    'country': self.getCountryName(),
                    'company': self.aq_parent.title.decode('utf-8'),
                    'userid': self.aq_parent.id,
                    'title': self.title.decode('utf-8'),
                    'id': self.id,
                    'years': "{0}-{1}".format(self.year, self.endyear),
                    'end_year': self.endyear,
                    'reported': self.reportingdate.strftime('%Y-%m-%d'),
                    'files': [],
                    'obligation': obligations[0] if obligations else "Unknown",
                    'accepted': accepted
                }

        return env_data

    security.declareProtected('Change Collections', 'manage_editReferral')
    def manage_editReferral(self, title, descr, referral_url,
            year, endyear, partofyear, country, locality,
            dataflow_uris=[], REQUEST=None):
        """ Manage the edited values """
        self.title = title
        self.referral_url = referral_url
        try: self.year = int(year)
        except: self.year = ''
        try: self.endyear = int(endyear)
        except: self.endyear = ''
        self.partofyear = partofyear
        self.country = country
        self.locality = locality
        self.descr = descr
        self.dataflow_uris = dataflow_uris
        # update ZCatalog
        self.reindex_object()
        if REQUEST:
# Should use these two lines, but that doesn't work with non-managers
#           message="Properties changed"
#           return self.manage_prop(self,REQUEST,manage_tabs_message=message)
            return self.messageDialog(
                            message="The properties of %s have been changed!" % self.id,
                            action='')

    security.declareProtected('Change Collections', 'manage_changeReferral')

    def manage_changeReferral(self, title=None, referral_url=None,
            year=None, endyear=None, partofyear=None,
            country=None, locality=None, descr=None,
            dataflow_uris=None, REQUEST=None):
        """ Manage the edited values """
        if title is not None:
            self.title=title
        if referral_url is not None:
            self.referral_url=referral_url
        if year is not None:
            self.year=year
        if endyear is not None:
            self.endyear=endyear
        if partofyear is not None:
            self.partofyear=partofyear
        if country is not None:
            self.country=country
        if locality is not None:
            self.locality=locality
        if descr is not None:
            self.descr=descr
        if dataflow_uris is not None:
            self.dataflow_uris=dataflow_uris
        # update ZCatalog
        self.reindex_object()
        if REQUEST:
            message="Properties changed"
            return self.manage_main(self,REQUEST,manage_tabs_message=message)


Globals.InitializeClass(Referral)
