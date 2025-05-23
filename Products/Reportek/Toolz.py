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
# Miruna Badescu, Eau de Web


""" Toolz module
    Contains functions useful for many classes
"""
from collections import defaultdict
from DateTime import DateTime
from plone.protect.utils import addTokenToUrl
from plone.memoize import ram
from Products.PythonScripts.standard import html_quote
from Products.Reportek import constants
from Products.Reportek.vocabularies import REPORTING_PERIOD_DESCRIPTION
from time import time
import RepUtils
from string import rfind


class Toolz:
    """ Useful functions """
    reporting_year_labels = REPORTING_PERIOD_DESCRIPTION

    def __valideIssueProperty(self, param):
        """Check if exists a property with given value"""
        return param in ['actor', 'country', 'bobobase_modification_time',
                         'reportingdate']

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

    # security.declareProtected('View', 'SearchSortWorkitems')
    def SearchSortWorkitems(self, sortby, how):
        """Returns a sorted list with workitem objects"""
        l_workitems = self.getWorkitemsForWorklist()
        if self.__validParams(sortby, how):
            if how == 'asc':
                how = 0
            else:
                how = 1
            if sortby == 'bobobase_modification_time':
                l_workitems = RepUtils.utSortByMethod(
                    l_workitems, sortby, DateTime(), how)
            else:
                l_workitems = RepUtils.utSortByAttr(l_workitems, sortby, how)
        return l_workitems

    # LDAP users info
    def getLDAPUser(self, uid):
        ldap_user_folder = self.getPhysicalRoot(
        ).acl_users['ldapmultiplugin']['acl_users']
        res = ldap_user_folder.findUser(search_param='uid',
                                        search_term=uid,
                                        exact_match=True)
        if len(res) > 0:
            return res[0]

        return {}

    def getLDAPUserFirstName(self, dn):
        return dn.get('sn', '')

    def getLDAPUserLastName(self, dn):
        return dn.get('givenName', '')

    def getLDAPUserCanonicalName(self, cn):
        return cn.get('cn', '')

    def getLDAPUserEmail(self, dn):
        return dn.get('mail', '')

    @ram.cache(lambda *args: time() // (60*60*12))
    def getLDAPGroups(self):
        """ Return a list of LDAP group ids
        """
        ldap_user_folder = self.getPhysicalRoot(
        ).acl_users['ldapmultiplugin']['acl_users']
        groups = ldap_user_folder.getGroups()
        group_ids = [group[0] for group in groups if group[0]]

        return group_ids

    # collection related - must be globals to be able
    # to call them in any context (ROOT or collection)
    def dataflow_table_grouped(self, key='SOURCE_TITLE', desc=0):
        # ROOT method dataflow_table returns a list of dictionaries
        # with the following keys: 'terminated', 'PK_RA_ID', 'SOURCE_TITLE',
        # 'details_url', 'TITLE', 'uri', 'LAST_UPDATE', 'PK_SOURCE_ID'
        # we want to group items by given key, ascendent(desc=0) or
        # descendent(desc=1)
        r = defaultdict(list)
        for item in RepUtils.utSortListByAttr(
                getattr(self, constants.ENGINE_ID).dataflow_table(),
                key, desc):
            r[item[key]].append(item)
        # unfortunetely, Zope framework seems not to handle just any
        # Python code (like defaultdict), so ulglify this a little
        return sorted(r.keys(), reverse=desc), dict(r)

    def partofyear_table(self):
        ordered_keys = [
            "WHOLE_YEAR",
            "FIRST_HALF",
            "SECOND_HALF",
            "FIRST_QUARTER",
            "SECOND_QUARTER",
            "THIRD_QUARTER",
            "FOURTH_QUARTER",
            "JANUARY",
            "FEBRUARY",
            "MARCH",
            "APRIL",
            "MAY",
            "JUNE",
            "JULY",
            "AUGUST",
            "SEPTEMBER",
            "OCTOBER",
            "NOVEMBER",
            "DECEMBER",
            ""
        ]
        return ordered_keys

    def tlzNewlineToBr(self, s):
        # converts the new lines to br tags and encodes the content
        t = html_quote(s)
        if t.find('\r') >= 0:
            t = ''.join(t.split('\r'))
        if t.find('\n') >= 0:
            t = '<br />'.join(t.split('\n'))
        return t

    def tlzNewlineToBrEx(self, s):
        # converts the new lines to br tags and without encoding the content
        t = s
        if t.find('\r') >= 0:
            t = ''.join(t.split('\r'))
        if t.find('\n') >= 0:
            t = '<br />'.join(t.split('\n'))
        return t

    def tlzSortByAttr(self, p_obj_list, p_attr, p_sort_order=0):
        return RepUtils.utSortObjsListByMethod2(p_obj_list,
                                                p_attr,
                                                p_sort_order)

    def tlzSortObjsListByMethod(self, p_obj_list, p_attr, p_sort_order=0):
        return RepUtils.utSortObjsListByMethod2(p_obj_list,
                                                p_attr,
                                                p_sort_order)

    def truncate(self, text):
        if len(text) <= 80:
            return text
        return '%s ...' % text[:77]

    def cook_file_id(self, file_id):
        """ cleans up a file id to make it suitable for a Zope id or a
            file system id
        """
        if file_id:
            file_id = file_id[max(
                rfind(file_id, '/'),
                rfind(file_id, '\\'),
                rfind(file_id, ':')) + 1:]
        return RepUtils.cleanup_id(file_id.strip())

    def get_key_url(self, url):
        """Returns url with csrf authorization key"""
        req = self.REQUEST
        if not url.startswith(req.SERVER_URL) and '://' not in url[:10]:
            furl = '{}/{}'.format(self.absolute_url(), url)
            furl = addTokenToUrl(furl, req)
            return furl.split('{}/'.format(self.absolute_url()))[-1]
        return addTokenToUrl(url)

    def merge_dicts_recursive(self, dict1, dict2):
        """
        Recursively merge dict2 into dict1.
        If a key exists in both and both values are dicts, merge those dicts.
        If a key exists in both but values aren't both dicts, dict2's value
        overwrites dict1's.
        """
        result = dict(dict1)  # Create a copy of dict1
        for k, v in dict2.iteritems():
            # If both values are dicts, merge them recursively
            if (
                k in result
                and isinstance(result[k], dict)
                and isinstance(v, dict)
            ):
                result[k] = self.merge_dicts_recursive(result[k], v)
            # Otherwise just overwrite with value from dict2
            else:
                result[k] = v
        return result
