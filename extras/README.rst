Update procedures
===================

Prerequisities
-----------------

Checkout Products.LDAPUserFolder = 2.23 in develop and copy SimpleLog
module from `extras/update_auth` package into Products.LDAPUserFolder
module::

    $ cd /your/buildout/directory
    $ cd src
    $ curl http://pypi.python.org/packages/source/P/Products.LDAPUserFolder/Products.LDAPUserFolder-2.23.tar.gz | tar xzvf -
    $ cd Products.Reportek/extras
    $ cp update_auth/SimpleLog.py ../../Products.LDAPUserFolder-2.23/Products/LDAPUserFolder/

Start Zope in debug from this path. Don't worry about an
``AttributeError: _hash`` message, the update script will fix that.

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
