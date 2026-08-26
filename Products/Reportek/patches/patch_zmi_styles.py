"""Patches for zmi.styles.

Zope 5.9 restricted ``++resource++zmi`` to the ``View management screens``
permission. The ZMI emits those asset URLs relative to the virtual host root,
so a user who only holds that permission further down the tree gets HTTP 200
for ``manage_main`` and HTTP 401 for every stylesheet and script it pulls in --
which makes the browser re-issue the Basic Auth challenge in a loop.

Upstream addressed one half of this in Zope 1195/1196 by prepending the path of
the *user folder* the principal was found in, turning the URLs into
``/subfolder/++resource++zmi/...``. That only helps when the user is defined
below the root. It does nothing for a user authenticated against the root
``acl_users`` -- as all Reportek LDAP users are -- who holds ``Manager`` merely
as a *local* role on some collection: ``aq_parent(user_folder)`` is the
application root, so there is nothing to prepend and the URLs stay root
relative.

This patch keeps the upstream behaviour and adds a fallback: when the user
folder yields no path, prepend the path of the object whose ZMI is being
rendered. ``++resource++zmi`` is reachable there through acquisition, and the
permission is then checked in a context where the local role applies.

Note this grants no access that did not already exist -- requesting
``/some/collection/++resource++zmi/zmi_base.css`` by hand already succeeds for
such a user. It only stops the ZMI emitting a URL its own user cannot fetch,
and it deliberately does *not* make the resources public, so anonymous callers
keep getting 401 as Zope 5.9 intended.
"""

import itertools
import logging

from AccessControl.SecurityManagement import getSecurityManager
from Acquisition import aq_inner, aq_parent

logger = logging.getLogger("Reportek")


def _strip_virtual_root(physical_path, virtual_root):
    """Drop the virtual host root prefix from a physical path.

    Mirrors the comparison upstream performs inline, so that both the user
    folder path and our fallback context path are treated identically.
    """
    stripped = []
    for part, vroot_part in itertools.zip_longest(physical_path, virtual_root):
        if part == vroot_part:
            continue
        stripped.append(part)
    return stripped


def patched_prepend_authentication_path(context, path):
    """Prepend a path in which the user may actually read ``++resource++zmi``.

    Preserves the upstream behaviour of using the user folder's path, and
    falls back to the current object's path when that is empty.
    """
    request = getattr(context, "REQUEST", None)
    if request is None:
        return path
    user_folder = aq_parent(getSecurityManager().getUser())
    if user_folder is None:
        return path

    virtual_root = request.get("VirtualRootPhysicalPath") or ()

    # Upstream: the path of the user folder the principal was found in.
    authentication_path = _strip_virtual_root(
        aq_parent(user_folder).getPhysicalPath(), virtual_root
    )

    if not [part for part in authentication_path if part]:
        # The principal lives in the root acl_users, so there is no user
        # folder path to prepend. Use the object being managed instead: a
        # local role granting "View management screens" there is enough to
        # read the resources through acquisition.
        try:
            context_path = aq_inner(context).getPhysicalPath()
        except (AttributeError, TypeError):
            logger.debug(
                "zmi.styles: no physical path for %r, leaving %s untouched",
                context,
                path,
            )
            return path
        authentication_path = _strip_virtual_root(context_path, virtual_root)

    parts = [
        part
        for part in itertools.chain(authentication_path, path.split("/"))
        if part
    ]

    return request.physicalPathToURL(parts, relative=True)
