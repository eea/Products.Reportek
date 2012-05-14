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
# Agency (EEA).  Portions created by Finsiel are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Contributor(s):
# Miruna Badescu, Finsiel Romania


""" Toolz module
    Contains functions useful for many classes
"""
from DateTime import DateTime
import RepUtils

class Toolz:
    """ Useful functions """

    def __valideIssueProperty(self, param):
        """Check if exists a property with given value"""
        return param in ['actor', 'country', 'bobobase_modification_time', 'reportingdate']

    def __validParams(self, sortby, how):
        """Validate sort parameters"""
        res = 1
        if (how != 'asc' and how != 'desc'):
            res = 0
        else:
            if (self.__valideIssueProperty(sortby)):
                res = 1
            else:
                res = 0
        return res

    #security.declareProtected('View', 'SearchSortWorkitems')
    def SearchSortWorkitems(self, sortby, how):
        """Returns a sorted list with workitem objects"""
        l_workitems = self.getWorkitemsForWorklist()
        if self.__validParams(sortby, how):
            if how == 'asc':
                how = 0
            else:
                how = 1
            if sortby == 'bobobase_modification_time':
                l_workitems = RepUtils.utSortByMethod(l_workitems, sortby, DateTime(), how)
            else:
                l_workitems = RepUtils.utSortByAttr(l_workitems, sortby, how)
        return l_workitems

    #LDAP users info
    def getLDAPUser(self, uid):
        res = self.getParentNode().acl_users.findUser(search_param='uid', search_term=uid)
        if len(res)>0:
            return res[0]
        return {}

    def getLDAPUserFirstName(self, dn):
        return unicode(dn.get('sn', ''), 'iso-8859-1').encode('utf-8')

    def getLDAPUserLastName(self, dn):
        return unicode(dn.get('givenName', ''), 'iso-8859-1').encode('utf-8')

    def getLDAPUserCanonicalName(self, cn):
        return unicode(cn.get('cn', ''), 'iso-8859-1').encode('utf-8')

    def getLDAPUserEmail(self, dn):
        return unicode(dn.get('mail', ''), 'iso-8859-1').encode('utf-8')