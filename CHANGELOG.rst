3.6.6 (unreleased)
----------------
3.6.5 (2014-02-26)
----------------
* Task 17979 - Fix blob path computation

3.6.4 (2014-02-25)
----------------
* Task 18472 - Refactor search.
* Task 17979 - Add blob path in filesystem to manage document view
* adapted locales/update.sh script for buzzardNT staging deployment

3.6.3 (2014-01-27)
----------------
* Various fixes for a fresh, clean and up-to-date buildout
* Unified products BDR and CDR (based on buildout REPORTEK_DEPLOYMENT env var)
* Add multilanguage to Reportek

3.4 (2013-09-09)
----------------
* Remote converters use RESTful API
* Local QA script assignable to mime-type
* Remote REST Application (Art. 17)

3.3 (2013-06-17)
----------------
* Add globally_restricted_site flag in ReportekEngine (for BDR) [dincamih]
* Display mapping related messages when handling application files [dincamih]
* Implement Envelope.has_blocker_feedback REST API [dincamih]
* SVG workflow graph [dincamih]
* Add interface to retrieve feedback details [dincamih]
* Reimplement SHP converter [dincamih]
* Use REST API for remote conversions [dincamih]
* View for displaying local roles for user id [dincamih]
* Other minor fixes [dincamih]

3.2 (2013-02-01)
----------------
* Session-based mechanism to set and display system messages [moregale]
* Fix handling of large files (XML sniffing, zip download) [moregale]
* Fetch dataflow schema mappings from DD; edit and save the table in a single object [moregale]
* Replace TinyMCE with CKEditor [dincamih]
* Clean feedbacks and comments before saving [dincamih]
* Add description note for local conversion service [dincamih]

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
