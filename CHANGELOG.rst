3.1.2 (2012-12-17)
------------------
* Add creator to the rdf response [dincamih]
* Add Build_collections (bulk creation of collections) [dincamih]
* Fix converters with extraparams [dincamih]
* Fix gml without background converters [dincamih]
* Bring back convertDocument for external calls compat. [dincamih]

3.1.1 (2012-11-23)
------------------
* Add apps migration deploy script [dincamih]
* Add UNS settings to ReportekEngine._properties [dincamih]
* Remove ReportekEngine.__setstate__ [dincamih]

3.1 (2012-11-21)
----------------
* Move envelope applications from '/' [dincamih]
* Local conversion service [dincamih]
* Convert using ApacheTika [dincamih]
* Require buildout flag to send UNS notifications [moregale]

3.0 (2012-08-31)
----------------
* Remove support for HTTP Range requests [moregale]
* Clean API for accessing a document's file content [moregale]
* For local scripts that need access to documents we create temporary
  files instead of providing paths to the original data store [moregale]
* Document storage reimplemented using ZODB BLOBs [moregale]
* Zip cache moved to ``${CLIENT_HOME}/zip_cache`` [moregale]
* New object type `File (Blob)` similar to OFS.Image.File [moregale]
* Feedback files stored as `File (Blob)` objects [moregale]
* Move search pages to disk [dincamih]

2.3 (2012-06-13)
----------------
* included update_catalog_indexes script in extras [nitaucor]
* included update_auth package in extras, see docstring of init [simiamih]
* Switch to distutils package structure. [moregale]
* Documentation generated with Sphinx. [roug, moregale]
* Remove Article 17 reporting from 2007. [bulanmir]
* Rewrite XML Schema sniffer, drop dependency on PyXML. [moregale]
* Change imports (CatalogAware; OFS events) to work on Zope 2.13. [moregale]
* Send email for errors caught by `error_log`. [moregale]

2.2
---
* Last version to be installed in Zope2 Products folder; compatible with
  Zope 2.9
