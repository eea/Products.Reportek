# -*- coding: utf-8 -*-
"""Import legacy eCas export into the new Reportek CAS PAS plugin.

Expected workflow:

1. In the final Python-2/Zope-2/4 environment, export the old plugin and remove
   it from the ZODB::

      bin/instance run parts/instance/import/export_ecas.py \
          --output parts/instance/import/ecas_export.json --remove-old

2. Copy ``ecas_export.json`` into the Zope5 container, e.g. ``/opt/zope/src``.

3. In Zope5 debug/run mode::

      from Products.Reportek.updates import import_ecas_plugin
      import_ecas_plugin.update(
          app, export_path='/opt/zope/src/ecas_export.json', replace=True)
"""

import argparse
import json
import os

import transaction
from persistent.mapping import PersistentMapping

from Products.PluggableAuthService.interfaces import plugins as pas_ifaces
from Products.Reportek.config import REPORTEK_DEPLOYMENT
from Products.Reportek.constants import ECAS_ID
from Products.Reportek.ReportekCASPlugin import (
    EcasClient,
    ReportekCASPlugin,
    addReportekCASPlugin,
)

DEFAULT_EXPORT_PATHS = [
    "/opt/zope/src/ecas_export.json",
    "/opt/zope/parts/instance/import/ecas_export.json",
    "ecas_export.json",
]

DEFAULT_INTERFACES = [
    "IExtractionPlugin",
    "IAuthenticationPlugin",
    "IChallengePlugin",
    "ICredentialsResetPlugin",
]


def _interface_map():
    names = DEFAULT_INTERFACES + ["ICredentialsUpdatePlugin"]
    return dict(
        (name, getattr(pas_ifaces, name)) for name in names if hasattr(pas_ifaces, name)
    )


def _find_export_path(export_path=None):
    if export_path:
        return export_path
    env_path = os.environ.get("ECAS_EXPORT_PATH")
    if env_path:
        return env_path
    for path in DEFAULT_EXPORT_PATHS:
        if os.path.exists(path):
            return path
    raise RuntimeError(
        "No eCas export file found. Pass export_path=... or set ECAS_EXPORT_PATH."
    )


def _deactivate_all(acl_users, plugin_id):
    registry = acl_users._getOb("plugins")
    for iface in _interface_map().values():
        try:
            registry.deactivatePlugin(iface, plugin_id)
        except Exception:
            pass


def _activate(acl_users, plugin_id, interface_names):
    registry = acl_users._getOb("plugins")
    iface_map = _interface_map()
    for name in interface_names or DEFAULT_INTERFACES:
        iface = iface_map.get(name)
        if iface is None:
            print("Skipping unsupported PAS interface: %s" % name)
            continue
        active_ids = [pid for pid, plugin in registry.listPlugins(iface)]
        if plugin_id not in active_ids:
            registry.activatePlugin(iface, plugin_id)
            print("Activated %s for %s" % (name, plugin_id))


def _set_plugin_properties(plugin, properties, export_data=None):
    skip = set(["id", "title"])
    legacy_class = (export_data or {}).get("class", "")
    for key, value in sorted((properties or {}).items()):
        if key in skip:
            continue
        if key == "SAMLValidate":
            # Old option from anz.casclient; not used by ReportekCASPlugin.
            continue
        try:
            if hasattr(plugin, "hasProperty") and plugin.hasProperty(key):
                plugin._updateProperty(key, value)
            elif hasattr(plugin, key):
                setattr(plugin, key, value)
        except Exception as exc:
            print("Could not restore eCas property %s: %s" % (key, exc))

    if "anz.ecasclient" in legacy_class:
        try:
            if hasattr(plugin, "hasProperty") and plugin.hasProperty(
                "serviceValidationEndpoint"
            ):
                plugin._updateProperty("serviceValidationEndpoint", "laxValidate")
            else:
                setattr(plugin, "serviceValidationEndpoint", "laxValidate")
        except Exception as exc:
            print("Could not set eCas serviceValidationEndpoint: %s" % exc)


def _restore_mapping(plugin, export_data):
    plugin._ecas_id = PersistentMapping()

    for row in export_data.get("ecas_mapping", []):
        ecas_id = row.get("ecas_id")
        if not ecas_id:
            continue
        username = row.get("username")
        email = row.get("email")
        seed = username or email or ecas_id
        entry = EcasClient(ecas_id, seed)
        entry._username = username
        entry._email = email
        plugin._ecas_id[ecas_id] = entry

    # Older DBs may only have username -> ecas_id. Merge without clobbering
    # richer entries restored above.
    for row in export_data.get("legacy_user2ecas_id", []):
        username = row.get("username")
        ecas_id = row.get("ecas_id")
        if not username or not ecas_id:
            continue
        entry = plugin._ecas_id.get(ecas_id)
        if entry is None:
            entry = EcasClient(ecas_id, username)
            plugin._ecas_id[ecas_id] = entry
        elif not entry.username:
            entry._username = username

    print("Restored %d eCas mapping entries" % len(plugin._ecas_id))


def update(
    app,
    export_path=None,
    plugin_id=ECAS_ID,
    replace=False,
    skipMigrationCheck=False,
):
    """Create/replace /acl_users/eCas from a JSON export."""
    if REPORTEK_DEPLOYMENT not in APPLIES_TO:
        print("Skipping eCas import for deployment: %s" % REPORTEK_DEPLOYMENT)
        return False

    export_path = _find_export_path(export_path)
    with open(export_path) as fp:
        export_data = json.load(fp)

    if export_data.get("format") != "reportek-ecas-export-v1":
        raise ValueError(
            "Unsupported eCas export format: %r" % export_data.get("format")
        )

    acl_users = app.unrestrictedTraverse("/acl_users")
    plugin_id = plugin_id or export_data.get("plugin_id") or ECAS_ID

    trans = transaction.begin()
    try:
        existing = acl_users._getOb(plugin_id, None)
        if existing is not None and not isinstance(existing, ReportekCASPlugin):
            if not replace:
                raise RuntimeError(
                    "/acl_users/%s exists and is %s. Re-run with replace=True."
                    % (plugin_id, existing.__class__)
                )
            _deactivate_all(acl_users, plugin_id)
            acl_users._delObject(plugin_id)
            existing = None

        if existing is None:
            addReportekCASPlugin(
                acl_users,
                plugin_id,
                export_data.get("properties", {}).get("title") or "Reportek CAS Plugin",
            )
            plugin = acl_users._getOb(plugin_id)
            print("Created /acl_users/%s" % plugin_id)
        else:
            plugin = existing
            print("Updating existing /acl_users/%s" % plugin_id)

        _set_plugin_properties(plugin, export_data.get("properties", {}), export_data)
        _restore_mapping(plugin, export_data)
        _activate(
            acl_users,
            plugin_id,
            export_data.get("active_interfaces") or DEFAULT_INTERFACES,
        )

        trans.commit()
        print("Imported eCas export from %s" % export_path)
        return True
    except Exception:
        trans.abort()
        raise


def main(app):
    """Entry point for ``zconsole run``."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-path", default=None)
    parser.add_argument("--plugin-id", default=ECAS_ID)
    parser.add_argument("--replace", action="store_true", default=True)
    parser.add_argument("--no-replace", dest="replace", action="store_false")
    # zconsole preserves its own argv ("run zope.conf script.py ...") when it
    # execs the script, so ignore unknown zconsole arguments here.
    args, unknown = parser.parse_known_args()

    result = update(
        app,
        export_path=args.export_path,
        plugin_id=args.plugin_id,
        replace=args.replace,
    )
    print("eCas import result: %s" % result)


if __name__ == "__main__":
    main(app)  # noqa: F821 - provided by zconsole run
