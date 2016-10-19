=================
Products.Reportek
=================

.. Contents ::

What is Reportek?
-----------------

The Reportek is a Zope Product that implements the second generation of the EIONET national repository.

Dependencies
------------

Reportek depends on two lists that it must get from somewhere:

* a list of obligations 
* a list of localities

You can either get the list from http://ROD.eionet.europa.eu with XML-RPC or you can use the ``SmallObligations`` product to roll your own obligations and/or localities. See the file ``HINTS.txt`` for information.

Installation
------------

The recommended method of installing the product is to run a buildout similar to the `reportek-zopebuildout <https://github.com/eea/reportek.zopebuildout>`_. All the requirements and prerequisites are documented in order for ease of deployment.

What is the envelopes.rdf script for?
-------------------------------------

The ``envelopes.rdf`` is used by Reportnet's content registry to harvest deliveries made to the repository. It uses a format called ``RDF``. If you don't want the content registry to harvest you don't need to install it.

Quickview converters
--------------------

Documents have the ability to display their content converted to text or HTML - really anything that is quicker to display than the native format. For this it uses external converters. Look in ``Document.py`` to see what. If you haven't installed a certain external program, then ``Document.py`` will fall back to the native format.

The folder ``Converters`` is automatically added in the Root folder after the product is installed. In order to use the converters installed on the server (local converters) you must add an object of type ``Converter`` in the ``Converters`` folder specifying the path to the actual converter file, the type of the files that can be converted by it and the type of the output files.
    
(eg. If you have installed the pdftotext converter then type in the Converter path (including the arguments) something like: 
``pdftotext -raw %s`` for Linux or something like ``"C:\Program Files\pdftotext" -raw %s`` for Windows.)

Once a converter is added in the Report Document list, you will be given the possibility to choose among the available conversions (*View document as*) for every type of document.

Authentication
--------------

You can use Zope's builtin User folder, or you can use LDAPUserFolder from http://www.dataflake.org. This will hook you into the CIRCA site directory, Your own organisation's or EEA's. That is up to you.

Authorization
-------------

Four (Five) types of users are foreseen:

* The anonymous visitor, who can browse released reports and download the public files.
* The trusted client, who can browse released reports and download public and protected files.
* A collection administrator, who maintain the hierarchial structure, but who doesn't upload any reports.
* A release-coordinator, who releases an envelope to the public. The public must be confident that they are not downloading an incomplete report, so a release/-revocation is logged in the activity log. Once a report is released, it is no longer possible to upload files. If a mistake is found then the release-status can be revoked.
* A reporter, who creates the actual reports. A reporter can request a report to be released when he is finished.

And then there still is the Zope Manager, who can fix everything if/when the security paradigme doesn't cut it.

A user can be one, more or all of these roles at the same time. Additionally, a user can only delete objects he himself have created. And in the case of files, only if the envelope is not released.

Usage
-----

The purpose of this product is to make it easy to store the obligatory environmental reports from each country. There are several organisations who receive these reports and for each organisation there are several reports covering subjects such as water and air quality.

To deal with the many reports we let the user organise them in a hierarchial set of collections of his own choice. At the leaves of the structure are the envelopes. They contain all the files and necesary meta-data. The collections also have meta-data, but they only serve as default values for envelope creation.

To prepare a report you first create an envelope. Then you upload the files and finally you release it for the public.

Generate documentation
----------------------

You can find information on how to generate documentation in the `reportek-zopebuildout's README <https://github.com/eea/reportek.zopebuildout#generate-documentation>`_

Tests
-----
You can find information on how to run the tests in the `reportek-zopebuildout's README` <https://github.com/eea/reportek.zopebuildout#tests>`_
