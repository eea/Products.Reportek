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
from Products.PythonScripts.standard import url_quote, html_quote

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
        ldap_user_folder = self.getPhysicalRoot().acl_users['ldapmultiplugin']['acl_users']
        res = ldap_user_folder.findUser(search_param='uid', search_term=uid)
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

    #collection related - must be globals to be able
    #to call them in any context (ROOT or collection)
    def dataflow_table_grouped(self, key='SOURCE_TITLE', desc=0):
        #ROOT method dataflow_table returns a list of dictionaries
        #with the following keys:
        #[
        #    'terminated', 'PK_RA_ID', 'SOURCE_TITLE', 'details_url', 'TITLE',
        #    'uri', 'LAST_UPDATE', 'PK_SOURCE_ID'
        #]
        #we want to group items by given key, ascendent(desc=0) or descendent(desc=1)
        r = {}
        #group items
        rhk = r.has_key
        for item in RepUtils.utSortListByAttr(self.dataflow_table(), key, desc):
            if not rhk(item[key]): r[item[key]] = []
            r[item[key]].append(item)
        #sort keys
        keys = r.keys()
        keys.sort()
        if desc: keys.reverse()
        return keys, r

    def partofyear_table(self):
        return ['',
            'Whole Year',
            'First Half',
            'Second Half',
            'First Quarter',
            'Second Quarter',
            'Third Quarter',
            'Fourth Quarter',
            'January',
            'February',
            'March',
            'April',
            'May',
            'June',
            'July',
            'August',
            'September',
            'October',
            'November',
            'December'
        ]

    def tlzNewlineToBr(self, s):
        #converts the new lines to br tags and encodes the content
        t = html_quote(s)
        if t.find('\r') >= 0: t = ''.join(t.split('\r'))
        if t.find('\n') >= 0: t = '<br />'.join(t.split('\n'))
        return t

    def tlzNewlineToBrEx(self, s):
        #converts the new lines to br tags and without encoding the content
        t = s
        if t.find('\r') >= 0: t = ''.join(t.split('\r'))
        if t.find('\n') >= 0: t = '<br />'.join(t.split('\n'))
        return t

    def tlzSortByAttr(self, p_obj_list, p_attr, p_sort_order=0):
        return RepUtils.utSortByAttr(p_obj_list, p_attr, p_sort_order)

    def tlzSortObjsListByMethod(self, p_obj_list, p_attr, p_sort_order=0):
        return RepUtils.utSortObjsListByMethod(p_obj_list,
                                               p_attr,
                                               p_sort_order)

    #SimpleTree support - work in progress!
    def tlzGetRoot(self):
        return self.getPhysicalRoot()

    def tlzFilterTreeChildren(self, x):
        root = self.tlzGetRoot()
        if x is root:
            return root
        else:
            if x.meta_type in ['Report Collection', 'Report Envelope', 'Repository Referral']:
                return x
            else:
                return None
