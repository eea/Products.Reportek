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

import types
from Products.ZCatalog.CatalogAwareness import CatalogAware
from OFS.SimpleItem import SimpleItem
import Globals
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.Reportek.constants import DF_URL_PREFIX
from AccessControl import getSecurityManager, ClassSecurityInfo
import AccessControl.Role

# Product imports
import RepUtils
from CountriesManager import CountriesManager
from Products.Reportek.BaseDelivery import BaseDelivery

manage_addReferralForm = PageTemplateFile('zpt/referral/add', globals())


def manage_addReferral(self, title, descr, referral_url, year, endyear,
                       partofyear, country, locality, dataflow_uris,
                       REQUEST=None):
    """ Add a new Referral object with id *id*. """
    id = RepUtils.generate_id("ref")
    try:
        year = int(year)
    except:
        year = ''
    try:
        endyear = int(endyear)
    except:
        endyear = ''

    ob = Referral(title, descr, referral_url, year, endyear, partofyear,
                  country, locality, dataflow_uris)
    ob.id = id
    ob.released = 1
    self._setObject(id, ob)
    ob = self._getOb(id)

    if REQUEST is not None:
        # Return to containers's view
        return REQUEST.RESPONSE.redirect(self.absolute_url())


class Referral(CatalogAware, SimpleItem, CountriesManager, BaseDelivery):
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

    def __init__(self, title, descr, referral_url, year, endyear, partofyear,
                 country, locality, dataflow_uris):
        """Referral constructor."""
        BaseDelivery.__init__(self, title=title, year=year, endyear=endyear,
                              partofyear=partofyear, country=country,
                              locality=locality, descr=descr,
                              dataflow_uris=dataflow_uris)
        self.referral_url = referral_url

    def get_reportingdate(self):
        return self.bobobase_modification_time()

    reportingdate = property(get_reportingdate)

    security.declarePrivate('get_first_accept')
    def get_first_accept(self):
        """ Figures out which type of content the webbrowser prefers
            If it is 'application/rdf+xml', then send RDF
        """
        s = self.REQUEST.get_header('HTTP_ACCEPT','*/*')
        segs = s.split(',')
        firstseg = segs[0].split(';')
        return firstseg[0].strip()

    security.declareProtected('View', 'index_html')
    index_html = PageTemplateFile('zpt/referral/index', globals())

    security.declareProtected('View', 'referral_tabs')
    referral_tabs = PageTemplateFile('zpt/referral/tabs', globals())

    security.declareProtected('Change Collections', 'manage_prop')
    manage_prop = PageTemplateFile('zpt/referral/prop', globals())


    security.declareProtected('View', 'manage_main')

    def manage_main(self,*args,**kw):
        """ Define manage main to be context aware """
#       manage_main_inh = Referral.inheritedAttribute ("manage_main")

        if getSecurityManager().checkPermission('View management screens',self):
            return apply(self.manage_prop,(self,)+ args,kw)
        else:
            return apply(self.index_html,(self,)+ args, kw)

    security.declareProtected('View', 'get_custom_delivery_rdf_meta')
    def get_custom_delivery_rdf_meta(self):
        """Return custom content type metadata for RDF export."""
        res = []
        res.append('<link>%s</link>' % RepUtils.xmlEncode(self.referral_url))
        res.append('<hasFile rdf:resource="%s"/>' % RepUtils.xmlEncode(self.referral_url))

        return res

    security.declareProtected('View', 'get_export_data')
    def get_export_data(self, format='xls'):
        """ Return data for export
        """
        env_data = BaseDelivery.get_export_data(self, format=format)
        if getSecurityManager().checkPermission('View', self):
            if format == 'xls':
                env_data.update({
                    'released': self.released,
                    'reported': self.reportingdate.strftime('%Y-%m-%d'),
                    'files': []
                })

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
                            action='./manage_main')

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
