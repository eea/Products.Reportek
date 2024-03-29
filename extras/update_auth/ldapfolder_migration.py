# flake8: noqa
##############################################################################
#
# Copyright (c) 2000-2009 Jens Vagelpohl and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" LDAPUserFolder GenericSetup support

$Id$

Mihnea Simian (Eau De Web):

    This is a modified version of exportimport from LDAPUserFolder 2.13
    that can work with 2.9

"""

import logging

from Acquisition import aq_base
from BTrees.OOBTree import OOBTree
# from Products.GenericSetup.interfaces import ISetupEnviron
from Products.GenericSetup.utils import (XMLAdapterBase, exportObjects,
                                         importObjects)
from Products.LDAPUserFolder.LDAPUserFolder import LDAPUserFolder
from ZPublisher.HTTPRequest import default_encoding

PROPERTIES = ('title', '_login_attr', '_uid_attr', 'users_base', 'users_scope',
              '_roles', 'groups_base', 'groups_scope', '_binduid', '_bindpwd',
              '_binduid_usage', '_rdnattr', '_user_objclasses',
              '_local_groups', '_implicit_mapping', '_pwd_encryption',
              'read_only', '_extra_user_filter', '_anonymous_timeout',
              '_authenticated_timeout'
              )


class LDAPUserFolderXMLAdapter(XMLAdapterBase):
    """ XML im/exporter for LDAPUserFolder instances
    """

    # adapts(ILDAPUserFolder, ISetupEnviron)

    _LOGGER_ID = name = 'ldapuserfolder'
    _encoding = default_encoding

    def _exportNode(self):
        """Export the object as a DOM node.
        """
        node = self._getObjectNode('object')
        node.appendChild(self._extractSettings())
        node.appendChild(self._extractAdditionalGroups())
        node.appendChild(self._extractGroupMap())
        node.appendChild(self._extractGroupsStore())
        node.appendChild(self._extractServers())
        node.appendChild(self._extractLDAPSchema())

        self._logger.info('LDAPUserFolder at %s exported.' % (
            self.context.absolute_url_path()))
        return node

    def _importNode(self, node):
        """Import the object from the DOM node.
        """
        if self.environ.shouldPurge():
            self._purgeSettings()

        self._initSettings(node)
        self._initAdditionalGroups(node)
        self._initGroupMap(node)
        self._initGroupsStore(node)
        self._initServers(node)
        self._initLDAPSchema(node)

        self._logger.info('LDAPUserFolder at %s imported.' % (
            self.context.absolute_url_path()))

    node = property(_exportNode, _importNode)

    def _purgeSettings(self):
        """ Purge all settings before applying them
        """
        self.context._clearCaches()
        self.context.__init__()

    def _extractSettings(self):
        """ Read settings from the LDAPUserFolder instance
        """
        fragment = self._doc.createDocumentFragment()
        for prop_name in PROPERTIES:
            node = self._doc.createElement('property')
            node.setAttribute('name', prop_name)
            prop_value = self.context.getProperty(prop_name)

            if isinstance(prop_value, (list, tuple)):
                for value in prop_value:
                    if isinstance(value, str):
                        value = value.decode(self._encoding)
                    child = self._doc.createElement('element')
                    child.setAttribute('value', value)
                    node.appendChild(child)
            else:
                if isinstance(prop_value, str):
                    prop_value = prop_value.decode(self._encoding)
                elif not isinstance(prop_value, basestring):
                    prop_value = unicode(prop_value)
                child = self._doc.createTextNode(prop_value)
                node.appendChild(child)
            fragment.appendChild(node)

        return fragment

    def _extractAdditionalGroups(self):
        """ Extract additional locally-defined groups
        """
        fragment = self._doc.createDocumentFragment()
        local_groups = self.context._additional_groups

        if local_groups:
            node = self._doc.createElement('additional-groups')
            for group in local_groups:
                child = self._doc.createElement('element')
                child.setAttribute('value', group)
                node.appendChild(child)
            fragment.appendChild(node)

        return fragment

    def _extractGroupMap(self):
        """ Extract LDAP group to Zope role mapping
        """
        fragment = self._doc.createDocumentFragment()
        group_map = self.context.getGroupMappings()

        if group_map:
            node = self._doc.createElement('group-map')
            for ldap_group, zope_role in group_map:
                child = self._doc.createElement('mapped-group')
                child.setAttribute('ldap_group', ldap_group)
                child.setAttribute('zope_role', zope_role)
                node.appendChild(child)
            fragment.appendChild(node)

        return fragment

    def _extractGroupsStore(self):
        """ Extract localy stored group memberships
        """
        fragment = self._doc.createDocumentFragment()
        stored_groups = self.context._groups_store.items()

        if stored_groups:
            node = self._doc.createElement('group-users')
            for user_dn, role_dns in stored_groups:
                child = self._doc.createElement('user')
                child.setAttribute('dn', user_dn)
                for role_dn in role_dns:
                    grandchild = self._doc.createElement('element')
                    grandchild.setAttribute('value', role_dn)
                    child.appendChild(grandchild)
                node.appendChild(child)
            fragment.appendChild(node)

        return fragment

    def _extractServers(self):
        """ Extract LDAP server information
        """
        fragment = self._doc.createDocumentFragment()
        servers = self.context.getServers()

        if servers:
            node = self._doc.createElement('ldap-servers')
            for server_info in self.context.getServers():
                child = self._doc.createElement('ldap-server')
                for key, value in server_info.items():
                    if isinstance(value, (int, bool)):
                        value = unicode(value)
                    child.setAttribute(key, value)
                node.appendChild(child)
            fragment.appendChild(node)

        return fragment

    def _extractLDAPSchema(self):
        """ Extract LDAP schema information
        """
        fragment = self._doc.createDocumentFragment()
        node = self._doc.createElement('ldap-schema')
        schema_config = self.context.getSchemaConfig()
        for schema_info in schema_config.values():
            child = self._doc.createElement('schema-item')
            for key, value in schema_info.items():
                if isinstance(value, (int, bool)):
                    value = unicode(value)
                child.setAttribute(key, value)
            node.appendChild(child)
        fragment.appendChild(node)

        return fragment

    def _initSettings(self, node):
        """ Apply settings from the export to a LDAPUserFolder instance
        """
        # property
        for child in node.childNodes:
            if child.nodeName != 'property':
                continue

            multivalues = [x for x in child.childNodes if
                           x.nodeType == child.ELEMENT_NODE]

            if multivalues:
                value = self._readSequenceValue(multivalues)
            else:
                value = self._getNodeText(child).encode(self._encoding)
                if value.lower() in ('true', 'yes'):
                    value = True
                elif value.lower() in ('false', 'no'):
                    value = False
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        pass
            self.context._setProperty(child.getAttribute('name'), value)

    def _readSequenceValue(self, nodes):
        """ Extract a sequence value (list or tuple)
        """
        values = []

        for node in nodes:
            if node.nodeName != 'element':
                continue
            values.append(node.getAttribute('value').encode(self._encoding))

        return values

    def _initAdditionalGroups(self, node):
        """ Initialize locally defined group data
        """
        # additional-groups/element/value
        for child in node.childNodes:
            if child.nodeName != 'additional-groups':
                continue

        value_nodes = [x for x in child.childNodes if
                       x.nodeType == child.ELEMENT_NODE]
        self.context._additional_groups = self._readSequenceValue(value_nodes)

    def _initGroupMap(self, node):
        """ Initialize LDAP group to Zope role mapping
        """
        # group-map/mapped-group/ldap_group/zope_role
        group_map = {}

        for child in node.childNodes:
            if child.nodeName != 'group-map':
                continue

            for grandchild in child.childNodes:
                if grandchild.nodeName != 'mapped-group':
                    continue

                key = grandchild.getAttribute('ldap_group')
                value = grandchild.getAttribute('zope_role')
                group_map[key.encode(self._encoding)] = value.encode(
                    self._encoding)

        self.context._groups_mappings = group_map

    def _initGroupsStore(self, node):
        """ Initialize locally stored user/group map
        """
        groups_store = OOBTree()

        # group-users/user/dn/element
        for child in node.childNodes:
            if child.nodeName != 'group-users':
                continue

            for grandchild in child.childNodes:
                if grandchild.nodeName != 'user':
                    continue

                user_dn = grandchild.getAttribute('dn').encode(self._encoding)
                values = [x for x in grandchild.childNodes if
                          x.nodeType == child.ELEMENT_NODE]
                role_dns = self._readSequenceValue(values)
                groups_store[user_dn] = role_dns

        self.context._groups_store = groups_store

    def _initServers(self, node):
        """ Initialize LDAP server configurations
        """
        # server / host / port / protocol / conn_timeout / op_timeout
        for child in node.childNodes:
            if child.nodeName != 'ldap-servers':
                continue

            if child.getAttribute('purge').lower() == 'true':
                server_count = len(self.context.getServers())
                self.context.manage_deleteServers(range(0, server_count))

            for grandchild in child.childNodes:
                if grandchild.nodeName != 'ldap-server':
                    continue

                if grandchild.getAttribute('protocol').lower() == u'ldaps':
                    use_ssl = 1
                elif grandchild.getAttribute('protocol').lower() == u'ldapi':
                    use_ssl = 2
                else:
                    use_ssl = 0
                port = grandchild.getAttribute('port')
                if port:
                    port = int(port)
                self.context.manage_addServer(
                    grandchild.getAttribute('host').encode(self._encoding),
                    port=port, use_ssl=use_ssl,
                    conn_timeout=int(grandchild.getAttribute('conn_timeout')
                                     or 5),
                    op_timeout=int(grandchild.getAttribute('op_timeout') or 5)
                )

    def _initLDAPSchema(self, node):
        """ Initialize LDAP schema information
        """
        # ldap-schema/schema-item/friendly_name/ldap_name/multivalued/binary/public_name
        for child in node.childNodes:
            if child.nodeName != 'ldap-schema':
                continue

            if child.getAttribute('purge').lower() == 'true':
                self.context._ldapschema = {}

            for grandchild in child.childNodes:
                if grandchild.nodeName != 'schema-item':
                    continue

                def get(n): return grandchild.getAttribute(
                    n).encode(self._encoding)

                ldap_name = get('ldap_name')
                item = self.context._ldapschema.setdefault(ldap_name, {})

                item['binary'] = get('binary').lower() in ('true', 'yes')
                item['friendly_name'] = get('friendly_name')
                item['multivalued'] = get(
                    'multivalued').lower() in ('true', 'yes')
                item['public_name'] = get('public_name')
                item['ldap_name'] = ldap_name


def importLDAPUserFolder(context):
    """ Import LDAPUserFolder settings from an XML file

    When using this step directly, the user folder is expected to reside
    at the same level in the object hierarchy where the setup tool is.
    """
    def readDataFile(filename):
        f = open(filename, 'r')
        body = f.read()
        return body
    container = context  # .getSite()
    context = ContextWrapper(context)
    uf = getattr(aq_base(container), 'acl_users', None)

    if uf is not None and isinstance(uf, LDAPUserFolder):
        importObjectsNoZCA(uf, '%s/' % CLIENT_HOME, context)  # noqa: F821
    else:
        context.getLogger('ldapuserfolder').debug('Nothing to import.')


def exportLDAPUserFolder(context):
    """ Export LDAPUserFolder settings to an XML file
    """
    def writeDataFile(filename, body, mimetype):
        f = open(filename, 'w')
        f.write(body)
        f.close()
    container = context  # .getSite()
    context = ContextWrapper(context)
    uf = getattr(aq_base(container), 'acl_users', None)

    if uf is not None and isinstance(uf, LDAPUserFolder):
        exportObjectsNoZCA(uf, "%s/" % CLIENT_HOME, context)  # noqa: F821
    else:
        context.getLogger('ldapuserfolder').debug('Nothing to export.')

# LDAPUserFolder has some expectations from context


class ContextWrapper(object):

    def __init__(self, app):
        self.app = app
    #
    # def __getitem__(self, name):
    #    return self.app.__getitem__(name)

    def __getattr__(self, name):
        if name == 'app':
            return self.__dict__['app']
        return self.app.__getattr__(name)

    def __setattr__(self, name, value):
        if name == 'app':
            self.__dict__.update({'app': value})
        return self.app.__setattr__(name, value)

    def getLogger(self, *args, **kw):
        return logging.getLogger(*args, **kw)

    def writeDataFile(self, filename, body, mimetype):
        f = open(filename, 'w')
        f.write(body)
        f.close()

    def readDataFile(self, filename):
        f = open(filename, 'r')
        body = f.read()
        return body

    def shouldPurge(self):
        return False

# Taken away from Products.GenericSetup.utils:


def exportObjectsNoZCA(obj, parent_path, context):
    """
    Taken away from Products.GenericSetup.utils. This version of LDAPUserFolder
    does not define an interface, so I can't register and query for
    export adapter.

    """
    exporter = LDAPUserFolderXMLAdapter(obj, context)
    path = '%s%s' % (parent_path, obj.getId().replace(' ', '_'))
    if exporter:
        if exporter.name:
            path = '%s%s' % (parent_path, exporter.name)
        filename = '%s%s' % (path, exporter.suffix)
        body = exporter.body
        if body is not None:
            context.writeDataFile(filename, body, exporter.mime_type)

    if getattr(obj, 'objectValues', False):
        for sub in obj.objectValues():
            exportObjects(sub, path+'/', context)


def importObjectsNoZCA(obj, parent_path, context):
    """
    Taken away from Products.GenericSetup.utils. This version of LDAPUserFolder
    does not define an interface, so I can't register and query for
    import adapter.

    """
    importer = LDAPUserFolderXMLAdapter(obj, context)
    path = '%s%s' % (parent_path, obj.getId().replace(' ', '_'))
    __traceback_info__ = path
    if importer:
        if importer.name:
            path = '%s%s' % (parent_path, importer.name)
        filename = '%s%s' % (path, importer.suffix)
        body = context.readDataFile(filename)
        if body is not None:
            importer.filename = filename  # for error reporting
            importer.body = body

    if getattr(obj, 'objectValues', False):
        for sub in obj.objectValues():
            importObjects(sub, path+'/', context)
