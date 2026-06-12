"""Helpers for accessing LDAP data through pas.plugins.ldap."""

USER_ATTRS = ("uid", "cn", "sn", "givenName", "mail", "employeeType")


def _root(context):
    if hasattr(context, "getPhysicalRoot"):
        return context.getPhysicalRoot()
    return context


def get_acl_users(context):
    root = _root(context)
    return getattr(root, "acl_users", None)


def get_ldap_plugin(context):
    acl_users = get_acl_users(context)
    if acl_users is None:
        return None
    return getattr(acl_users, "ldap", None)


def _first(value, default=""):
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        return value[0] if value else default
    return value


def user_to_mapping(user):
    attrs = getattr(user, "attrs", {}) or {}
    result = {name: _first(attrs.get(name)) for name in USER_ATTRS}
    result["uid"] = result.get("uid") or getattr(user, "id", "")
    return result


def get_ldap_user(context, uid):
    ldap = get_ldap_plugin(context)
    if ldap is None or not uid:
        return {}
    try:
        return user_to_mapping(ldap.users[uid])
    except (AttributeError, KeyError, TypeError):
        return {}


def search_ldap_users(context, term, params=None, exact_match=False):
    ldap = get_ldap_plugin(context)
    if ldap is None or not term:
        return []

    users = getattr(ldap, "users", None)
    if not users:
        return []

    params = params or USER_ATTRS
    attrlist = tuple(set(USER_ATTRS) | set(params))
    results = {}
    for param in params:
        criteria = {param: term if exact_match else term + "*"}
        try:
            matches = users.search(
                criteria=criteria,
                attrlist=attrlist,
                exact_match=exact_match,
            )
        except (KeyError, ValueError, TypeError):
            continue
        for user_id, attrs in matches:
            row = {name: _first(attrs.get(name)) for name in attrlist}
            row["uid"] = row.get("uid") or user_id
            results[row["uid"]] = row
    return list(results.values())


def get_ldap_group_ids(context):
    ldap = get_ldap_plugin(context)
    if ldap is None:
        return []
    try:
        return list(ldap.groups.keys())
    except AttributeError:
        return [group["id"] for group in ldap.enumerateGroups(sort_by="id")]


def search_ldap_groups(context, term):
    ldap = get_ldap_plugin(context)
    if ldap is None or not term:
        return []
    try:
        matches = ldap.groups.search(
            criteria={"id": term + "*"},
            exact_match=False,
        )
    except Exception:
        return []
    return [
        {"id": group_id, "cn": group_id, "title": group_id}
        for group_id in sorted(matches)
    ]


def get_ldap_schema(context):
    ldap = get_ldap_plugin(context)
    if ldap is None:
        return [(name, name) for name in USER_ATTRS]
    try:
        return list(ldap.settings["users.attrmap"].items())
    except Exception:
        return [(name, name) for name in USER_ATTRS]
