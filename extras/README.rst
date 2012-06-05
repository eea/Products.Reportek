Update procedures
===================

Prerequisities
-----------------

Checkout Products.LDAPUserFolder = 2.23 in develop and copy SimpleLog
module from `extras/update_auth` package into Products.LDAPUserFolder module.
Start Zope in debug from this path:

    $ pwd
    /your/env/src/Products.Reportek/extras
    $ ../../../bin/zope-instance debug


Authentication
-----------------

    >>> from update_auth import update_authentication
    >>> update_authentication(app)
    >>> import transaction; transaction.commit()


Catalog
-----------------

    >>> import update_catalog_indexes
    >>> update_catalog_indexes.update_indexes(app)
    >>> import transaction; transaction.commit()
