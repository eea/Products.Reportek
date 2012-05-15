What is Reportek?
=================

The Reportek is a Zope Product that implements the second
generation of the EIONET national repository.

Dependencies
------------

Reportek depends on two lists that it must get from somewhere: A list
of obligations and a list of localities. You can either get the list
from ROD.eionet.eu.int with XML-RPC or you can use the SmallObligations
product to roll your own obligations and/or localities. See the file
HINTS.txt for information

Python dependencies
-------------------

Reportek needs PyXML from http://pyxml.sourceforge.net/
pyshapelib from http://ftp.intevation.de/users/bh/pyshapelib/
shapelib from http://dl.maptools.org/dl/shapelib/

Installation
------------

If you haven't already done it, first create a ZCatalog named
Catalog. Keep the default indexes and metadata. Then add the following indexes:
TextIndex: PrincipiaSearchSource, 
FieldIndex: bobobase_modification_time, id, meta_type, country,
dataflow, partofyear, released, reportingdate.
KeywordIndex: years.
PathIndex: path
Then add as metadata: bobobase_modification_time, id, meta_type, country,
dataflow_title.
Otherwise search will not work. Extract Reportek to the Product folder.

Then there is a ZEXP file called Reportek-scripts. It contains the
design template, the DTML code for search etc. Copy it to the import
directory. Then import it into the toplevel Zope folder. Depending
on your preferences copy the scripts to where you have created
Reportek Collections.

What is the envelopes.rdf script for?
-------------------------------------

The envelopes.rdf is used by Reportnet's content registry to harvest
deliveries made to the repository. It uses a format called RDF. If
you don't want the content registry to harvest you don't need to
install it.

Quickview converters
--------------------

Documents have the ability to display their content converted to text
or HTML - really anything that is quicker to display than the native
format. For this it uses external converters. Look in Document.py
to see what. If you haven't installed a certain external program,
then Document.py will fall back to the native format.

The folder 'Converters' is automatically added in the Root folder 
after the product is installed. In order to use the converters 
installed on the server (local converters) you 
must add an object of type 'Converter' in the Converters folder 
specifying the path to the actual converter file, the type of the files 
that can be converted by it and the type of the output files.

(e.g. If you have installed the pdftotext converter then type in the 
Converter path (including the arguments) something like: 
'pdftotext -raw %s' for Linux or something like: 
"C:\ProgramFiles\pdftotext" -raw %s for Windows

Once a converter is added in the Report Document list, you will be 
give the possibility to choose among the available conversions 
(View document as.) for every type of document.

Authentication
--------------

You can use Zope's builtin User folder, or you can use LDAPUserFolder
from www.dataflake.org. This will hook you into the CIRCA site directory
Your own organisation's or EEA's. That is up to you.

Authorization
-------------

Four (Five) types of users are foreseen:

* The anonymous visitor, who can browse released reports and download
  the public files.

* The trusted client, who can browse released reports and download
  public and protected files.

* A collection administrator, who maintain the hierarchial structure,
  but who doesn't upload any reports.

* A release-coordinator, who releases an envelope to the public. The
  public must be confident that they are not downloading an incomplete
  report, so a release/-revocation is logged in the activity log.
  Once a report is released, it is no longer possible to upload files.
  If a mistake is found then the release-status can be revoked.

* A reporter, who creates the actual reports. A reporter can request
  a report to be released when he is finished.

* And then there still is the Zope Manager, who can fix everything
  if/when the security paradigme doesn't cut it.

A user can be one, more or all of these roles at the same time.

Additionally, a user can only delete objects he himself have created.
And in the case of files, only if the envelope is not released.

Permissions
-----------

There are seven permissions:

* Add Collections, which is given to the collection administrator

* Change Collections, which is given to "owner". Thereby the collection
  administrator can only modify the collections he has created.

* Add Envelopes, which is given to the "reporter". This allows people to
  create envelopes. If you have the right to create an envelope you also
  have the right to add files into it.  If there are certain parts of
  the hierarchy that a reporter should be restricted to, then give him
  the permission as a local role, or create a user folder on that level.

* Change Envelopes. Give this permission to "owner" to let a "reporter"
  fill his own envelopes or give the permission to "reporter" to let all
  reporters modify all envelopes.

* Add Feedback given to "Client" to be able to add feedback for release
  of envelopes

* Delete Objects. Typically give this permission to "owner" and mayby
  "release-coordinator" or "collection administrator".

* Release Envelopes. Can be given to "owner", "reporter" or some
  other class of users.

Usage
-----

The purpose of this product is to make it easy to store the
obligatory environmental reports from each country. There are several
organisations who receive these reports and for each organisation
there are several reports covering subjects such as water and air
quality.

To deal with the many reports we let the user organise them in a
hierarchial set of collections of his own choice. At the leaves
of the structure are the envelopes. They contain all the files and
necesary meta-data. The collections also have meta-data, but they
only serve as default values for envelope creation.

To prepare a report you first create an envelope. Then you upload
the files and finally you release it for the public.
