"""Patches for node.ext.ldap."""

import logging

import ldap

logger = logging.getLogger("Reportek")


def patched_authenticate(self, dn, pw):
    """Verify credentials, but don't rebind the session to that user.

    node.ext.ldap's LDAPConnector.bind() applies ``conn_timeout`` and
    ``op_timeout``, but LDAPSession.authenticate() bypasses the connector and
    opens a raw python-ldap connection for the user credential bind. Apply the
    same timeout settings here so a stalled LDAP bind cannot occupy a Waitress
    worker indefinitely.
    """
    props = self._props
    if props.ignore_cert:  # pragma: no cover
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    elif props.tls_cacertfile:  # pragma: no cover
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, props.tls_cacertfile)
    elif props.tls_cacertdir:  # pragma: no cover
        ldap.set_option(ldap.OPT_X_TLS_CACERTDIR, props.tls_cacertdir)
    if props.tls_clcertfile and props.tls_clkeyfile:  # pragma: no cover
        ldap.set_option(ldap.OPT_X_TLS_CERTFILE, props.tls_clcertfile)
        ldap.set_option(ldap.OPT_X_TLS_KEYFILE, props.tls_clkeyfile)
    elif props.tls_clcertfile or props.tls_clkeyfile:  # pragma: no cover
        logger.exception("Only client certificate or key have been provided.")

    con = ldap.initialize(
        props.uri,
        bytes_mode=False,
        bytes_strictness="silent",
    )
    con.set_option(ldap.OPT_REFERRALS, 0)

    conn_timeout = getattr(props, "conn_timeout", -1)
    op_timeout = getattr(props, "op_timeout", -1)
    if conn_timeout and conn_timeout > 0:
        con.set_option(ldap.OPT_NETWORK_TIMEOUT, conn_timeout)
    if op_timeout and op_timeout > 0:
        con.timeout = op_timeout

    try:
        if props.start_tls:
            con.start_tls_s()
        con.simple_bind_s(dn, pw)
    except (ldap.INVALID_CREDENTIALS, ldap.UNWILLING_TO_PERFORM):
        return False
    else:
        return True
