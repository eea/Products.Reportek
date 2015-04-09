3.8.4 (09-04-2015)
------------------
* Task #21032 - Added referrals migration extension script [olimpiurob]
* Task #21032 - Include Repository Referrals in obligation search on CDR [olimpiurob]

3.8.3 (06-04-2015)
------------------
* Task #24025 - Drop fuzzy search and use exact_match for ldap_user_folder.findUser [olimpiurob]
* Task #23435 - Display the envelope's id if there's no title in searchdsearchdataflow results [olimpiurob]
* Task #23434 - Url quote reportingdate_start and reportingdate_end in engineMacros template [olimpiurob]
* Task #20536 - Treat case when an envelope's workflow does not exist anymore [olimpiurob]

3.8.2 (27-03-2015)
------------------
* Task #21521 - Adding support for uploading multiple files on feedback [malduvit]
* Task #22820 - Added an explanatory text [malduvit]

3.8.1 (11-03-2015)
------------------
* move getCountryName and getCountryCode to Reportek Collection
* Refs #23650 show comapny id in collections ZMI->settings [baragdan]
* Refs #21879 - improve threaded localQA [baragdan]

3.8.0 (27-02-2015)
------------------
* proper production egg

3.7.2-dev16 (26-02-2015)
------------------------
* Task #23412 - Conversion of XML file to XLS gives an error
* Task #23463 - overridden PropertiedUser.getRolesInContext() to check middleware too

3.7.2-dev15 (26-02-2015)
------------------------
* Task #23451 - AttributeError company_id
* Task #22656 - use script title in feedback id
* Task #22974 - minor fix

3.7.2-dev14 (20-02-2015)
------------------------

3.7.2-dev13 (19-02-2015)
------------------------
* Task #23228 - Authentication lost on BDR. add webqKeepAlive [baragdan]
* Task #22974 - Search dataflow functionality in ReportekUtilities [malduvit]
* Task #23217 - nicely inform user that no company was found when no company was found [baragdan]
* Task #23215 - keep GET query arguments when login redirects [baragdan]

3.7.2-dev12 (13-02-2015)
------------------------
* Task #22993 - Add a tab to ReportekEngine management where we can see migrations
* Task #23236 - Fix organisation_details link to reporting folder for non-ue types

3.7.2-dev11 (10-02-2015)
------------------------

3.7.2-dev10 (10-02-2015)
------------------------
* Task #22993 - add migration to migration tracking support. Create migration decorator [baragdan] (needs migration)
* Task #22445 - Lockdown: unmatch companies case + sending emails [baragdan]
* Task #22989 - Fix datatable error on IE [malduvit]

3.7.2-dev8 (05-02-2015)
-----------------------
* Task #22904 - Add missing functionality to Envelope [baragdan]
* Task #22820 - Notification settings [malduvit]
* Task #22817 - Fix url for fgas portal [malduvit]
* Task #22819 - Ajax loading for companies table [malduvit]
* Task #22874 - Ajax loading for pending companies [malduvit]
* Task #22445 - implement Lockdown (TODO: send mails) [baragdan]
* Task #22664 - Run local QA on "Run Full QA" [baragdan]
* Task #21874 - bugfix: invalid json [nituacor]

3.7.2-dev7 (23-01-2015)
-----------------------
* Task #22646 - fix original size of value 0

3.7.2-dev6 (23-01-2015)
-----------------------
* Minor interface changes

3.7.2-dev5 (23-01-2015)
-----------------------
* Task #20076 - Translate fgas portal country codes to bdr country folders
* Imporve BDR messages content on pages involving Fgas Portal

3.7.2-dev4 (22-01-2015)
-----------------------
* Refs #21874 - ReportekAPI with get all released envelopes and other methods

3.7.2-dev3 (22-01-2015)
-----------------------
* Task #20076 - Fgas Portal integration [baragdan] (BDR only) {setup it in Data.fs}
* Task #20006 - Add support for CAS/eCAS auth for whoever needs it [baragdan] (BDR) {needs setup of Data.fs objects OR benign if unconfigured}
* Task #22376 - Moved build collections form from ReporekEngine to ReportekUtilities [malduvit]


3.7.2-dev2 (14-01-2015)
-----------------------
* Task #22404 - Workaround zope's inabillity to detect mime type while utf8 BOM present [baragdan]
* Task #22436 - Fix seek(0) on raw zip handler when normal, non raw read is used [baragdan]

3.7.2-dev1 (06-01-2015)
-----------------------
* Task #22312
    - Add more categories to ReportekUtilities 

3.7.2-dev (05-01-2015)
----------------------
* Task 19360 - add 'deferred mode' to the compression of Report Documents [baragdan]
* better separation of deployments [baragdan]
* fixes for ReportekUtilities [malduvit]


3.7.1 (10-12-2014)
-------------------
* Task 3324 
    - Fixed file upload in envelope [vitaliemaldur]
    - Fixed the id generation for the file [vitaliemaldur]
* Task 21521 - Simplified process of attaching multiple files to a feedback [olimpiurob]
* Task 20358:
    - Added the possiblity of changing the properties of the ReportekEngine
      xmlrpc methods from manage_properties view [olimpiurob]
    - Removed inheritance DataflowsManager and CountriesManager inheritance in
      the Collection class. The xmlrpc methods will be called from ReportekEngine [olimpiurob]
    - Fixed tests after migration [olimpiurob]
    - Minor changes to ReportekUtilities. [olimpiurob]
    - Added statistics and envelopes.autocomplete browser pages in
      views.zcml. [olimpiurob]
    - Changed assign_role functionality to add the new role instead of
      overwriting existing ones. [olimpiurob]
    - Changed revoke_roles functionality to add the possibility of individually
      select which roles to revoke. [olimpiurob]
    - Added functional tests for ReportekUtilities [olimpiurob]
* Task 20730 - Make zip upload much more faster by transplanting zipped content from zip container to gzip blob file [baragdan]

3.7.0 (16-10-2014)
-------------------
* Task 20730 - Add migration script to fix blob file sizes (requires migration) [baragdan]
* Task 21228 - Make CR ping robust towards concurrent pings for the same envelope and durable in case of zope restart [baragdan]
* Task 21377 - Make script for exporting all feedback urls that are manual and include email addresss [baragdan]
* Task 20730 - Fixed getZipInfo method not to crash when fed non-zip file [baragdan]
* Task 20561 - Fix the display of content_type for old, compression unaware Documents [baragdan]
* Task 20537 - Prevent empty obligation from showing in enevelopes obligations [baragdan]
* Task 19360 - Get rid of unreliable fs_path. Blobs can be  moved by zope so always compute the path (requires migration) [baragdan]
* Task 20500 - fix pingCR for local roles [nituacor]
* Task 19360 - Avoid decompressing and recompressing [baragdan]
* Task 19323 - Eliminate the unreleased gap between the envelope release and CR ping [baragdan]

3.6.17 (23-06-2014)
-------------------
* Task 19962 - Implemented functionality for allow to set the maximum size for QA script. [mironovi]

3.6.16 (19-06-2014)
-------------------
* Task 5992 - export only apps referenced by procs; also do path compare and report for apps [baragdan]
* Task 3312 - Fixed rebuild_catlog to include the dataflow mapping records [baragdan]

3.6.15 (18-06-2014)
-------------------
* Task 5992 - Fix and improve Import/Export of open dataflow processes [baragdan]
* Task 19856 - Fix Obligation list under envelope properties [baragdan]
* Task 3279 - Broaden the detection of xml mime type [baragdan]
* Task 17226 - Reject ambiguous schema locations [baragdan]

3.6.14 (2014-05-20)
-------------------
* Task 3312 - Refactor DataflowMappings [baragdan]
* Task 17579 - Envelope activities history show missing activities in red [baragdan]
* Task 19418 - RDF output has links url quoted [baragdan]
* Task 18960 - Reportek to split xmlSchema on space in RDF output [baragdan]
* Task 19323 - Implement ping/delete to the Content Registry [baragdan]
* Task 17109 - Implement a ping to the content registry (also pings subitems) [baragdan]

3.6.13 (2014-04-22)
-------------------
* Task 19353 - fix searchdataflow displaying search regardless of permissions
* Task 19310 - fix displaying of multiyear obligation in envelope overview [baragdan]

3.6.12 (2014-04-11)
-------------------
* Task 18707 - Fix receiving of remote conversion service results [baragdan]
* Task 17612 - Build_collections: improve error messages
* Task 17109 - Implement ping on enevlope release but not yet on revoke [baragdan]

3.6.11 (2014-03-13)
-------------------
* Task 17922 - Write size of uploaded file to event log [nituacor]

3.6.10 (2014-03-10)
-------------------
* Task 17979 - Fix yet another kind of blob path.

3.6.9 (2014-03-10)
------------------
* Task 17247 - Rerender feedback htmls. Update script to readd missing html. Prevent reportek.convertes/safe_html from removing i18n
* Task 17979 - Fix blob path when uploading new file

3.6.8 (2014-03-03)
------------------
* Task 18701 - Add url filed back to search form

3.6.7 (2014-02-28)
------------------
* Task 18521 - Fixed the expiration message on the envelope note page

3.6.6 (2014-02-26)
------------------
* Some fixes to DTML -> ZPT conversion. Fix the envelope overview automatic refresh.
* Task 18609 - Fix radio button labels on search form.

3.6.5 (2014-02-26)
------------------
* Task 17979 - Fix blob path computation

3.6.4 (2014-02-25)
------------------
* Task 18472 - Refactor search.
* Task 17979 - Add blob path in filesystem to manage document view
* adapted locales/update.sh script for buzzardNT staging deployment

3.6.3 (2014-01-27)
------------------
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
