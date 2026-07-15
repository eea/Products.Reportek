"""
Migration script: Products.LDAPMultiPlugins -> pas.plugins.ldap

Run via:
  docker-compose exec instance /opt/zope/bin/zconsole run /opt/zope/etc/zope.conf /opt/zope/src/migrate_ldap.py

Or paste into zconsole debug session.
"""

import transaction
from odict import odict

from Products.PluggableAuthService.interfaces.plugins import IRolesPlugin

OLD_PLUGIN_ID = "ldapmultiplugin"
NEW_PLUGIN_ID = "ldap"
ROLE_PLUGIN_ID = "ldap_group_roles"


def principal_id_from_dn(dn):
    """Extract the PAS principal id from an LDAP DN.

    Old LDAPUserFolder stores `_groups_store` keys as full DNs, while the new
    pas.plugins.ldap principal id is the uid value.
    """
    first = dn.split(",", 1)[0]
    key, value = first.split("=", 1)
    if key.lower() != "uid":
        print(f"  WARNING: unexpected local group DN RDN {first!r}; using {value!r}")
    return value


def ensure_role_manager_role(role_plugin, role_id):
    """Ensure acl_users/roles knows a role before assigning it.

    Zope's global valid roles may include Reportek roles such as ClientFG, but
    ZODBRoleManager can only assign roles that are defined in its own _roles
    mapping. Create the local role definition on demand before assigning it to
    a principal.
    """
    roles_plugin = role_plugin.aq_parent.roles
    if role_id not in roles_plugin.listRoleIds():
        roles_plugin.addRole(role_id, title=role_id)
        print("  Added role %s to acl_users/roles" % role_id)


def migrate_local_groups_store(role_plugin, groups_store):
    """Migrate old LDAPUserFolder DN -> groups to direct role assignments."""
    if not groups_store:
        return 0

    valid_roles = set(role_plugin.validRoles())
    count = 0
    skipped = 0
    for dn, roles in sorted(groups_store.items()):
        principal_id = principal_id_from_dn(dn)
        for role_id in roles or []:
            if role_id not in valid_roles:
                print(
                    "  WARNING: skipping local group %r for %r; not a valid role"
                    % (role_id, principal_id)
                )
                skipped += 1
                continue
            ensure_role_manager_role(role_plugin, role_id)
            role_plugin.manage_assignRoleToPrincipal(role_id, principal_id)
            print("  Assigned local LDAP role %s to %s" % (role_id, principal_id))
            count += 1

    if skipped:
        print("  Skipped %s local LDAP assignments" % skipped)
    return count


def migrate(app):
    acl = app.acl_users
    plugins = acl.plugins

    # ---------------------------------------------------------------
    # 1. Read old plugin config
    # ---------------------------------------------------------------
    old = acl[OLD_PLUGIN_ID]
    luf = old.acl_users

    servers = luf.getServers()
    # Build LDAP URI from server list
    uris = []
    for s in servers:
        proto = s["protocol"]
        host = s["host"]
        port = s["port"]
        uris.append(f"{proto}://{host}:{port}")
    uri = " ".join(uris)

    bind_dn = luf._binduid
    bind_pwd = luf._bindpwd
    users_base = luf.users_base
    users_scope = luf.users_scope  # 2 = SUBTREE
    groups_base = luf.groups_base
    groups_scope = luf.groups_scope
    login_attr = luf._login_attr
    uid_attr = luf._uid_attr
    rdn_attr = luf._rdnattr
    obj_classes = luf._user_objclasses
    schema = luf.getSchemaDict()

    # Collect which PAS interfaces the old plugin is active for
    old_interfaces = []
    for info in plugins.listPluginTypeInfo():
        iface = info["interface"]
        actives = [pid for pid, p in plugins.listPlugins(iface)]
        if OLD_PLUGIN_ID in actives:
            old_interfaces.append((info["id"], iface))

    print(f"Old plugin URI: {uri}")
    print(f"Old plugin bind DN: {bind_dn}")
    print(f"Old plugin users base: {users_base}")
    print(f"Old plugin groups base: {groups_base}")
    print(f"Old plugin interfaces: {[i[0] for i in old_interfaces]}")

    # ---------------------------------------------------------------
    # 2. Create new pas.plugins.ldap plugin
    # ---------------------------------------------------------------
    from pas.plugins.ldap.plugin import manage_addLDAPPlugin

    if NEW_PLUGIN_ID in acl.objectIds():
        print(f"Plugin '{NEW_PLUGIN_ID}' already exists, removing first...")
        acl.manage_delObjects([NEW_PLUGIN_ID])

    manage_addLDAPPlugin(acl, NEW_PLUGIN_ID, title="LDAP Plugin")
    new_plugin = acl[NEW_PLUGIN_ID]
    print(f"Created new plugin: {NEW_PLUGIN_ID}")

    # ---------------------------------------------------------------
    # 3. Configure the new plugin
    # ---------------------------------------------------------------
    settings = new_plugin.settings

    # Server settings
    settings["server.uri"] = uri
    settings["server.user"] = bind_dn
    settings["server.password"] = bind_pwd
    settings["server.conn_timeout"] = 5
    settings["server.op_timeout"] = 10
    settings["server.start_tls"] = False
    settings["server.ignore_cert"] = False
    settings["server.page_size"] = 1000

    # Cache
    settings["cache.cache"] = True
    settings["cache.timeout"] = 300

    # Users config
    settings["users.baseDN"] = users_base
    settings["users.scope"] = users_scope

    # Build user attribute map from old schema
    users_attrmap = odict()
    users_attrmap["rdn"] = rdn_attr
    users_attrmap["id"] = uid_attr
    users_attrmap["login"] = login_attr
    for s in schema:
        ldap_name = s["ldap_name"]
        if ldap_name == "cn":
            users_attrmap["fullname"] = "cn"
        elif ldap_name == "mail":
            users_attrmap["email"] = "mail"
        elif ldap_name == "sn":
            users_attrmap["sn"] = "sn"
        elif ldap_name == uid_attr:
            pass  # already mapped
        elif ldap_name == "employeeType":
            users_attrmap["employeeType"] = "employeeType"
    # Ensure id attr is in the map for propertysheet
    if users_attrmap["id"] not in users_attrmap:
        users_attrmap[users_attrmap["id"]] = users_attrmap["id"]
    settings["users.attrmap"] = users_attrmap
    settings["users.queryFilter"] = "(&(objectClass=person)(uid=*))"
    settings["users.objectClasses"] = obj_classes
    # We have stored group membership on group entries (groupOfUniqueNames /
    # uniqueMember), not as memberOf on user entries. Keep this disabled so
    # pas.plugins.ldap resolves user groups by searching groups for the user's DN.
    settings["users.memberOfSupport"] = False
    settings["users.recursiveGroups"] = False

    # Groups config
    settings["groups.baseDN"] = groups_base
    settings["groups.scope"] = groups_scope
    groups_attrmap = odict()
    groups_attrmap["rdn"] = "cn"
    groups_attrmap["id"] = "cn"
    groups_attrmap["title"] = "description"
    settings["groups.attrmap"] = groups_attrmap
    settings["groups.queryFilter"] = "(objectClass=groupOfUniqueNames)"
    settings["groups.objectClasses"] = ["groupOfUniqueNames"]
    settings["groups.memberOfSupport"] = True

    new_plugin._p_changed = True
    print("Settings configured")

    # ---------------------------------------------------------------
    # 4. Activate new plugin for the same PAS interfaces
    # ---------------------------------------------------------------
    from Products.PluggableAuthService.interfaces.plugins import (
        IGroupEnumerationPlugin,
        IGroupsPlugin,
        IPropertiesPlugin,
    )

    for iface_id, iface in old_interfaces:
        try:
            plugins.activatePlugin(iface, NEW_PLUGIN_ID)
            print(f"  Activated {iface_id}")
        except Exception as e:
            print(f"  Failed to activate {iface_id}: {e}")

    # Also activate additional interfaces that pas.plugins.ldap supports
    extra_ifaces = [
        ("IGroupsPlugin", IGroupsPlugin),
        ("IGroupEnumerationPlugin", IGroupEnumerationPlugin),
        ("IPropertiesPlugin", IPropertiesPlugin),
    ]
    for iface_id, iface in extra_ifaces:
        try:
            plugins.activatePlugin(iface, NEW_PLUGIN_ID)
            print(f"  Activated {iface_id} (extra)")
        except Exception:
            # May already be active or not supported
            pass

    # ---------------------------------------------------------------
    # 5. Preserve old LDAP group -> Zope role mappings
    # ---------------------------------------------------------------
    from Products.Reportek.ldap_group_roles import (
        manage_addLDAPGroupRolesPlugin,
    )

    if ROLE_PLUGIN_ID in acl.objectIds():
        print(f"Plugin '{ROLE_PLUGIN_ID}' already exists, removing first...")
        acl.manage_delObjects([ROLE_PLUGIN_ID])

    manage_addLDAPGroupRolesPlugin(acl, ROLE_PLUGIN_ID)
    role_plugin = acl[ROLE_PLUGIN_ID]
    group_mappings = dict(getattr(luf, "_groups_mappings", {}) or {})
    try:
        group_mappings = dict(luf.getGroupMappings())
    except Exception:
        pass
    role_plugin.set_mappings(
        group_mappings,
        implicit_mapping=getattr(luf, "_implicit_mapping", False),
        default_roles=getattr(luf, "_roles", ()),
    )
    plugins.activatePlugin(IRolesPlugin, ROLE_PLUGIN_ID)
    print(f"Created {ROLE_PLUGIN_ID} with {len(group_mappings)} group role mappings")

    # ---------------------------------------------------------------
    # 6. Preserve old LDAPUserFolder local user -> group assignments
    # ---------------------------------------------------------------
    # LDAPUserFolder's `_local_groups` stores per-user group assignments in
    # `_groups_store` as DN -> [group ids]. In BDR those group ids are used as
    # role ids (ClientFG, ClientODS, Manager, ...). pas.plugins.ldap reads real
    # LDAP group membership from LDAP, so these local ZODB-only assignments need
    # to become direct principal role assignments in our Reportek LDAP Group
    # Roles plugin.
    local_groups_enabled = getattr(luf, "_local_groups", False)
    groups_store = dict(getattr(luf, "_groups_store", {}) or {})
    migrated_local_assignments = migrate_local_groups_store(
        role_plugin, groups_store
    )
    if local_groups_enabled:
        print(
            "Migrated %s local LDAPUserFolder _groups_store role assignments"
            % migrated_local_assignments
        )
    elif groups_store:
        print(
            "Migrated %s _groups_store role assignments even though _local_groups is false"
            % migrated_local_assignments
        )

    # ---------------------------------------------------------------
    # 7. Deactivate old plugin
    # ---------------------------------------------------------------
    for iface_id, iface in old_interfaces:
        try:
            plugins.deactivatePlugin(iface, OLD_PLUGIN_ID)
            print(f"  Deactivated old {iface_id}")
        except Exception as e:
            print(f"  Failed to deactivate old {iface_id}: {e}")

    print()
    print("Migration complete. Test login before committing!")
    print("To commit: transaction.commit()")
    print("To rollback: transaction.abort()")

    # Uncomment the next line to auto-commit:
    # transaction.commit()
    return new_plugin


if __name__ == "__main__":
    # When run via zconsole run, 'app' is available as a global
    new_plugin = migrate(app)  # noqa: F821
    # Auto-commit when run as script
    transaction.commit()
    print("Transaction committed.")
