:mod:`Products.Reportek.Document` --- Document module
=====================================================

Documents are objects in the Zope OFS that encapsulate a file. Data is stored
efficiently on the filesystem. Content can be uploaded, modified and downloaded
through-the-web, or via the Python API.

Content is accessed via :attr:`.Document.data_file`. See :class:`.FileWrapper`
for more information::

    >>> with doc.data_file.open() as f:
    ...    print "first 100 bytes: %r" % f.read(100)

To write a new version, open the data file as ``wb``::

    >>> with doc.data_file.open('wb') as f:
    ...    f.write("some new content")


:class:`Products.Reportek.Document` --- Document core class
-----------------------------------------------------------

.. automodule:: Products.Reportek.Document
   :members:

:class:`Products.Reportek.IconShow` --- Mixin class
---------------------------------------------------

.. automodule:: Products.Reportek.IconShow
   :members:

