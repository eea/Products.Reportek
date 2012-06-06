Deploy using buildout
=====================

The current best practice is to deploy Zope serivces using buildout.
Several configurations_ are maintained in SVN.

.. _configurations: https://svn.eionet.europa.eu/repositories/Zope/trunk/cdr-buildout/

1. Create the root buildout directory and check out the code and
configuration (use any path you like for ``$BUILDOUT_DIR``)::

    $ BUILDOUT_DIR="/var/local/cdr-production"
    $ SVNTRUNK="https://svn.eionet.europa.eu/repositories/Zope/trunk"
    $ mkdir $BUILDOUT_DIR; cd $BUILDOUT_DIR
    $ svn checkout $SVNTRUNK/Products.Reportek/ src/Products.Reportek
    $ svn checkout $SVNTRUNK/cdr-buildout/production/ src/cdr-buildout-production

2. Manually link our products that we depend on. This should be
streamlined at some point::

    $ svn checkout $SVNTRUNK/XMLRPCMethod src/XMLRPCMethod
    $ svn checkout $SVNTRUNK/SmallObligations src/SmallObligations
    $ svn checkout $SVNTRUNK/RDFGrabber src/RDFGrabber
    $ mkdir products
    $ cd products
    $ ln -s ../src/XMLRPCMethod
    $ ln -s ../src/SmallObligations
    $ ln -s ../src/RDFGrabber
    $ cd ..

3. Create cache folders and symlink buildout files (symlinks are used to
avoid polluting the local SVN checkout folder). Then run `bootstrap` so
that buildout takes ownership of this installation::

    $ mkdir cache cache/download cache/extends src
    $ ln -s src/cdr-buildout-production/bootstrap.py
    $ ln -s src/cdr-buildout-production/buildout.cfg
    $ python2.7 bootstrap.py -d

4. Run the buildout script to install dependencines and configure
everything. This can be run many times, whenever something changes in
the configuration::

    $ bin/buildout

5. If you are performing a migration: copy the `Data.fs` file to
``var/filestorage/Data.fs``; copy the `reposit` folder to
``var/zope-instance/reposit``. After starting the Zope server, make sure
to pack the database, so ZODB has a chance to update its on-disk data
structures.

6. Start up the server. It will listen on whatever port is specified in
``buildout.cfg``, under ``http-address``::

    $ bin/zope-instance start


Update scripts for migrating to Zope 2.13 (June 2012)
=====================================================

Prerequisities
~~~~~~~~~~~~~~
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

Authentication::

    >>> import update_auth
    >>> update_auth.update_authentication(app)
    >>> import transaction; transaction.commit()

Catalog::

    >>> import update_catalog_indexes
    >>> update_catalog_indexes.update_indexes(app)
    >>> import transaction; transaction.commit()
