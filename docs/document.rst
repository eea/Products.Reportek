:mod:`Products.Reportek.Document` --- Document module
=====================================================

.. module:: Products.Reportek.Document

Documents are objects in the Zope OFS that encapsulate a file. Data is stored
efficiently on the filesystem. Content can be uploaded, modified and downloaded
through-the-web, or via the Python API.

Content is accessed via :attr:`.Document.data_file`. See :class:`.FileContainer`
for more information::

    >>> with doc.data_file.open() as f:
    ...    print "first 100 bytes: %r" % f.read(100)

To write a new version, open the data file as ``wb``::

    >>> with doc.data_file.open('wb') as f:
    ...    f.write("some new content")


:class:`~Products.Reportek.Document.Document` --- Container for uploaded files
------------------------------------------------------------------------------
.. autoclass:: Products.Reportek.Document.Document
   :members:

:class:`~Products.Reportek.Document.FileContainer` --- Container for document content
-------------------------------------------------------------------------------------
.. autoclass:: Products.Reportek.Document.FileContainer
   :members:

:class:`~Products.Reportek.IconShow.IconShow` --- Mixin class
-------------------------------------------------------------
.. automodule:: Products.Reportek.IconShow
   :members:

