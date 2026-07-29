# -*- coding: utf-8 -*-
"""Fix migrated eCas login identifier for legacy BDR authorization.

Run from an already migrated Zope 5 BDR deployment, for example::

    /opt/zope/bin/zconsole run /opt/zope/etc/zope.conf
    >>> from Products.Reportek.updates import u20260729_fix_ecas_login_identifier
    >>> u20260729_fix_ecas_login_identifier.update(app)

The migration is intentionally small: it updates ``/acl_users/eCas`` so PAS
continues authenticating users with the legacy EU Login moniker identity, while
``getEcasUserId()`` still exposes the stable ECAS id for the registry API.

It also deactivates stale legacy ``eionetCas`` PAS registrations. After the
Zope 5 migration those objects may still be listed as active for extraction or
authentication even though they no longer implement the PAS interfaces, causing
``Active plugin eionetCas no longer implements ...`` on each request.
"""

import logging

import transaction

from Products.PluggableAuthService.interfaces import plugins as pas_ifaces
from Products.Reportek.config import DEPLOYMENT_BDR, REPORTEK_DEPLOYMENT
from Products.Reportek.constants import ECAS_ID
from Products.Reportek.ReportekCASPlugin import ReportekCASPlugin
from Products.Reportek.updates import MigrationBase

logger = logging.getLogger(__name__)

VERSION = 24
APPLIES_TO = [DEPLOYMENT_BDR]
LEGACY_LOGIN_IDENTIFIER = "moniker"
STALE_ECAS_PLUGIN_IDS = ("eionetCas",)
STALE_ECAS_PLUGIN_INTERFACES = (
    "IExtractionPlugin",
    "IAuthenticationPlugin",
    "IChallengePlugin",
    "ICredentialsResetPlugin",
    "ICredentialsUpdatePlugin",
)


def log_msg(msg, level="INFO"):
    lvl = {
        "CRITICAL": 50,
        "ERROR": 40,
        "WARNING": 30,
        "INFO": 20,
        "DEBUG": 10,
        "NOTSET": 0,
    }
    logger.log(lvl.get(level), msg)
    print(msg)


def deactivate_stale_ecas_plugins(acl_users):
    registry = acl_users._getOb("plugins")
    changed = []
    for plugin_id in STALE_ECAS_PLUGIN_IDS:
        if plugin_id == ECAS_ID:
            continue
        for iface_name in STALE_ECAS_PLUGIN_INTERFACES:
            iface = getattr(pas_ifaces, iface_name, None)
            if iface is None:
                continue
            active_ids = registry.listPluginIds(iface)
            if plugin_id not in active_ids:
                continue
            registry.deactivatePlugin(iface, plugin_id)
            changed.append((plugin_id, iface_name))
    for plugin_id, iface_name in changed:
        log_msg("Deactivated stale %s for %s" % (plugin_id, iface_name))
    return changed


def fix_ecas_login_identifier(app):
    """Set migrated ReportekCASPlugin loginIdentifier to legacy moniker."""
    if REPORTEK_DEPLOYMENT not in APPLIES_TO:
        log_msg(
            "Skipping eCas loginIdentifier fix for deployment: %s"
            % REPORTEK_DEPLOYMENT
        )
        return False

    acl_users = app.unrestrictedTraverse("/acl_users", None)
    if acl_users is None:
        log_msg("Skipping eCas loginIdentifier fix: /acl_users not found", "WARNING")
        return False

    deactivate_stale_ecas_plugins(acl_users)

    plugin = acl_users._getOb(ECAS_ID, None)
    if plugin is None:
        log_msg(
            "Skipping eCas loginIdentifier fix: /acl_users/%s not found" % ECAS_ID,
            "WARNING",
        )
        return False

    if not isinstance(plugin, ReportekCASPlugin):
        log_msg(
            "Skipping eCas loginIdentifier fix: /acl_users/%s is %s"
            % (ECAS_ID, plugin.__class__.__name__),
            "WARNING",
        )
        return False

    current = getattr(plugin, "loginIdentifier", None)

    if hasattr(plugin, "hasProperty") and plugin.hasProperty("loginIdentifier"):
        plugin._updateProperty("loginIdentifier", LEGACY_LOGIN_IDENTIFIER)
    else:
        setattr(plugin, "loginIdentifier", LEGACY_LOGIN_IDENTIFIER)

    transaction.commit()
    log_msg(
        "Updated /acl_users/%s loginIdentifier from %r to %r"
        % (ECAS_ID, current, LEGACY_LOGIN_IDENTIFIER)
    )
    return True


@MigrationBase.checkMigration(__name__)
def update(app, skipMigrationCheck=False):
    return fix_ecas_login_identifier(app)
